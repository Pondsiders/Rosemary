"""Materialize data/dataset.yaml from seed_cases.yaml + the source database.

Run from anywhere:
    EVAL_SOURCE_DATABASE_URL=postgresql://... uv run python mechanism/evals/extract_dataset.py

Reads `seed_cases.yaml` (committed, with hand-curated labels), pulls the
corresponding rows from the source database, and writes the full materialized
dataset to `data/dataset.yaml` (gitignored).

`EVAL_SOURCE_DATABASE_URL` is required — fails loud if unset. The URL points
at a Postgres database containing the conversation history table this eval
draws from.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import asyncpg
import yaml

_EVALS_DIR = Path(__file__).resolve().parent
_SEED_FILE = _EVALS_DIR / "seed_cases.yaml"
_OUT_DIR = _EVALS_DIR / "data"
_OUT_FILE = _OUT_DIR / "dataset.yaml"


async def _fetch_messages(ids: list[int], url: str) -> dict[int, asyncpg.Record]:
    """Pull source-database rows for the given ids; raise on any missing."""
    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch(
            "SELECT id, timestamp, content FROM scribe.messages WHERE id = ANY($1)",
            ids,
        )
    finally:
        await conn.close()
    by_id = {r["id"]: r for r in rows}
    missing = [i for i in ids if i not in by_id]
    if missing:
        msg = f"Missing row ids in source database: {missing}"
        raise ValueError(msg)
    return by_id


async def _main() -> None:
    """Read seed, join with source content, write materialized dataset."""
    url = os.environ.get("EVAL_SOURCE_DATABASE_URL")
    if not url:
        msg = "EVAL_SOURCE_DATABASE_URL is required (no default)."
        raise RuntimeError(msg)

    seed = yaml.safe_load(_SEED_FILE.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = seed["cases"]

    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        msg = "Duplicate IDs in seed_cases.yaml"
        raise ValueError(msg)

    by_id = await _fetch_messages(ids, url)

    out_cases: list[dict[str, Any]] = []
    for c in cases:
        row = by_id[c["id"]]
        out_cases.append(
            {
                "id": c["id"],
                "stratum": c["stratum"],
                "timestamp": row["timestamp"].isoformat(),
                "content": row["content"],
                "expected_topics": c["expected_topics"],
            }
        )

    _OUT_DIR.mkdir(exist_ok=True)
    _ = _OUT_FILE.write_text(
        yaml.safe_dump(
            {"cases": out_cases},
            sort_keys=False,
            allow_unicode=True,
            width=120,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(out_cases)} cases → {_OUT_FILE}")


if __name__ == "__main__":
    asyncio.run(_main())
