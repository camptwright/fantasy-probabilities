"""Application settings.

CONSTRAINT #14: Alembic runs synchronously and cannot use asyncpg. A bare
postgresql:// URL makes SQLAlchemy reach for psycopg2, which is not a
dependency, and `alembic upgrade head` dies with ModuleNotFoundError.
sync_database_url therefore forces psycopg3 explicitly.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "fantasy"
    postgres_password: str = "changeme"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "fantasy_edge"

    redis_url: str = "redis://redis:6379/0"

    # Sports supported end-to-end (ingestion, API, scheduler). Sleeper's own
    # feature stays NFL-only regardless - Sleeper has no NCAAF product.
    supported_sports: tuple[str, ...] = ("nfl", "ncaaf")

    espn_base_urls: dict[str, str] = {
        "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl",
        "ncaaf": "https://site.api.espn.com/apis/site/v2/sports/football/college-football",
    }
    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    odds_api_sport_keys: dict[str, str] = {
        "nfl": "americanfootball_nfl",
        "ncaaf": "americanfootball_ncaaf",
    }
    odds_api_quota_floor: int = 50
    underdog_base_url: str = "https://api.underdogfantasy.com"
    sleeper_username: str = ""
    sleeper_base_url: str = "https://api.sleeper.app/v1"
    fantasy_api_token: str = ""
    litellm_base_url: str = "http://litellm:4000/v1"
    litellm_api_key: str = ""
    fantasy_model_alias: str = "worker"
    fantasy_news_rss_urls: str = ""

    # Fractional-Kelly multiplier applied to /signals' full-Kelly stake
    # suggestion - standard bankroll-risk reduction, not a fitted value.
    kelly_fraction_cap: float = 0.25

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
