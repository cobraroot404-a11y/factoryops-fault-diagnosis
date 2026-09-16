from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://factoryops:factoryops@localhost:5432/factoryops"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    rabbitmq_url: str = "amqp://factoryops:factoryops@localhost:5672/"
    telemetry_exchange: str = "telemetry.exchange"
    readings_queue: str = "readings.process"
    readings_retry_queue: str = "readings.retry"
    readings_dead_letter_queue: str = "readings.dead-letter"
    max_delivery_attempts: int = 3
    retry_delay_ms: int = 5000

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_request_body_bytes: int = 65536

    # Diagnosis rule engine — configurable thresholds, persistence windows, hysteresis.
    temp_trigger_c: float = 85.0
    temp_clear_c: float = 75.0
    current_trigger_a: float = 18.0
    current_clear_a: float = 14.0
    vibration_trigger_mm_s: float = 7.0
    vibration_clear_mm_s: float = 4.5
    persistence_breaches_to_trigger: int = 3
    persistence_healthy_to_clear: int = 5
    missing_telemetry_seconds: int = 30
    missing_telemetry_check_interval_seconds: int = 10

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
