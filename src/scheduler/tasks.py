"""Fork-safe Celery wrappers for the NFL ingestion primitives."""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from config.settings import get_settings
from src.db.client import get_worker_db
from src.ingest.espn import sync_scoreboard
from src.ingest.theodds import poll_team_markets
from src.ingest.underdog import ingest_props
from src.ingest.sleeper import sync_sleeper_account
from src.scheduler.celery_app import celery_app


@celery_app.task(name="fantasy.sync_espn")
def sync_espn() -> dict[str, int]:
    async def run() -> dict[str, int]:
        written = {}
        async with get_worker_db() as db:
            for sport in get_settings().supported_sports:
                written[sport] = await sync_scoreboard(db, sport=sport)
        return written

    return asyncio.run(run())


@celery_app.task(name="fantasy.sync_underdog")
def sync_underdog() -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with get_worker_db() as db:
            written, parked = await ingest_props(db)
            return {"written": written, "parked": parked}

    return asyncio.run(run())


@celery_app.task(name="fantasy.sync_team_markets")
def sync_team_markets() -> dict[str, int]:
    async def run() -> dict[str, int]:
        # Never use a module-cached Redis client in a task: every asyncio.run
        # call has a distinct event loop (constraint #22).
        redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
        written = {}
        try:
            async with get_worker_db() as db:
                # One quota guard covers every sport (see poll_team_markets'
                # own docstring) - polling nfl then ncaaf in the same task
                # run means a mid-loop quota trip correctly stops the rest.
                for sport in get_settings().supported_sports:
                    written[sport] = await poll_team_markets(db, redis, sport=sport)
        finally:
            await redis.aclose()
        return written

    return asyncio.run(run())


@celery_app.task(name="fantasy.sync_sleeper")
def sync_sleeper() -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with get_worker_db() as db:
            return await sync_sleeper_account(db)

    return asyncio.run(run())
