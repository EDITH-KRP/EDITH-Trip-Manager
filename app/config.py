from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EDITH-TRIP MANAGER"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = "DEFAULT_REPLACE_WITH_A_LONG_RANDOM_SECRET_KEY_FOR_JWT_SIGNING"
    access_token_expire_minutes: int = 60

    # Supabase / PostgreSQL Connection
    # Direct PostgreSQL URI or Connection Pooler: postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_db_url: str = ""
    database_url: str = ""
    local_db_path: str = "data/edith.db"

    # Default bootstrap administrator
    admin_name: str = "Prajwal"
    admin_email: str = "prajwal@edith.travel"
    admin_password: str = "Prajwal784"

    frontend_origin: str = "http://127.0.0.1:5500"

    # Indian DLT SMS Gateway Configuration
    sms_enabled: bool = False
    sms_gateway_url: str = "https://www.fast2sms.com/dev/bulkV2"
    sms_gateway_api_key: str = ""
    sms_sender_id: str = "EDTTRP"
    sms_entity_id: str = ""

    # Cloudflare Zero Trust / Access Protection
    cloudflare_access_enabled: bool = False
    cloudflare_access_aud: str = ""
    cloudflare_access_team: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
