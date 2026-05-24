from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_skills_dir() -> str:
    return str(_PROJECT_ROOT / "src" / "infrastructure" / "skills" / "definitions")


class RagSettings(BaseModel):
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedding_dimension: int = 768
    embedding_model: str = "nomic-embed-text"
    top_k: int = 5


class BusinessChatSettings(BaseModel):
    skills_dir: str = Field(default_factory=_default_skills_dir)
    planner_temperature: float = 0.1
    report_temperature: float = 0.4


class PostgresConnectionParams(BaseModel):
    host: str
    port: int
    database: str
    username: str
    password: str

    @property
    def asyncpg_url(self) -> str:
        from urllib.parse import quote_plus
        return (
            f"postgresql+asyncpg://{quote_plus(self.username)}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @property
    def sync_url(self) -> str:
        from urllib.parse import quote_plus
        return (
            f"postgresql+psycopg2://{quote_plus(self.username)}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.database}"
        )


def _parse_dotnet_connection_string(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            key, _, value = part.partition("=")
            result[key.strip().lower()] = value.strip()
    return result


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database (raw .NET connection string) ---
    db_connection_string: str
    db_max_rows: int = 1000

    # --- Ollama ---
    ollama_base_url: str
    ollama_api_key: str
    ollama_model: str

    # --- HuggingFace ---
    huggingface_api_key: str

    # --- RAG (nested via Rag__* env vars) ---
    rag: RagSettings = RagSettings()

    # --- Business chat (nested via BusinessChat__* env vars) ---
    business_chat: BusinessChatSettings = BusinessChatSettings()

    # --- FastFixPro ---
    fastfixpro_api_base_url: str
    fastfixpro_api_token: str

    # --- Parsed connection params (populated by model_validator) ---
    postgres: PostgresConnectionParams | None = None

    @model_validator(mode="after")
    def parse_connection_strings(self) -> "Settings":
        pg = _parse_dotnet_connection_string(self.db_connection_string)
        self.postgres = PostgresConnectionParams(
            host=pg.get("host", "localhost"),
            port=int(pg.get("port", 5432)),
            database=pg.get("database", ""),
            username=pg.get("username", ""),
            password=pg.get("password", ""),
        )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
