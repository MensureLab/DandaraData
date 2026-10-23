import pandas as pd
from dandaradata.fcp_catalog import build_catalog
from dandaradata.mention_detection import detect_mentions
from dandaradata.entity_linking import evaluate
from dandaradata.consolidation import build_relations
from dandaradata.ingestion import ARTICLE_FIELDS


def article(ut, text):
    row = {'UT':ut}
    row.update({col:'' for col in ARTICLE_FIELDS})
    row['Y4'] = text
    return row


def test_compound_beats_isolated_homonym_with_shared_context():
    fcp = pd.DataFrame([
        {'COMUNIDADE':'VILA UNIÃO / CAMPINA','UF':'PA','MUNICÍPIO':'SALVATERRA',
         'Nº PROCESSO NA FCP':'P-COMPOSTO','Nº DE CRQ':'2'},
        {'COMUNIDADE':'CAMPINA','UF':'PA','MUNICÍPIO':'SALVATERRA',
         'Nº PROCESSO NA FCP':'P-ISOLADO','Nº DE CRQ':'1'},
    ])
    adf = pd.DataFrame([article('UT584',
        'Pesquisa na comunidade quilombola Vila União/Campina, em Salvaterra, Pará.')])
    candidates, idx, _ = build_catalog(fcp)
    mentions = detect_mentions(adf,idx)
    decisions = evaluate(adf,candidates,mentions,{
        'minimum_score':5,'require_geographic_evidence':True,'homonym_margin':2})
    accepted = build_relations(decisions)
    assert set(accepted['COMUNIDADE_CANDIDATA']) == {'vila uniao','campina'}
    assert set(accepted['Nº PROCESSO NA FCP']) == {'P-COMPOSTO'}
    assert all(accepted['STATUS_RELACAO'] == 'PROPOSTA_NAO_AUDITADA')


def test_does_not_match_short_word_inside_longer_word():
    fcp = pd.DataFrame([{'COMUNIDADE':'CAMPINA','UF':'PA','MUNICÍPIO':'SALVATERRA',
        'Nº PROCESSO NA FCP':'P-1','Nº DE CRQ':'1'}])
    adf = pd.DataFrame([article('UT1','O município de Campinas possui muitos moradores.')])
    _, idx, _ = build_catalog(fcp)
    assert detect_mentions(adf,idx) == []


def test_independent_short_name_is_preserved():
    fcp = pd.DataFrame([
       {'COMUNIDADE':'PEDRO CUBAS','UF':'SP','MUNICÍPIO':'ELDORADO',
        'Nº PROCESSO NA FCP':'P-1','Nº DE CRQ':'1'},
       {'COMUNIDADE':'PEDRO CUBAS DE CIMA','UF':'SP','MUNICÍPIO':'ELDORADO',
        'Nº PROCESSO NA FCP':'P-2','Nº DE CRQ':'1'}
    ])
    adf = pd.DataFrame([article('UT550',
       'Quilombolas das comunidades Pedro Cubas e Pedro Cubas de Cima em Eldorado, São Paulo.')])
    candidates, idx, _ = build_catalog(fcp)
    decisions = evaluate(adf,candidates,detect_mentions(adf,idx),
       {'minimum_score':5,'require_geographic_evidence':True,'homonym_margin':2})
    assert len(build_relations(decisions)) == 2
