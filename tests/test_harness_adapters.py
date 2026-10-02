"""Frozen canonical agreement and deterministic registration for issue #71."""
import json
from pathlib import Path
from dataclasses import FrozenInstanceError
import pytest
from tessera.canonical import parse_and_normalize
from tessera.harness_adapters import DEFAULT_HARNESS_ADAPTERS, HarnessAdapter, HarnessAdapterRegistry

FIXTURES = json.loads((Path(__file__).parent / 'fixtures/harness_adapters/canonical_baseline.json').read_text())


@pytest.mark.parametrize('case', FIXTURES, ids=[c['path'] for c in FIXTURES])
def test_exact_canonical_agreement_with_main(case):
    result = parse_and_normalize(case['raw_text'], '/source/' + case['path'], '/source').to_dict()
    result['temporal']['indexed_at'] = '<runtime-index-time>'
    assert result == case['canonical']


@pytest.mark.parametrize('filename,adapter,harness', [
    ('AGENTS.md', 'agents', None), ('aGeNtS.mD', 'agents', None),
    ('CLAUDE.md', 'claude', 'claude'), ('GEMINI.md', 'gemini', 'gemini'),
    ('copilot-instructions.md', 'copilot', 'copilot'), ('SKILL.md', 'skill', None),
    ('sample.skill.md', 'skill', None), ('sk_sample.md', 'skill', None),
    ('AGENTS.md.backup', 'generic', None), ('CLAUDE.md.txt', 'generic', None),
    ('unknown-guide.md', 'generic', None),
])
def test_inspect_selection_and_filename_evidence(filename, adapter, harness):
    actual = DEFAULT_HARNESS_ADAPTERS.inspect('/root/nested/' + filename)
    assert actual.adapter_id == adapter
    assert actual.harness == harness
    assert actual.evidence == 'filename:' + filename
    assert actual.to_dict()['document_type'] == actual.document_type


def test_explicit_instruction_on_unknown_file_stays_drawerless():
    raw = '---\ndocument_type: harness_instructions\n---\nKeep source text.'
    meta = parse_and_normalize(raw, '/source/unknown.md', '/source')
    assert meta.classification.drawer is None
    assert meta.metadata_origin['document_type'] == 'explicit'
    assert meta.scope.harness is None
    assert meta.metadata_origin['scope.harness'] == 'default'


def test_custom_registration_changes_only_explicit_consumer_not_default_registry():
    adapter = HarnessAdapter('custom', filenames=('PROJECT_RULES.md',), harness='custom')
    registry = DEFAULT_HARNESS_ADAPTERS.register(adapter)
    assert DEFAULT_HARNESS_ADAPTERS.inspect('PROJECT_RULES.md').adapter_id == 'generic'
    raw = '# Build\nRun tests.'
    before = parse_and_normalize(raw, '/source/PROJECT_RULES.md', '/source')
    after = parse_and_normalize(raw, '/source/PROJECT_RULES.md', '/source', adapter_registry=registry)
    assert after.classification.drawer is None
    assert after.classification.kind == 'instruction'
    assert after.scope.harness == 'custom'
    assert after.metadata_origin['scope.harness'] == 'inferred'
    assert after.source == before.source
    assert after.identity == before.identity
    assert after.quality == before.quality


def test_empty_registry_explicitly_selects_generic_fallback():
    result = parse_and_normalize('Text', '/source/CLAUDE.md', '/source', adapter_registry=HarnessAdapterRegistry())
    assert result.classification.document_type == 'memory'
    assert result.scope.harness is None


def test_registry_is_immutable_and_order_independent():
    a = HarnessAdapter('z', filenames=['A.md'])
    b = HarnessAdapter('a', filenames=['B.md'])
    x = HarnessAdapterRegistry([a, b]); y = HarnessAdapterRegistry([b, a])
    assert x == y
    assert a.filenames == ('a.md',)
    with pytest.raises(FrozenInstanceError):
        x.adapters = ()
    with pytest.raises(FrozenInstanceError):
        a.harness = 'changed'


def test_ambiguous_matching_fails_deterministically_instead_of_implying_authority():
    custom = HarnessAdapter('also-agents', filenames=('AGENTS.md',))
    registry = DEFAULT_HARNESS_ADAPTERS.register(custom)
    with pytest.raises(ValueError, match='Ambiguous instruction adapters: agents, also-agents'):
        registry.inspect('/source/AGENTS.md')
    with pytest.raises(ValueError, match='Ambiguous'):
        parse_and_normalize('Source', '/source/AGENTS.md', '/source', adapter_registry=registry)


@pytest.mark.parametrize('args', [
    {'adapter_id': ''}, {'adapter_id': 'empty'},
    {'adapter_id': 'invalid', 'filenames': 'AGENTS.md'},
    {'adapter_id': 'invalid', 'filenames': ('dir/AGENTS.md',)},
    {'adapter_id': 'invalid', 'filenames': ('AGENTS.md',), 'document_type': 'memory'},
    {'adapter_id': 'invalid', 'filenames': ('AGENTS.md',), 'harness': ''},
])
def test_invalid_rules_are_rejected(args):
    with pytest.raises(ValueError):
        HarnessAdapter(**args)


def test_duplicate_names_and_reserved_generic_cannot_replace_fallback():
    a = HarnessAdapter('one', filenames=('ONE.md',))
    with pytest.raises(ValueError):
        HarnessAdapterRegistry((a, a))
    with pytest.raises(ValueError):
        HarnessAdapterRegistry((HarnessAdapter('generic', filenames=('OTHER.md',)),))
    with pytest.raises(TypeError):
        HarnessAdapterRegistry(('not an adapter',))


def test_explicit_source_fields_win_over_adapter_defaults():
    raw = '---\ndocument_type: reference\nkind: factual\nscope:\n  harness: source-owned\n  path: ./limited/**\n  level: folder\n---\nSource.'
    result = parse_and_normalize(raw, '/source/CLAUDE.md', '/source')
    assert result.classification.document_type == 'reference'
    assert result.scope.harness == 'source-owned'
    assert result.scope.path == './limited/**'
    assert result.scope.level == 'folder'
    assert all(result.metadata_origin[k] == 'explicit' for k in ('document_type','kind','scope.harness','scope.path','scope.level'))
