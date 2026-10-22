"""Ingest and persist the Aberdeen FC news listing."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from fitba.settings import NORMALIZED_DIR, ensure_dirs
from fitba.sources import afc
from fitba.sources.base import IngestResult

NEWS_COLUMNS = afc.NEWS_COLUMNS


def news_path() -> Path:
    return NORMALIZED_DIR / "news" / "afc.parquet"


def ingest_news(*, force: bool = False) -> IngestResult:
    ensure_dirs()
    source = afc.ingest(force=force)
    if source.status != "ok":
        return source
    try:
        frame = afc.load()
        path = news_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = pl.read_parquet(path)
            frame = pl.concat([existing, frame], how="vertical_relaxed")
        frame = frame.unique(subset=["article_id"], keep="last").sort(
            "published_date", descending=True, nulls_last=True
        )
        frame.write_parquet(path)
        return IngestResult(
            source="afc_news",
            status="ok",
            rows=frame.height,
            path=str(path),
            details={"url": afc.NEWS_URL},
        )
    except Exception as exc:  # noqa: BLE001 - reported to the CLI
        return IngestResult(source="afc_news", status="error", errors=[str(exc)])


def load_news(limit: int | None = None) -> pl.DataFrame:
    path = news_path()
    if not path.exists():
        return pl.DataFrame({column: [] for column in NEWS_COLUMNS})
    frame = pl.read_parquet(path).sort("published_date", descending=True, nulls_last=True)
    return frame.head(limit) if limit else frame
