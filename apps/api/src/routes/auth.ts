import { Hono } from "hono";
import { getCookie, setCookie } from "hono/cookie";
import { db, users, userPreferences } from "@autokindler/db";
import { eq } from "drizzle-orm";
import { env } from "../lib/env.js";
import { signJwt } from "../lib/jwt.js";

export const authRoutes = new Hono();

/**
 * GET /api/auth/github
 * Initiate GitHub OAuth flow — redirect user to GitHub authorization page.
 */
authRoutes.get("/github", (c) => {
  // Generate random state for CSRF protection
  const state = crypto.randomUUID();

  // Store state in a short-lived cookie (5 min)
  setCookie(c, "oauth_state", state, {
    httpOnly: true,
    secure: env.APP_URL.startsWith("https"),
    sameSite: "Lax",
    maxAge: 300, // 5 minutes
    path: "/",
  });

  const params = new URLSearchParams({
    client_id: env.GITHUB_CLIENT_ID,
    redirect_uri: `${env.APP_URL}/api/auth/github/callback`,
    scope: "read:user user:email",
    state,
  });

  return c.redirect(
    `https://github.com/login/oauth/authorize?${params.toString()}`
  );
});

/**
 * GET /api/auth/github/callback
 * Handle GitHub OAuth callback — exchange code for token, upsert user, issue JWT.
 */
authRoutes.get("/github/callback", async (c) => {
  const code = c.req.query("code");
  const state = c.req.query("state");
  const storedState = getCookie(c, "oauth_state");

  // Validate state parameter
  if (!state || !storedState || state !== storedState) {
    return c.redirect(
      `${env.APP_URL}/auth/callback?error=invalid_state`
    );
  }

  // Clear the state cookie
  setCookie(c, "oauth_state", "", {
    httpOnly: true,
    maxAge: 0,
    path: "/",
  });

  if (!code) {
    return c.redirect(
      `${env.APP_URL}/auth/callback?error=missing_code`
    );
  }

  try {
    // Exchange code for access token
    const tokenResponse = await fetch(
      "https://github.com/login/oauth/access_token",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code,
        }),
      }
    );

    const tokenData = (await tokenResponse.json()) as {
      access_token?: string;
      error?: string;
      error_description?: string;
    };

    if (tokenData.error || !tokenData.access_token) {
      console.error("GitHub token exchange failed:", tokenData.error);
      return c.redirect(
        `${env.APP_URL}/auth/callback?error=token_exchange_failed`
      );
    }

    const accessToken = tokenData.access_token;

    // Fetch user profile
    const [userResponse, emailsResponse] = await Promise.all([
      fetch("https://api.github.com/user", {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: "application/json",
        },
      }),
      fetch("https://api.github.com/user/emails", {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: "application/json",
        },
      }),
    ]);

    if (!userResponse.ok || !emailsResponse.ok) {
      console.error("GitHub API call failed:", userResponse.status, emailsResponse.status);
      return c.redirect(
        `${env.APP_URL}/auth/callback?error=github_api_failed`
      );
    }

    const emails = (await emailsResponse.json()) as Array<{
      email: string;
      primary: boolean;
      verified: boolean;
    }>;

    // Find primary verified email
    const primaryEmail = emails.find((e) => e.primary && e.verified);
    if (!primaryEmail) {
      return c.redirect(
        `${env.APP_URL}/auth/callback?error=no_verified_email`
      );
    }

    const email = primaryEmail.email;

    // Upsert user in DB
    const [upsertedUser] = await db
      .insert(users)
      .values({ email })
      .onConflictDoUpdate({
        target: users.email,
        set: { email }, // no-op update to trigger RETURNING
      })
      .returning({ id: users.id, email: users.email });

    // Create user_preferences row if new user (idempotent)
    await db
      .insert(userPreferences)
      .values({ userId: upsertedUser.id })
      .onConflictDoNothing({ target: userPreferences.userId });

    // Sign JWT
    const jwt = await signJwt({
      userId: upsertedUser.id,
      email: upsertedUser.email,
    });

    // Set httpOnly cookie with JWT
    setCookie(c, "autokindler_token", jwt, {
      httpOnly: true,
      secure: env.APP_URL.startsWith("https"),
      sameSite: "Lax",
      maxAge: 7 * 24 * 60 * 60, // 7 days
      path: "/",
    });

    // Redirect to frontend callback with token for extension to capture
    return c.redirect(
      `${env.APP_URL}/auth/callback?token=${jwt}`
    );
  } catch (err) {
    console.error("OAuth callback error:", err);
    return c.redirect(
      `${env.APP_URL}/auth/callback?error=auth_failed`
    );
  }
});
