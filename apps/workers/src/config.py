"""Application configuration via Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Worker configuration loaded from environment variables.

    All defaults point to LocalStack / local dev. No real credentials needed
    for local development.
    """

    DATABASE_URL: str = "postgres://autokindler:autokindler@localhost:5432/autokindler"

    # SQS
    SQS_ENDPOINT: str = "http://localhost:4566"
    SQS_QUEUE_URL: str = (
        "http://sqs.us-east-1.localhost.localstack.cloud:4566"
        "/000000000000/autokindler-deliveries"
    )
    AWS_REGION: str = "us-east-1"

    # SES / SMTP
    SES_SMTP_HOST: str = "localhost"
    SES_SMTP_PORT: int = 4566
    SES_SMTP_USER: str = ""
    SES_SMTP_PASSWORD: str = ""
    SES_FROM_EMAIL: str = "autokindler@openfolie.org"

    # File cache
    CACHE_DIR: str = "/tmp/autokindler-cache"
    CACHE_TTL_DAYS: int = 3

    # Timeouts (seconds)
    DOWNLOAD_TIMEOUT: int = 60
    CONVERSION_TIMEOUT: int = 120
    EMAIL_TIMEOUT: int = 30
    JOB_TIMEOUT: int = 300

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
