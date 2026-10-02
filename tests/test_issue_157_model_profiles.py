"""Offline acceptance scenarios for typed model profiles (Issue #157)."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from tessera import TesseraEngine
from tessera.config import (
    ConfigurationError, ConfigurationResolver, GlobalRegistry, ProjectConfig,
    StoreRecord, apply_init_plan, build_init_plan, unregister_global_store,
    write_global_registry, write_project_config,
)
from tessera.init_flow import InitRequest, apply_initialization_plan, build_initialization_plan
from tessera.model_profiles import (
    Capability, CredentialReference, EmbeddingProfile, GenerationProfile,
    ModelAdapterRegistry, ModelAvailabilityError, ModelProfile, ModelProfiles,
    ModelReference, RerankingProfile,
)

STORE_A = "00000000-0000-0000-0000-000000000001"
STORE_B = "00000000-0000-0000-0000-000000000002"
SECRET = "do-not-persist-test-credential"


def profiles():
    return ModelProfiles.from_mapping({
        "embeddings": {
            "local-default": {"provider": "local", "backend": "sentence-transformers", "model": "example/encoder", "dimensions": 32, "normalization": "l2"},
            "cloud": {"provider": "google", "model": "example-embedding", "credential": {"source": "env", "variable": "TEST_MODEL_KEY"}},
        },
        "generation": {
            "fast": {"provider": "openai-compatible", "model": "example-fast", "endpoint": "https://api.example.test/v1", "credential": {"source": "env", "variable": "TEST_MODEL_KEY"}},
            "reasoning": {"provider": "anthropic", "model": "example-reasoning"},
        },
        "reranking": {
            "local-default": {"provider": "local", "backend": "sentence-transformers", "model": "./model-files/cross-encoder"},
        },
    })


def project(tmp_path, model_profiles=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    config = ProjectConfig(tmp_path, tmp_path / ".tessera/config.yaml", StoreRecord(STORE_A, str(tmp_path / "memories")), models=model_profiles or profiles())
    write_project_config(config)
    return config


def test_typed_capabilities_and_reused_names_are_independent():
    models = profiles()
    embedding = models.resolve(ModelReference("embedding", "local-default"))
    reranking = models.resolve(ModelReference("reranking", "local-default"))
    assert type(embedding) is EmbeddingProfile
    assert type(reranking) is RerankingProfile
    assert embedding is not reranking
    assert type(models.resolve(ModelReference("generation", "fast"))) is GenerationProfile
    with pytest.raises(ConfigurationError, match="wrong capability"):
        ModelProfiles(generation={"wrong": embedding})
    with pytest.raises(ConfigurationError, match="unknown model profile"):
        models.resolve(ModelReference("generation", "local-default"))
    with pytest.raises(ConfigurationError, match="typed ModelReference"):
        models.resolve("local-default")
    with pytest.raises(ConfigurationError):
        ModelProfile("local", "example")
    with pytest.raises(TypeError):
        models.embeddings["new"] = embedding


def test_changing_generation_does_not_change_embedding_identity():
    before = profiles()
    mapping = before.to_mapping()
    mapping["generation"]["fast"]["model"] = "other-model"
    after = ModelProfiles.from_mapping(mapping)
    assert before.embeddings == after.embeddings
    assert before.reranking == after.reranking
    assert before.generation != after.generation


@pytest.mark.parametrize("provider,capability,extra", [
    ("local", "embeddings", {"backend": "sentence-transformers"}),
    ("google", "embeddings", {}), ("google", "generation", {}),
    ("openai", "embeddings", {}), ("openai", "generation", {}),
    ("openai-compatible", "embeddings", {"endpoint": "http://localhost:8000/v1"}),
    ("openai-compatible", "generation", {"endpoint": "https://api.example.test/v1"}),
    ("anthropic", "generation", {}),
    ("local", "reranking", {"backend": "sentence-transformers"}),
    ("custom", "reranking", {"adapter": "application-ranker"}),
])
def test_provider_class_schema_matrix(provider, capability, extra):
    raw = {capability: {"chosen": {"provider": provider, "model": "example", **extra}}}
    assert ModelProfiles.from_mapping(raw).to_mapping() == raw


@pytest.mark.parametrize("raw", [
    None, [], {"unknown": {}}, {"embeddings": []},
    {"generation": {"bad name": {"provider": "openai", "model": "example"}}},
    {"generation": {"fast": {"provider": "unknown", "model": "example"}}},
    {"generation": {"fast": {"provider": [], "model": "example"}}},
    {"embeddings": {"fast": {"provider": "anthropic", "model": "example"}}},
    {"reranking": {"fast": {"provider": "google", "model": "example"}}},
    {"generation": {"fast": {"provider": "openai", "model": "example", "dimensions": 32}}},
    {"generation": {"fast": {"provider": "openai", "model": "example", "normalization": "l2"}}},
    {"generation": {"fast": {"provider": "openai", "model": "example", "device": "cpu"}}},
    {"embeddings": {"fast": {"provider": "local", "model": "example"}}},
    {"generation": {"fast": {"provider": "custom", "model": "example"}}},
    {"generation": {"fast": {"provider": "openai-compatible", "model": "example"}}},
])
def test_invalid_schema_has_actionable_configuration_error(raw):
    with pytest.raises(ConfigurationError):
        ModelProfiles.from_mapping(raw)


@pytest.mark.parametrize("dimensions", [True, False, 0, -1, 1.5, "32", [], {}])
def test_dimensions_are_strictly_positive_integers(dimensions):
    with pytest.raises(ConfigurationError, match="dimensions"):
        EmbeddingProfile("openai", "example", dimensions=dimensions)


@pytest.mark.parametrize("credential", [
    SECRET, {"source": "env", "variable": "TEST_MODEL_KEY", "value": SECRET},
    {"source": "inline", "value": SECRET}, {"source": "env", "variable": "not a variable"},
    {"source": "file", "variable": "TEST_MODEL_KEY"}, None,
])
def test_inline_or_invalid_credentials_fail_without_echo(credential):
    raw = {"generation": {"fast": {"provider": "openai", "model": "example", "credential": credential}}}
    with pytest.raises(ConfigurationError) as error:
        ModelProfiles.from_mapping(raw)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("field", ["api_key", "token", "password", "headers", SECRET])
def test_unsupported_secret_fields_are_not_echoed(field):
    with pytest.raises(ConfigurationError) as error:
        ModelProfiles.from_mapping({"generation": {"fast": {"provider": "openai", "model": "example", field: SECRET}}})
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("endpoint", [
    "https://user:do-not-persist-test-credential@example.test/v1",
    "https://example.test/v1?key=do-not-persist-test-credential",
    "https://example.test/v1#do-not-persist-test-credential",
    "http://example.test/v1", "https:///no-host", "https://example.test:bad/v1",
])
def test_unsafe_endpoint_is_rejected_without_echo(endpoint):
    with pytest.raises(ConfigurationError) as error:
        GenerationProfile("openai-compatible", "example", endpoint=endpoint)
    assert SECRET not in str(error.value)


def test_local_profiles_need_no_credentials_and_never_use_them():
    class DenyEnvironment(dict):
        def get(self, *_):
            pytest.fail("local model preparation read environment credentials")
    registry = ModelAdapterRegistry()
    registry.register(Capability.EMBEDDING, "local", lambda p: p.model, name="sentence-transformers")
    assert registry.prepare(profiles(), ModelReference("embedding", "local-default"), environ=DenyEnvironment()) == "example/encoder"
    with pytest.raises(ConfigurationError, match="local profiles"):
        EmbeddingProfile("local", "example", backend="sentence-transformers", credential=CredentialReference("env", "TEST_MODEL_KEY"))


def test_missing_credential_is_late_explicit_and_secret_free():
    registry = ModelAdapterRegistry()
    registry.register(Capability.EMBEDDING, "google", lambda p: p.identity())
    selected = ModelReference("embedding", "cloud")
    models = profiles()  # no credential read, even though a remote profile exists
    for env in ({}, {"TEST_MODEL_KEY": "  "}):
        with pytest.raises(ModelAvailabilityError) as error:
            registry.prepare(models, selected, environ=env)
        assert error.value.code == "missing_credential"
    result = registry.prepare(models, selected, environ={"TEST_MODEL_KEY": SECRET})
    assert result["model"] == "example-embedding"
    assert SECRET not in json.dumps(result)
    assert SECRET not in repr(models)
    assert SECRET not in json.dumps(models.to_mapping())


def test_unavailable_adapter_and_dependency_are_actionable_and_isolated():
    registry = ModelAdapterRegistry()
    models = profiles()
    with pytest.raises(ModelAvailabilityError) as error:
        registry.prepare(models, ModelReference("embedding", "local-default"), environ={})
    assert error.value.code == "adapter_unavailable"

    def unavailable(_):
        raise ImportError(SECRET)
    registry.register(Capability.EMBEDDING, "local", unavailable, name="sentence-transformers")
    with pytest.raises(ModelAvailabilityError) as error:
        registry.prepare(models, ModelReference("embedding", "local-default"))
    assert error.value.code == "optional_dependency_unavailable"
    assert SECRET not in str(error.value)
    registry.register(Capability.GENERATION, "anthropic", lambda _: "ready")
    assert registry.prepare(models, ModelReference("generation", "reasoning")) == "ready"


def test_custom_adapter_is_explicit_and_never_loaded_from_a_module_string():
    model_profiles = ModelProfiles(reranking={"application": RerankingProfile("custom", "application-v1", adapter="application-ranker")})
    registry = ModelAdapterRegistry()
    registry.register("reranking", "custom", lambda profile: profile.model, name="application-ranker")
    assert registry.prepare(model_profiles, ModelReference("reranking", "application")) == "application-v1"
    with pytest.raises(ConfigurationError, match="already registered"):
        registry.register("reranking", "custom", lambda _: None, name="application-ranker")


def test_identity_and_mutable_alias_diagnostics_do_not_claim_verification(tmp_path):
    profile = EmbeddingProfile("local", "./model-files/encoder", backend="sentence-transformers", device="cpu", dimensions=32, normalization="l2")
    assert profile.local_path(tmp_path) == tmp_path / "model-files/encoder"
    assert "mutable_or_unpinned_model" in profile.reproducibility_warnings()
    for revision in ("main", "latest", "v1.0", None):
        assert "mutable_or_unpinned_model" in replace(profile, model_revision=revision).reproducibility_warnings()
    declared = replace(profile, model_revision="a" * 40, fingerprint="sha256:" + "b" * 64)
    assert declared.reproducibility_warnings() == ("declared_identity_not_verified",)
    assert declared.identity()["dimensions"] == 32
    assert declared.identity()["capability"] == "embedding"
    assert replace(profile, model="organization/encoder").local_path(tmp_path) is None
    assert not (tmp_path / "model-files").exists()


def test_project_round_trip_preserves_references_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_MODEL_KEY", SECRET)
    config = project(tmp_path)
    loaded = ProjectConfig.load(config.config_path)
    assert loaded.models == config.models
    selected = ConfigurationResolver(cwd=tmp_path, environ={}).resolve()
    assert selected.models == config.models
    assert SECRET not in json.dumps(selected.to_dict())
    assert SECRET not in config.config_path.read_text()
    assert selected.models.generation["fast"].credential.variable == "TEST_MODEL_KEY"
    assert selected.storage_dir == str(tmp_path / "memories")
    write_project_config(loaded)
    assert ProjectConfig.load(config.config_path).models == config.models


def test_named_global_profiles_never_mix_with_projects_or_other_stores(tmp_path):
    registry_path = tmp_path / "registry.yaml"
    local = ModelProfiles(embeddings={"same": EmbeddingProfile("local", "example/global", backend="sentence-transformers")})
    remote = ModelProfiles(generation={"same": GenerationProfile("google", "example/remote")})
    write_global_registry(GlobalRegistry(registry_path, {
        "first": StoreRecord(STORE_A, str(tmp_path / "one")),
        "second": StoreRecord(STORE_B, str(tmp_path / "two")),
    }, {"first": local, "second": remote}))
    loaded = GlobalRegistry.load(registry_path)
    assert loaded.models == {"first": local, "second": remote}
    resolver = ConfigurationResolver(cwd=tmp_path, environ={}, registry_path=registry_path)
    first = resolver.resolve(global_name="first")
    second = resolver.resolve(global_name="second")
    assert first.models == local and second.models == remote
    assert len(first.source_roots) == 1 and first.source_roots[0].path == str(tmp_path / "one")
    project_config = project(tmp_path / "project")
    selected = ConfigurationResolver(cwd=project_config.project_root, environ={}, registry_path=registry_path).resolve(global_name="first")
    assert selected.source == "project_config" and selected.models == project_config.models
    assert resolver.resolve(explicit=str(tmp_path / "one")).models == ModelProfiles()
    unregister_global_store("second", registry_path)
    assert GlobalRegistry.load(registry_path).models == {"first": local}


def test_global_reinit_preserves_each_store_models(tmp_path):
    path = tmp_path / "registry.yaml"
    write_global_registry(GlobalRegistry(path, {"first": StoreRecord(STORE_A, str(tmp_path / "one")), "second": StoreRecord(STORE_B, str(tmp_path / "two"))}, {"first": profiles(), "second": profiles()}))
    plan = build_init_plan(mode="global", store_path=str(tmp_path / "moved"), registry_name="first", registry_path=path)
    selected = apply_init_plan(plan)
    assert selected.models == profiles()
    assert GlobalRegistry.load(path).models == {"first": profiles(), "second": profiles()}
    request = InitRequest(mode="global", store_path=str(tmp_path / "moved"), registry_name="first", registry_path=str(path))
    newer = build_initialization_plan(request)
    assert newer.current_configuration["models"] == profiles().to_mapping()
    result = apply_initialization_plan(newer)
    assert result.configuration.models == profiles()


def test_project_reinit_preserves_models_when_sources_change(tmp_path):
    config = project(tmp_path)
    (tmp_path / "README.md").write_text("# Guide\n\nA public example.\n")
    plan = build_initialization_plan(InitRequest(mode="project", project_root=str(tmp_path), source_mode="recommended"))
    assert plan.proposed_configuration["models"] == config.models.to_mapping()
    result = apply_initialization_plan(plan)
    assert result.configuration.models == config.models
    assert ProjectConfig.load(config.config_path).models == config.models


def test_old_config_and_core_remain_model_free(tmp_path):
    config = ProjectConfig(tmp_path, tmp_path / ".tessera/config.yaml", StoreRecord(STORE_A, str(tmp_path / "memories")))
    write_project_config(config)
    assert "models" not in config.to_mapping()
    assert "models" not in ConfigurationResolver(cwd=tmp_path, environ={}).resolve().to_dict()
    raw = {"schema_version": 1, "store": {"id": STORE_A, "path": "memories"}}
    config.config_path.write_text(yaml.safe_dump(raw))
    selected = ConfigurationResolver(cwd=tmp_path, environ={}).resolve()
    assert selected.models == ModelProfiles()
    engine = TesseraEngine(configuration=selected)
    engine.write_memory_note("example/charter", "factual", "example", "Cobalt is the example project beacon.", [], [])
    engine.build_index()
    assert engine.retrieve_context("cobalt beacon", top_n=1)[0]["id"] == "example/charter"


def test_configured_remote_models_do_not_change_core_or_index(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_MODEL_KEY", SECRET)
    config = project(tmp_path)
    selection = ConfigurationResolver(cwd=tmp_path, environ={}).resolve()
    engine = TesseraEngine(configuration=selection)
    engine.write_memory_note("example/charter", "factual", "example", "Cobalt is the example project beacon.", [], [])
    engine.build_index()
    with_profiles = engine.retrieve_context("cobalt beacon", top_n=1)
    plain = TesseraEngine(configuration=replace(selection, models=ModelProfiles()))
    plain.build_index()
    assert plain.retrieve_context("cobalt beacon", top_n=1) == with_profiles
    for file in Path(selection.index_dir).rglob("*"):
        if file.is_file():
            assert SECRET.encode() not in file.read_bytes()
    assert SECRET not in repr(engine.configuration)


def test_no_provider_imports_network_or_credentials_on_core_startup(tmp_path):
    config = project(tmp_path)
    script = '''
import importlib.abc, sys, socket
class DenyOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {'torch', 'transformers', 'sentence_transformers', 'openai', 'anthropic', 'google'}:
            raise AssertionError('unexpected optional import')
sys.meta_path.insert(0, DenyOptional())
def no_network(*args, **kwargs): raise AssertionError('unexpected network')
socket.create_connection = no_network
socket.socket.connect = no_network
from tessera.config import ConfigurationResolver
from tessera import TesseraEngine
selection = ConfigurationResolver(cwd=sys.argv[1], environ={}).resolve()
engine = TesseraEngine(configuration=selection)
engine.build_index()
assert engine.retrieve_context('nothing') == []
'''
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_yaml_parse_error_does_not_echo_secret_material(tmp_path):
    config = project(tmp_path)
    config.config_path.write_text("schema_version: 2\nmodels: [" + SECRET)
    with pytest.raises(ConfigurationError) as error:
        ProjectConfig.load(config.config_path)
    assert SECRET not in str(error.value)


def test_profiles_and_engine_support_disposable_mcp_snapshots(tmp_path):
    import copy
    for model_profiles in (ModelProfiles(), profiles()):
        assert copy.deepcopy(model_profiles) is model_profiles
        config = project(tmp_path, model_profiles)
        engine = TesseraEngine(configuration=replace(
            ConfigurationResolver(cwd=tmp_path, environ={}).resolve(),
            models=model_profiles,
        ))
        snapshot = copy.deepcopy(engine)
        assert snapshot.configuration.models == model_profiles
        assert snapshot.graph is not engine.graph


def test_native_absolute_and_relative_model_paths(tmp_path):
    import os
    local = EmbeddingProfile("local", str(tmp_path / "encoder"), backend="application")
    assert local.local_path(tmp_path) == tmp_path / "encoder"
    relative = replace(local, model="." + os.sep + "encoder")
    assert relative.local_path(tmp_path) == tmp_path / "encoder"


def test_cli_config_inspects_profiles_without_loading_or_exposing_credentials(tmp_path, monkeypatch):
    import os
    project(tmp_path)
    monkeypatch.setenv("TEST_MODEL_KEY", SECRET)
    env = {key: value for key, value in os.environ.items() if key != "TESSERA_STORAGE_DIR"}
    result = subprocess.run([sys.executable, "-m", "tessera.cli", "config", "show", "--project", str(tmp_path), "--json"], cwd=tmp_path, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert SECRET not in result.stdout + result.stderr
    assert json.loads(result.stdout)["storage_selection"]["models"] == profiles().to_mapping()


def test_duplicate_secret_shaped_yaml_key_is_not_echoed(tmp_path):
    config = project(tmp_path)
    config.config_path.write_text("models:\n  " + SECRET + ": 1\n  " + SECRET + ": 2\n")
    with pytest.raises(ConfigurationError, match="duplicate") as error:
        ProjectConfig.load(config.config_path)
    assert SECRET not in str(error.value)
