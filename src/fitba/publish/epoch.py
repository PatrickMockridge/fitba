"""Dataset epoch stamping for published payloads.

Every fresh document in one publish shares a ``dataset_id`` and an
``update_id``. A stale fallback keeps the ids of the content it carries, is
marked ``dataset_state="stale"`` and names its reason; only the serving fields
(``published_at`` and ``served_by_update_id``) move to the current run.

The stamp is applied in the write helpers, so no builder has to remember to add
it. Array payloads cannot carry keys without changing their shape; their epoch
is recorded in the manifest ``files[]`` entry instead.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict

STALE_STATES = {"stale", "partial", "unavailable", "no_fixture"}


class EpochFields:
    """Additive epoch fields shared by every published document."""

    dataset_id: str | None = None
    update_id: str | None = None
    published_at: str | None = None
    served_by_update_id: str | None = None
    dataset_state: str | None = None
    stale_reason: str | None = None
    source_snapshots: dict[str, Any] | None = None


class EpochModel(EpochFields, BaseModel):
    """Strict document base that accepts the additive epoch fields."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


@dataclass(frozen=True, slots=True)
class DatasetStamp:
    dataset_id: str
    update_id: str
    published_at: str
    source_snapshots: dict[str, Any] = field(default_factory=dict)


_STAMP: ContextVar[DatasetStamp | None] = ContextVar("fitba_dataset_stamp", default=None)


def set_stamp(stamp: DatasetStamp) -> Any:
    return _STAMP.set(stamp)


def reset_stamp(token: Any) -> None:
    _STAMP.reset(token)


def current_stamp() -> DatasetStamp | None:
    return _STAMP.get()


def stamp_payload(payload: Any) -> Any:
    """Return a copy of a dict payload with the current epoch fields."""
    stamp = _STAMP.get()
    if stamp is None or not isinstance(payload, dict):
        return payload
    output = dict(payload)
    existing_state = str(output.get("dataset_state") or output.get("state") or "")
    if output.get("dataset_id") is None:
        output["dataset_id"] = stamp.dataset_id
    if output.get("update_id") is None:
        output["update_id"] = stamp.update_id
    output["published_at"] = stamp.published_at
    output["served_by_update_id"] = stamp.update_id
    if output.get("dataset_state") is None:
        output["dataset_state"] = "stale" if existing_state in STALE_STATES else "fresh"
    if output.get("generated_at") is None:
        output["generated_at"] = (
            output.get("served_generated_at")
            if output.get("dataset_state") == "stale" and output.get("served_generated_at")
            else stamp.published_at
        )
    if output.get("dataset_state") == "stale":
        output["stale_reason"] = output.get("stale_reason") or "served_from_previous_publish"
    if "source_snapshots" not in output and stamp.source_snapshots:
        output["source_snapshots"] = stamp.source_snapshots
    return output


__all__ = [
    "STALE_STATES",
    "DatasetStamp",
    "EpochModel",
    "current_stamp",
    "reset_stamp",
    "set_stamp",
    "stamp_payload",
]
