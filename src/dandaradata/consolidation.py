"""Deduplicate by provisional COMMUNITY identity, never solely by FCP record."""
from __future__ import annotations
from collections import defaultdict
import pandas as pd
from .models import Decision


def build_relations(decisions: list[Decision]) -> pd.DataFrame:
    grouped: dict[tuple[str,str],list[Decision]] = defaultdict(list)
    for d in decisions:
        if d.decision == 'PROPOSTA':
            grouped[(d.ut,d.entity_id)].append(d)
    rows = []
    for (ut, entity_id), group in sorted(grouped.items()):
        d = sorted(group, key=lambda item:(-item.score,item.candidate_id))[0]
        rows.append({
            'UT': ut,
            'ID_ARTIGO': d.article_id,
            'ID_COMUNIDADE_INTERNO': entity_id,
            'COMUNIDADE_CANDIDATA': d.name,
            'OUTRAS_VARIANTES_VALIDADAS': ' | '.join(sorted({g.name for g in group if g.name != d.name})),
            'COMUNIDADE_FCP_ORIGINAL': d.source_name,
            'Nº PROCESSO NA FCP': d.process,
            'UF': d.uf,
            'MUNICÍPIO_FCP': d.municipality,
            'Nº DE CRQ': d.n_crq,
            'STATUS_IDENTIDADE': d.identity_status,
            'STATUS_RELACAO': 'PROPOSTA_NAO_AUDITADA',
            'PONTUACAO': d.score,
            'CAMPOS_EVIDENCIA': ' | '.join(sorted({field for g in group for field in g.mention_fields.split(' | ')})),
            'EVIDENCIAS_JSON': d.evidences,
        })
    columns = [
        'UT', 'ID_ARTIGO', 'ID_COMUNIDADE_INTERNO','COMUNIDADE_CANDIDATA',
        'OUTRAS_VARIANTES_VALIDADAS', 'COMUNIDADE_FCP_ORIGINAL','Nº PROCESSO NA FCP',
        'UF','MUNICÍPIO_FCP','Nº DE CRQ','STATUS_IDENTIDADE','STATUS_RELACAO',
        'PONTUACAO','CAMPOS_EVIDENCIA','EVIDENCIAS_JSON'
    ]
    return pd.DataFrame(rows, columns=columns)


def make_article_view(articles: pd.DataFrame, relations: pd.DataFrame) -> pd.DataFrame:
    """Article-centric experimental view, NOT a drop-in replacement for audited historical output."""
    names = relations.rename(columns={'COMUNIDADE_CANDIDATA':'COMUNIDADE'})
    # The article input already contains administrative columns from the historical super-sheet.
    # Drop them prior to merging, so candidates' actual FCP process is never overwritten.
    overlapping = [c for c in names.columns if c in articles.columns and c != 'UT']
    data = articles.drop(columns=overlapping, errors='ignore')
    # Keep every article once if it has no relation, and once per entity otherwise.
    return data.merge(names, how='left', on='UT', validate='one_to_many', sort=False)
