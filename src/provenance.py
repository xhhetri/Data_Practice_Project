"""Bind a completed pipeline run to raw inputs, code and generated artifacts."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
import pandas as pd
from src.analysis.clean import REPO_ROOT


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_outputs(metadata):
    for name, expected in metadata['outputs'].items():
        path = REPO_ROOT / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f'Artifact changed after this pipeline run: {name}; rerun the pipeline')


def write_metadata():
    manifest = pd.read_csv(REPO_ROOT / 'data/bronze/_manifest.csv').fillna('')
    if (manifest.status != 'real').any():
        raise ValueError('Analyst release requires all real source files; samples cannot be published as real results')
    annual = pd.read_csv(REPO_ROOT / 'data/processed/annual_master.csv')
    monthly = pd.read_csv(REPO_ROOT / 'data/processed/monthly_fuel_series.csv')
    code_hash = hashlib.sha256()
    paths = [REPO_ROOT / 'run_pipeline.py', REPO_ROOT / 'requirements-lock.txt']
    for folder in ['src', 'app', 'scripts', 'monitoring']:
        paths.extend((REPO_ROOT / folder).rglob('*.py'))
    paths.append(REPO_ROOT / 'dashboard/template.html')
    for path in sorted(paths):
        if path.exists():
            code_hash.update(str(path.relative_to(REPO_ROOT)).encode())
            code_hash.update(path.read_bytes())
    identity = hashlib.sha256((code_hash.hexdigest() + ''.join(manifest.sha256)).encode()).hexdigest()[:16]
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO_ROOT, capture_output=True, text=True)
    metadata = {'run_id': identity, 'built_at': datetime.now(timezone.utc).isoformat(),
                'code_sha256': code_hash.hexdigest(), 'git_revision': revision.stdout.strip(),
                'sources': manifest.to_dict('records'),
                'coverage': {'annual_start': int(annual.year.min()), 'annual_end': int(annual.year.max()),
                             'sales_start': monthly.date.min(), 'sales_end': monthly.date.max(),
                             'annual_rows': len(annual), 'monthly_rows': len(monthly)},
                'packages': {name: version(name) for name in ['pandas', 'numpy', 'scikit-learn', 'statsmodels', 'streamlit']}}
    metrics_path = REPO_ROOT / 'reports/model_results/metrics.json'
    metrics = json.loads(metrics_path.read_text(encoding='utf-8'))
    metrics['_run'] = {'run_id': identity, 'code_sha256': code_hash.hexdigest()}
    metrics_path.write_text(json.dumps(metrics, indent=2, allow_nan=False), encoding='utf-8')
    artifacts = list((REPO_ROOT / 'data/processed').glob('*.csv'))
    artifacts.extend((REPO_ROOT / 'reports/model_results').glob('*'))
    artifacts.append(REPO_ROOT / 'reports/validation/emission_factor_check.csv')
    metadata['outputs'] = {str(p.relative_to(REPO_ROOT)).replace('\\', '/'): sha256(p) for p in artifacts if p.is_file()}
    (REPO_ROOT / 'reports/run_metadata.json').write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding='utf-8')
    return metadata
