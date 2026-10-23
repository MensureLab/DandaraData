import pandas as pd
from dandaradata.normalization import normalize_with_offsets
from dandaradata.evaluation import pair_set


def test_normalization_offsets_preserve_original_text():
    text = 'Vila União/Campina'
    norm, offsets = normalize_with_offsets(text)
    assert norm == 'vila uniao campina'
    assert text[offsets[11]:offsets[17]+1] == 'Campina'


def test_process_comparison_deduplicates_multi_crq_rows():
    df = pd.DataFrame([
        {'UT':'X','Nº PROCESSO NA FCP':'P1','COMUNIDADE':'VILA UNIÃO'},
        {'UT':'X','Nº PROCESSO NA FCP':'P1','COMUNIDADE':'CAMPINA'}
    ])
    assert pair_set(df) == {('X','P1')}
