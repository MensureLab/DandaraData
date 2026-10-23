"""Command line: python -m dandaradata --config config/experiment.json"""
import argparse
import json
from pathlib import Path
from .pipeline import run_experiment


def main():
    parser = argparse.ArgumentParser(description='DandaraData Next: entity linking determinístico experimental')
    parser.add_argument('--config', default='config/experiment.json')
    parser.add_argument('--run-id', help='Diretório isolado desta execução')
    args = parser.parse_args()
    summary = run_experiment(Path(args.config), args.run_id)
    print(json.dumps({'run_id':summary['run_id'],
                      'proposed_relations':summary['proposed_relations'],
                      'administrative_comparison':summary.get('administrative_comparison',{})},
                     ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
