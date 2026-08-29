"""Celery application and conservative NFL ingestion schedule."""

from __future__ import annotations

from celery import Celery

from config.settings import get_settings

settings = get_settings()
celery_app = Celery("fantasy_edge", broker=settings.redis_url, include=["src.scheduler.tasks"])
celery_app.conf.update(
    timezone="America/Chicago",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    beat_schedule={
        "sync-espn-scoreboard": {"task": "fantasy.sync_espn", "schedule": 900.0},
        "sync-underdog-props": {"task": "fantasy.sync_underdog", "schedule": 900.0},
        # The Odds API task itself no-ops until an API key is configured and
        # applies its durable quota guard before making another request.
        "sync-team-markets": {"task": "fantasy.sync_team_markets", "schedule": 1800.0},
        "sync-sleeper-leagues": {"task": "fantasy.sync_sleeper", "schedule": 900.0},
    },
)
