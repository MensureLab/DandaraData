"""Historical administrative comparison; no fabricated gold-standard entity F1."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

KEYS = ('UT','Nº PROCESSO NA FCP')


def pair_set(df: pd.DataFrame) -> set[tuple[str,str]]:
    if any(c not in df.columns for c in KEYS):
        return set()
    valid = df[list(KEYS)].fillna('').astype(str)
    return {tuple(x) for x in valid.itertuples(index=False, name=None)
            if x[0].strip() and x[1].strip() and x[1].lower() != 'nan'}


def compare_history(relations: pd.DataFrame, historical: Path,
                    audit: Path | None = None, false_negatives: Path | None = None
                    ) -> tuple[pd.DataFrame, dict]:
    prior = pd.read_csv(historical, dtype=str, keep_default_na=False, low_memory=False)
    baseline = pair_set(prior)
    current = pair_set(relations)
    audits: dict[tuple[str,str],str] = {}
    if audit and audit.exists():
        aud = pd.read_csv(audit, dtype=str, keep_default_na=False)
        for _, row in aud.iterrows():
            ut, proc = str(row.get('UT','')).strip(), str(row.get('Nº processo FCP','')).strip()
            if ut and proc:
                audits[(ut,proc)] = str(row.get('Classificação','')).strip()
    historical_fns = set()
    if false_negatives and false_negatives.exists():
        fns = pd.read_csv(false_negatives, dtype=str, keep_default_na=False)
        for _, row in fns.iterrows():
            ut, proc = str(row.get('UT','')).strip(),str(row.get('Nº processo FCP','')).strip()
            if ut and proc:
                historical_fns.add((ut,proc))

    diff = []
    for ut, proc in sorted(baseline | current):
        key = (ut,proc)
        movement = ('PRESERVADA' if key in baseline and key in current else
                    'ADICIONADA' if key in current else 'REMOVIDA')
        known = audits.get(key, 'FN_HISTORICO' if key in historical_fns else 'NAO_AUDITADA')
        diff.append({'UT':ut, 'Nº PROCESSO NA FCP':proc,
                     'MOVIMENTO': movement, 'CLASSIFICACAO_HISTORICA':known,
                     'PRECISA_NOVA_AUDITORIA':movement != 'PRESERVADA'})
    detail = pd.DataFrame(diff)
    summary = {
        'historical_admin_pairs': len(baseline),
        'experimental_admin_pairs': len(current),
        'preserved_admin_pairs': len(baseline & current),
        'new_admin_pairs': len(current-baseline),
        'removed_admin_pairs': len(baseline-current),
        'known_historical_fns_recovered': len((current-baseline) & historical_fns),
        'known_historical_tps_removed': sum(audits.get(key) == 'TP'
                                           for key in baseline-current),
        'known_historical_fps_removed': sum(audits.get(key) == 'FP'
                                           for key in baseline-current),
        'new_pairs_not_in_historical_fn_list': len((current-baseline)-historical_fns),
        'precision_recall_f1_v3': 'NAO_CALCULADOS: requer auditoria na unidade desejada',
    }
    return detail, summary
