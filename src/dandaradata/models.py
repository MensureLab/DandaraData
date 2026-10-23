"""Explicit scientific and administrative entities (IDs are INTERNAL, not official CRQ IDs)."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    entity_id: str
    record_id: int
    process: str
    source_name: str
    name: str
    municipality: str
    uf: str
    n_crq: int
    identity_status: str
    region: str = ''

@dataclass(frozen=True)
class Mention:
    ut: str
    article_id: int
    field: str
    candidate_id: str
    name: str
    matched_text: str
    start: int
    end: int
    context: str

@dataclass(frozen=True)
class Decision:
    ut: str
    article_id: int
    candidate_id: str
    entity_id: str
    process: str
    source_name: str
    name: str
    uf: str
    municipality: str
    n_crq: int
    identity_status: str
    decision: str
    score: float
    evidences: str
    reasons: str
    mention_fields: str
    mention_count: int
    scientific_validation: str = 'NAO_AUDITADA'
