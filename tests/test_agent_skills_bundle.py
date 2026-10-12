"""Exercise packaged instructions against current public CLI/API contracts."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import yaml
import pytest

from tessera.agent_skills import AGENT_SKILL_BUNDLE_VERSION, list_agent_skill_names, read_agent_skill

ROOT = Path(__file__).resolve().parents[1]


def commands(skill, variables):
    text = read_agent_skill(skill)
    result = []
    for block in re.findall(r'```bash\n(.*?)```', text, re.S):
        for line in block.strip().splitlines():
            for key, value in variables.items():
                line = line.replace('"$' + key + '"', shlex.quote(str(value)))
            args = shlex.split(line)
            if args[0] == 'tessera':
                args = [sys.executable, '-m', 'tessera.cli', *args[1:]]
            elif args[0] == 'python':
                args[0] = sys.executable
            result.append(args)
    return result


def run(args, cwd):
    env = dict(os.environ, NO_COLOR='1', TESSERA_UPDATE_CHECK='0')
    env.pop('TESSERA_STORAGE_DIR', None)
    env['PYTHONPATH'] = str(ROOT)
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=60)


def snapshot(path):
    return {str(p.relative_to(path)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in path.rglob('*') if p.is_file()}


def test_bundle_names_metadata_and_loading_are_read_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = snapshot(tmp_path)
    names = list_agent_skill_names()
    assert isinstance(names, tuple) and len(names) == 5
    assert AGENT_SKILL_BUNDLE_VERSION == '1'
    for name in names:
        text = read_agent_skill(name)
        metadata = yaml.safe_load(text.split('---', 2)[1])
        assert metadata['name'] == name
        assert metadata['description']
        assert metadata['metadata']['tessera-bundle-version'] == AGENT_SKILL_BUNDLE_VERSION
        assert metadata['metadata']['tessera-package'] == 'tessera-agent-memory'
        assert len(text.encode()) < 12000
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('name', ['../config.py', '/etc/passwd', '', 'tessera-future-context', None, 17])
def test_unknown_or_pathlike_name_cannot_escape_packaged_resources(name):
    with pytest.raises(ValueError):
        read_agent_skill(name)


def test_skill_examples_run_a_real_scoped_workflow(tmp_path):
    project = tmp_path / 'project'; project.mkdir()
    existing = project / 'source.txt'; existing.write_text('Do not rewrite this source.\n')
    variables = {'PROJECT': project, 'STORE': project / 'memories', 'QUERY': 'sample service Python'}
    init, config = commands('tessera-init', variables)
    before = snapshot(project)
    dry = run(init, project); assert dry.returncode == 0, dry.stderr
    assert json.loads(dry.stdout)['applied'] is False
    assert snapshot(project) == before
    apply = run([a for a in init if a != '--dry-run'], project)
    assert apply.returncode == 0, apply.stderr
    assert json.loads(apply.stdout)['applied'] is True
    shown = run(config, project); assert shown.returncode == 0
    selection = json.loads(shown.stdout)['storage_selection']
    assert Path(selection['storage_dir']) == project / 'memories'

    written = run(commands('tessera-write', variables)[0], project)
    assert written.returncode == 0, written.stderr
    outcome = json.loads(written.stdout)
    assert outcome['persisted'] is True
    assert outcome['admission'] == 'accept'
    assert Path(outcome['filepath']).is_file()
    retrieved = run(commands('tessera-query', variables)[0], project)
    assert retrieved.returncode == 0, retrieved.stderr
    hits = json.loads(retrieved.stdout)
    assert hits and hits[0]['id'] == 'examples/runtime'
    assert hits[0]['provenance']['source']
    before_doctor = snapshot(project)
    for command in commands('tessera-doctor', variables):
        result = run(command, project)
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        if 'source_files_modified' in report:
            assert report['source_files_modified'] == 0
    assert snapshot(project) == before_doctor
    assert existing.read_text() == 'Do not rewrite this source.\n'


def test_write_rejection_is_not_a_saved_memory(tmp_path):
    command = commands('tessera-write', {'STORE': tmp_path})[0]
    command[command.index('--content') + 1] = ''
    result = run(command, tmp_path)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload['persisted'] is False and payload['admission'] == 'reject'
    assert not (tmp_path / 'examples/runtime.md').exists()


def test_project_aware_python_query_fallback_preserves_scope(tmp_path):
    from tessera import TesseraEngine
    from tessera.config import ConfigurationResolver
    project = tmp_path / 'project'; project.mkdir()
    init = commands('tessera-init', {'PROJECT': project})[0]
    assert run([a for a in init if a != '--dry-run'], project).returncode == 0
    resolved = ConfigurationResolver(environ={}).resolve(project=project)
    engine = TesseraEngine(configuration=resolved)
    engine.build_index()
    assert engine.retrieve_context('no invented evidence', top_n=5) == []


def test_benchmark_example_emits_real_sanity_metrics(tmp_path):
    command = commands('tessera-benchmark', {})[0]
    command[command.index('--output-dir') + 1] = str(tmp_path / 'sanity')
    result = run(command, ROOT)
    assert result.returncode == 0, result.stderr
    metrics = json.loads(result.stdout)
    assert metrics['queries'] == 4
    assert metrics['missing_evidence_check'] == 'passed'
    assert metrics['hit_at_3'] == 1.0
    assert (tmp_path / 'sanity').is_dir()
