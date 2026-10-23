"""Create lookup candidates, NEVER equate split fragments to certified entities automatically."""
from __future__ import annotations
from collections import defaultdict
import re
import pandas as pd
from .models import Candidate
from .normalization import normalize

UNSUITABLE_FRAGMENTS = {
    'comunidade', 'comunidades', 'quilombo', 'quilombos',
    'quilombola', 'quilombolas', 'crq', 'crqs', 'regiao',
    'territorio', 'territorios', 'povoados', 'estado',
}


def parse_count(value: object) -> int:
    try:
        return max(1, int(float(str(value).strip().replace(',', '.'))))
    except (ValueError, TypeError):
        return 1


def split_name(raw: object) -> list[str]:
    """Candidate fragments, not a certification of individual identities."""
    whole = normalize(raw)
    if not whole or whole in UNSUITABLE_FRAGMENTS:
        return []
    fragments = re.split(r'\s+e\s+|[,/:;()]', str(raw), flags=re.IGNORECASE)
    cleaned: list[str] = []
    for fragment in fragments:
        name = normalize(fragment)
        if len(name) >= 3 and name not in UNSUITABLE_FRAGMENTS and name not in cleaned:
            cleaned.append(name)
    if not cleaned:
        return [whole]
    return cleaned


def build_catalog(fcp: pd.DataFrame) -> tuple[list[Candidate], dict[str, list[Candidate]], pd.DataFrame]:
    candidates: list[Candidate] = []
    alias_index: dict[str, list[Candidate]] = defaultdict(list)
    catalog_rows: list[dict] = []

    for idx, row in fcp.iterrows():
        name = str(row['COMUNIDADE']).strip()
        process = str(row['Nº PROCESSO NA FCP']).strip()
        n_crq = parse_count(row['Nº DE CRQ'])
        parts = split_name(name)
        municipalities = [normalize(m) for m in re.split(r'[|/]', str(row['MUNICÍPIO']))]
        municipalities = [m for m in municipalities if m]
        parts = [p for p in parts if p]
        if not parts:
            continue

        if n_crq == 1:
            identity = 'INDIVIDUAL_POR_REGISTRO'
            # If a single certified community has multiple names, interpret fragments
            # as aliases for ONE candidate entity rather than creating 2 CRQs.
            entity_for_part = [f'FCP-{idx:05d}-01'] * len(parts)
        elif n_crq == len(parts):
            identity = 'INDIVIDUALIZACAO_PROVISORIA'
            entity_for_part = [f'FCP-{idx:05d}-{k:02d}' for k in range(1, len(parts)+1)]
        else:
            identity = 'REGISTRO_AGREGADO_NAO_INDIVIDUALIZADO'
            # All fragment matches refer only to one unresolved administrative group.
            entity_for_part = [f'GRUPO-{idx:05d}'] * len(parts)

        for k, (part, entity_id) in enumerate(zip(parts, entity_for_part), start=1):
            candidate_id = f'C-{idx:05d}-{k:02d}'
            candidate = Candidate(
                candidate_id, entity_id, int(idx), process, name, part,
                ' | '.join(municipalities), str(row['UF']).strip().upper(),
                n_crq, identity, str(row.get('REGIÃO', '')).strip(),
            )
            candidates.append(candidate)
            alias_index[part].append(candidate)
            catalog_rows.append(vars(candidate).copy())

    return candidates, alias_index, pd.DataFrame(catalog_rows)
