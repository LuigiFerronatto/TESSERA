import importlib.resources
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9/3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
MANIFEST = ROOT / "MANIFEST.in"
EXPECTED_SKILLS = {
    "sk_docker_environment.md",
    "sk_runtime_verification.md",
    "sk_schema_compliance.md",
    "sk_service_lifecycle.md",
    "sk_shell_execution.md",
}


def _project_config() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_distribution_declares_only_the_runtime_package() -> None:
    config = _project_config()
    setuptools = config["tool"]["setuptools"]

    assert setuptools["packages"] == ["tessera"]
    assert setuptools["include-package-data"] is False
    assert config["tool"]["setuptools"]["package-data"]["tessera"] == [
        "skills_library/*.md"
    ]


def test_sdist_manifest_excludes_repository_only_families() -> None:
    directives = set(MANIFEST.read_text(encoding="utf-8").splitlines())

    for family in ("benchmarks", "tests", "docs", "archive", "examples", ".github"):
        assert f"prune {family}" in directives


def test_metadata_and_entry_points_match_the_public_contract() -> None:
    config = _project_config()
    project = config["project"]

    assert project["name"] == "tessera"
    assert project["version"] == "3.4.0"
    assert project["license"] == "MIT"
    assert project["scripts"] == {
        "tessera": "tessera.cli:main",
        "tessera-mcp": "tessera.mcp_server:main",
    }
    assert project["optional-dependencies"]["mcp"] == ["mcp>=1.2.0,<2.0.0"]
    assert project["optional-dependencies"]["llm"] == ["requests>=2.28"]


def test_required_skills_are_package_resources() -> None:
    resources = importlib.resources.files("tessera").joinpath("skills_library")
    actual = {item.name for item in resources.iterdir() if item.name.endswith(".md")}

    assert actual == EXPECTED_SKILLS
