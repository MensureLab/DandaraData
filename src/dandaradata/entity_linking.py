"""Transparent, deterministic and inspectable evidence-based entity linking."""
from __future__ import annotations
from collections import defaultdict
import json
import re
from typing import Iterable
import pandas as pd
from .models import Candidate, Decision, Mention
from .normalization import normalize, contains_phrase
from .ingestion import ARTICLE_FIELDS

STATE_NAMES = {
    'AC':'acre', 'AL':'alagoas', 'AP':'amapa', 'AM':'amazonas',
    'BA':'bahia', 'CE':'ceara', 'DF':'distrito federal',
    'ES':'espirito santo', 'GO':'goias', 'MA':'maranhao',
    'MT':'mato grosso', 'MS':'mato grosso do sul', 'MG':'minas gerais',
    'PA':'para', 'PB':'paraiba', 'PR':'parana', 'PE':'pernambuco',
    'PI':'piaui', 'RJ':'rio de janeiro', 'RN':'rio grande do norte',
    'RS':'rio grande do sul', 'RO':'rondonia', 'RR':'roraima',
    'SC':'santa catarina', 'SP':'sao paulo', 'SE':'sergipe', 'TO':'tocantins'
}
CONTEXT_WORDS = ('quilombo','quilombola','quilombos','quilombolas',
                 'comunidade','comunidades','territorio quilombola')

# Termos potencialmente ambíguos identificados durante o desenvolvimento histórico.
# O uso de uma lista explicita de casos é hipótese de partida, não verdade de referência.
AMBIGUOUS_ALIASES = {
    'franca','ovo','um','kalunga','base','peixes','forte','alto','piaui',
    'floresta','america','brasileira','araca','jatoba','jurema',
    'aroeira','piloes','mata','mocambo','solidao','crioulo','corte',
    'palmeiras','porcoes','porcao','batalha','barreiras','sao paulo',
    'pedra do sal','chapada','capivari','jequitiba'
}

def anchored_mention(m: Mention) -> bool:
    """Check nearby explicit quilombola cues (not just anywhere in the abstract)."""
    norm = normalize(m.context)
    alias = normalize(m.matched_text)
    tokens = norm.split()
    phrase = alias.split()
    for i in range(len(tokens) - len(phrase) + 1):
        if tokens[i:i+len(phrase)] != phrase:
            continue
        before = tokens[max(0,i-5):i]
        after = tokens[i+len(phrase):i+len(phrase)+5]
        if any(x in before for x in ('comunidade','quilombo','quilombola','povoado')):
            return True
        if any(x in after for x in ('quilombo','quilombola','comunidade')):
            return True
    return False


def state_found(uf: str, article_text: str, normalized_text: str) -> bool:
    state = STATE_NAMES.get(uf.upper())
    if not state:
        return False
    # Do not count the common preposition "para" as the Brazilian state Pará.
    if uf.upper() == 'PA':
        return bool(re.search(r'(?<!\w)pará(?!\w)', article_text.lower()))
    return contains_phrase(normalized_text, state)


def evaluate(articles: pd.DataFrame, candidates: list[Candidate],
             mentions: list[Mention], matching: dict) -> list[Decision]:
    by_candidate = {c.candidate_id:c for c in candidates}
    by_ut = {str(row['UT']): row for _, row in articles.iterrows()}
    mention_groups: dict[tuple[str,str],list[Mention]] = defaultdict(list)
    aliases_by_record: dict[tuple[str,int],set[str]] = defaultdict(set)
    for m in mentions:
        mention_groups[(m.ut, m.candidate_id)].append(m)
        aliases_by_record[(m.ut, by_candidate[m.candidate_id].record_id)].add(m.name)

    # For homonym resolution, collect all candidate IDs actually mentioned.
    same_name: dict[tuple[str,str], list[str]] = defaultdict(list)
    for ut, cid in mention_groups:
        same_name[(ut, by_candidate[cid].name)].append(cid)

    preliminary: dict[tuple[str,str],dict] = {}
    for (ut, cid), observed in mention_groups.items():
        candidate = by_candidate[cid]
        article = by_ut[ut]
        raw_text = ' '.join(str(article.get(f, '')) for f in ARTICLE_FIELDS)
        norm_text = normalize(raw_text)
        municipalities = [s for s in candidate.municipality.split(' | ') if s]
        found_cities = [city for city in municipalities if contains_phrase(norm_text, city)]
        found_state = state_found(candidate.uf, raw_text, norm_text)
        ctx = any(any(contains_phrase(normalize(m.context), word) for word in CONTEXT_WORDS)
                  for m in observed)
        co_names = aliases_by_record[(ut,candidate.record_id)] - {candidate.name}
        ambiguity_anchored = any(anchored_mention(m) for m in observed)
        co_name_support = len(co_names) > 0 and candidate.n_crq > 1

        signals = {
            'nome_detectado': True,
            'municipios_encontrados': found_cities,
            'estado_encontrado': found_state,
            'contexto_quilombola_proximo': ctx,
            'outras_partes_mesmo_registro': sorted(co_names),
            'identidade_comunitaria': candidate.identity_status,
            'nome_ambiguo_com_indicador_proximo': ambiguity_anchored,
        }
        weights = matching.get('weights', {})
        score = (float(weights.get('name',3))
                 + (float(weights.get('municipality',4)) if found_cities else 0)
                 + (float(weights.get('state',1)) if found_state else 0)
                 + (float(weights.get('context',1)) if ctx else 0)
                 + (float(weights.get('cooccurrence',2)) if co_name_support else 0))
        preliminary[(ut,cid)] = dict(score=score,signals=signals, observed=observed,
                                     geo_ok=bool(found_cities or found_state),
                                     city_found=bool(found_cities))

    # Penalize nested name mentions ONLY when there are no independent occurrences
    # (important for Pedro Cubas and Pedro Cubas de Cima).
    by_field: dict[tuple[str,str],list[Mention]] = defaultdict(list)
    for m in mentions:
        by_field[(m.ut,m.field)].append(m)
    for (ut,cid), p in preliminary.items():
        c = by_candidate[cid]
        independent = any(not any(
            other.candidate_id != m.candidate_id
            and by_candidate[other.candidate_id].uf == c.uf
            and len(by_candidate[other.candidate_id].name) > len(c.name)
            and other.start <= m.start and m.end <= other.end
            for other in by_field[(m.ut,m.field)]
        ) for m in p['observed'])
        p['signals']['mencao_independente_de_nomes_maiores'] = independent
        if not independent:
            p['score'] -= float(matching.get('weights', {}).get('nested_only_penalty',3))

    # Distinct records with an identical alias compete for the same mention.
    for (ut, alias), ids in same_name.items():
        distinct_records = {by_candidate[cid].record_id for cid in ids}
        if len(distinct_records) < 2:
            continue
        scores = sorted(((preliminary[(ut,cid)]['score'], cid) for cid in ids), reverse=True)
        top = scores[0][0]
        second = scores[1][0]
        for _, cid in scores:
            p = preliminary[(ut,cid)]
            p['signals']['homonimos_no_corpus'] = len(distinct_records)
            # Compare actual scores; no automatic acceptance on weak/tied evidence.
            p['homonym_uncertain'] = (top - second < float(matching.get('homonym_margin', 2)))
            p['homonym_weaker'] = (p['score'] < top)

    decisions: list[Decision] = []
    min_score = float(matching.get('minimum_score', 5))
    require_geo = bool(matching.get('require_geographic_evidence', True))
    for (ut,cid), p in preliminary.items():
        candidate = by_candidate[cid]
        reasons = []
        if candidate.name in AMBIGUOUS_ALIASES and not p['signals']['nome_ambiguo_com_indicador_proximo']:
            decision = 'REVISAR'
            reasons.append('nome_ambiguo_sem_contexto_explicito_proximo')
        elif not candidate.process:
            decision = 'REVISAR'
            reasons.append('numero_processo_fcp_ausente')
        elif p['score'] < min_score:
            decision = 'REJEITADA'
            reasons.append('pontuacao_insuficiente')
        elif require_geo and not p['geo_ok']:
            decision = 'REVISAR'
            reasons.append('sem_evidencia_geografica')
        elif p.get('homonym_uncertain', False):
            decision = 'REVISAR'
            reasons.append('homonimos_nao_resolvidos')
        elif p.get('homonym_weaker', False):
            decision = 'REVISAR'
            reasons.append('outra_entidade_com_mesma_mencao_tem_evidencia_maior')
        else:
            decision = 'PROPOSTA'
            reasons.append('evidencias_atingiram_criterios')
        if candidate.identity_status == 'REGISTRO_AGREGADO_NAO_INDIVIDUALIZADO':
            reasons.append('identidade_comunitaria_nao_individualizada')
        elif candidate.identity_status == 'INDIVIDUALIZACAO_PROVISORIA':
            reasons.append('individualizacao_provisoria_sem_confirmacao_externa')
        p['signals']['pontuacao'] = p['score']
        decisions.append(Decision(
            ut=ut, article_id=p['observed'][0].article_id,
            candidate_id=cid, entity_id=candidate.entity_id, process=candidate.process,
            source_name=candidate.source_name, name=candidate.name,
            uf=candidate.uf, municipality=candidate.municipality,
            n_crq=candidate.n_crq, identity_status=candidate.identity_status,
            decision=decision, score=p['score'],
            evidences=json.dumps(p['signals'], ensure_ascii=False, sort_keys=True),
            reasons=json.dumps(reasons, ensure_ascii=False),
            mention_fields=' | '.join(sorted({m.field for m in p['observed']})),
            mention_count=len(p['observed']),
        ))
    return sorted(decisions, key=lambda d:(d.article_id,d.process,d.name))
