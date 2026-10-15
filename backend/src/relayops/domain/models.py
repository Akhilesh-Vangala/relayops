"""Typed public observations and proposals; no private evaluation answers."""
import hashlib
import json
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    kind: Literal["hold_invoice", "open_supplier_claim", "reserve_replacement", "resolve_case"]
    amount: int = Field(ge=0, le=10_000_000)


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    tenant: str = Field(min_length=1, max_length=80)
    case_id: str = Field(min_length=1, max_length=80)
    source_version: str = Field(pattern="^[a-f0-9]{64}$")
    outcome: Literal["resolve", "needs_information", "no_change"]
    explanation: str = Field(min_length=1, max_length=1200)
    evidence_ids: tuple[str, ...] = Field(min_length=4, max_length=12)
    actions: tuple[Action, ...] = Field(max_length=4)

    @classmethod
    def from_json(cls, value):
        return cls.model_validate_json(json.dumps(value))


class Refused(ValueError):
    """A source, policy, ownership or execution boundary was not satisfied."""
