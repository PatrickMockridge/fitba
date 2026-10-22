"""Pydantic models for the canonical metric registry.

The registry is deliberately strict: a newly published number without a
definition, source, verification mode and owner is a build failure. Metric
semantic changes require a version bump and owner review.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Basis = Literal["measured", "inferred", "curated", "mixed", "unknown"]
CoverageTier = Literal["event", "match", "curated", "value_only", "derived", "unknown"]
Verification = Literal[
    "recompute",
    "cross_surface",
    "config_match",
    "source_checksum",
    "provenance_only",
]
Status = Literal["active", "deprecated", "planned"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rounding(StrictModel):
    method: Literal["half_even", "half_up", "floor", "ceil", "integer", "step"]
    decimals: int = 0
    step: int | None = None
    display: str
    scale: float = 1.0
    suffix: str | None = None


class Metric(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9]+(?:\.[a-z0-9-]+)+$")
    label: str
    description: str
    value_type: Literal["scalar", "object", "table", "series"]
    fields: list[str] = []
    formula: str | dict[str, str]
    inputs: list[str]
    unit: str
    aggregation: str
    denominator: str | dict[str, str] | None = None
    rounding: Rounding | dict[str, Rounding]
    basis: Basis
    source_layer: str
    coverage_tier: CoverageTier
    confidence_rule: str
    home_payload: str
    payload_paths: list[str]
    home_surface: str
    displayed_surfaces: list[str]
    verification: Verification
    verification_checks: list[dict[str, str]] = []
    implementation: str | None = None
    source_paths: list[str] = []
    limitations: list[str] = []
    owner: str
    reviewed: date
    version: int = Field(ge=1)
    status: Status = "active"

    @model_validator(mode="after")
    def _validate_contract(self) -> Metric:
        if not self.payload_paths:
            raise ValueError(f"{self.id}: payload_paths must not be empty")
        if not self.displayed_surfaces:
            raise ValueError(f"{self.id}: displayed_surfaces must not be empty")
        if not self.home_surface.startswith("/"):
            raise ValueError(f"{self.id}: home_surface must start with '/'")
        for surface in self.displayed_surfaces:
            if not surface.startswith("/"):
                raise ValueError(f"{self.id}: displayed surface {surface!r} must start with '/'")
        if self.verification == "recompute" and not self.implementation:
            raise ValueError(f"{self.id}: recompute metrics need an implementation")
        if self.verification == "source_checksum" and not self.source_paths:
            raise ValueError(f"{self.id}: source_checksum metrics need source_paths")
        if self.verification == "provenance_only" and not self.limitations:
            raise ValueError(f"{self.id}: provenance_only metrics need an explicit limitation")
        return self


class Parameter(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9]+(?:\.[a-z0-9-]+)+$")
    label: str
    kind: Literal["scalar", "matrix", "enum"]
    value: Any
    unit: str
    used_by: list[str]
    config_path: str
    config_keys: list[str] = []
    verification: Literal["config_match"]
    owner: str
    reviewed: date
    version: int = Field(ge=1)


class ChangePolicy(StrictModel):
    owner_approval_required: bool
    version_scheme: str
    changelog: str


class MetricRegistry(StrictModel):
    schema_version: int
    registry_version: str
    reviewed: date
    owner: str
    change_policy: ChangePolicy
    structural_number_patterns: list[str]
    metrics: list[Metric]
    parameters: list[Parameter]

    @model_validator(mode="after")
    def _validate_registry(self) -> MetricRegistry:
        metric_ids = [metric.id for metric in self.metrics]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("duplicate metric ids")
        parameter_ids = [parameter.id for parameter in self.parameters]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError("duplicate parameter ids")
        return self
