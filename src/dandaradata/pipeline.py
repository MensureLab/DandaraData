"""Run an experiment with independent, reproducible intermediate artifacts."""
from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import pandas as pd
from .ingestion import load_inputs
from .fcp_catalog import build_catalog
from .mention_detection import detect_mentions
from .entity_linking import evaluate
from .consolidation import build_relations, make_article_view
from .evaluation import compare_history


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):
            digest.update(chunk)
    return digest.hexdigest()


def run_experiment(config_path: Path, run_id_override: str | None = None) -> dict:
    config_path = config_path.resolve()
    root = config_path.parent.parent
    config = json.loads(config_path.read_text(encoding='utf-8'))
    run_id = run_id_override or config.get('experiment', {}).get('run_id','v3_experimental')
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('ID do experimento precisa conter apenas letras, números, _ e -.')
    in_cfg = config['inputs']
    articles_path = root/in_cfg['articles']
    fcp_path = root/in_cfg['fcp']
    out_dir = root/config.get('outputs',{}).get('root_dir','data/outputs')/run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    articles, fcp = load_inputs(articles_path, fcp_path)
    print(f'[1/5] Lidas entradas: {len(articles)} artigos e {len(fcp)} registros FCP')
    candidates, alias_index, catalog_df = build_catalog(fcp)
    print(f'[2/5] Candidatos de busca: {len(candidates)} (não são CRQs certificadas confirmadas)')
    mentions = detect_mentions(articles, alias_index,
                minimum_name_length=int(config.get('matching',{}).get('minimum_name_length',3)))
    print(f'[3/5] Menções localizadas: {len(mentions)}')
    decisions = evaluate(articles, candidates, mentions, config.get('matching',{}))
    relations = build_relations(decisions)
    print(f'[4/5] Relações propostas NÃO auditadas: {len(relations)}')
    catalog_df.to_csv(out_dir/'catalogo_candidatos.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame([asdict(m) for m in mentions], columns=list(asdict(mentions[0])) if mentions else
                 ['ut','article_id','field','candidate_id','name','matched_text','start','end','context']).to_csv(
                     out_dir/'mencoes_detectadas.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame([asdict(d) for d in decisions]).to_csv(out_dir/'decisoes_entity_linking.csv',index=False,encoding='utf-8-sig')
    relations.to_csv(out_dir/'relacoes_propostas.csv',index=False,encoding='utf-8-sig')
    make_article_view(articles, relations).to_csv(out_dir/'artigos_final_v3_teste.csv',index=False,encoding='utf-8-sig')
    print(f'[5/5] Saídas gravadas em {out_dir}')
    summary = {
        'version':'DandaraData Next - V3 experimental (sem NER)',
        'run_id': run_id,
        'config_sha256': sha256_file(config_path),
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'input_sha256': {'articles':sha256_file(articles_path), 'fcp':sha256_file(fcp_path)},
        'articles':len(articles),'fcp_records':len(fcp),'candidate_aliases':len(candidates),
        'mentions':len(mentions),'decisions':len(decisions),
        'proposed_relations':len(relations),
        'identity_status_in_proposals': relations['STATUS_IDENTIDADE'].value_counts().to_dict(),
        'decision_status':pd.Series([d.decision for d in decisions]).value_counts().to_dict(),
        'warning':'Nenhuma relacao V3 foi validada automaticamente como TP; nao calcular F1 sem referencia auditada.',
    }
    history = in_cfg.get('historical_output')
    if history and (root/history).exists():
        audit_path = root/in_cfg.get('audit','') if in_cfg.get('audit') else None
        fn_path = root/in_cfg.get('false_negatives','') if in_cfg.get('false_negatives') else None
        comparison, metrics = compare_history(relations, root/history, audit_path, fn_path)
        comparison.to_csv(out_dir/'comparacao_administrativa.csv',index=False,encoding='utf-8-sig')
        summary['administrative_comparison'] = metrics
    (out_dir/'config_utilizada.json').write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    (out_dir/'resumo_execucao.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary
