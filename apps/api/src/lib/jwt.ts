import { SignJWT, jwtVerify, type JWTPayload } from "jose";
import { env } from "./env.js";

const secret = new TextEncoder().encode(env.JWT_SECRET);

export interface JwtUserPayload extends JWTPayload {
  sub: string; // userId
  email: string;
}

/**
 * Sign a JWT with HS256, 7-day expiry, iss: 'autokindler'.
 * Returns the compact token string.
 */
export async function signJwt(payload: {
  userId: string;
  email: string;
}): Promise<string> {
  return new SignJWT({ email: payload.email })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(payload.userId)
    .setIssuer("autokindler")
    .setIssuedAt()
    .setExpirationTime(env.JWT_EXPIRY)
    .sign(secret);
}

/**
 * Verify a JWT and return the decoded payload.
 * Throws on expired/invalid tokens.
 */
export async function verifyJwt(token: string): Promise<JwtUserPayload> {
  const { payload } = await jwtVerify(token, secret, {
    issuer: "autokindler",
  });
  return payload as JwtUserPayload;
}
