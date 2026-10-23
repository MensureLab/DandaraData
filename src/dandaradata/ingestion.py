"""Load the user's historical input files with stable identifiers."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

FCP_COLUMNS = {'COMUNIDADE','UF','MUNICÍPIO','Nº DE CRQ','Nº PROCESSO NA FCP'}
ARTICLE_COLUMNS = {'UT','TI','X1','Y1','DE','X5','AB','X4','Y4'}
ARTICLE_FIELDS = ('TI', 'X1', 'Y1', 'DE', 'X5', 'AB', 'X4', 'Y4')


def read_data(path: str | Path, required: set[str]) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False, encoding='utf-8-sig')
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Colunas ausentes em {path}: {sorted(missing)}')
    return df


def load_inputs(articles: Path, fcp: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    adf = read_data(articles, ARTICLE_COLUMNS)
    fdf = read_data(fcp, FCP_COLUMNS)
    if adf['UT'].duplicated().any() or adf['UT'].eq('').any():
        raise ValueError('UT deve identificar unicamente os artigos e não pode estar vazio.')
    # Há pelo menos um registro histórico sem processo; preservá-lo com ID interno
    # para auditoria, mas não atribuir vínculo administrativo confirmado.
    return adf, fdf
