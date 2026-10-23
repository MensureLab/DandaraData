import pandas as pd
from dandaradata.fcp_catalog import build_catalog, split_name


def test_compound_record_yields_distinct_provisional_entities():
    fcp = pd.DataFrame([dict(COMUNIDADE='VILA UNIÃO / CAMPINA', UF='PA',
        MUNICÍPIO='SALVATERRA', **{'Nº PROCESSO NA FCP':'01420.001847/2006-27','Nº DE CRQ':'2'})])
    candidates, aliases, _ = build_catalog(fcp)
    assert {c.name for c in candidates} == {'vila uniao','campina'}
    assert len({c.entity_id for c in candidates}) == 2
    assert all(c.identity_status == 'INDIVIDUALIZACAO_PROVISORIA' for c in candidates)


def test_one_crq_multiple_spellings_is_one_entity():
    fcp = pd.DataFrame([dict(COMUNIDADE='AÇU / ASSU', UF='RN',
        MUNICÍPIO='AÇU', **{'Nº PROCESSO NA FCP':'P1','Nº DE CRQ':'1'})])
    candidates, _, _ = build_catalog(fcp)
    assert len(candidates) == 2
    assert len({c.entity_id for c in candidates}) == 1


def test_aggregate_never_expands_by_n_crq():
    fcp = pd.DataFrame([dict(COMUNIDADE='KALUNGA', UF='GO',
        MUNICÍPIO='CAVALCANTE', **{'Nº PROCESSO NA FCP':'P2','Nº DE CRQ':'39'})])
    candidates, _, _ = build_catalog(fcp)
    assert len(candidates) == 1
    assert candidates[0].identity_status == 'REGISTRO_AGREGADO_NAO_INDIVIDUALIZADO'


def test_split_fragments_are_not_certified_identities():
    assert split_name('PACA E ANINGAL') == ['paca','aningal']
