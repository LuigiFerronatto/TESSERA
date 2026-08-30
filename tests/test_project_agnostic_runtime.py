from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _legacy_project_token() -> str:
    # Constructed so the legacy external-project name is not itself reintroduced
    # into the public source surface by this regression guard.
    return "".join(("L", "A", "O"))


def test_package_metadata_is_tessera_native():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert _legacy_project_token().lower() not in text.lower()
    assert "github.com/LuigiFerronatto/TESSERA" in text
    assert "TESSERA Contributors" in text


def test_mcp_runtime_uses_tessera_storage_identifier():
    text = (ROOT / "tessera" / "mcp_server.py").read_text(encoding="utf-8")
    assert _legacy_project_token().lower() not in text.lower()
    assert 'os.environ.get("TESSERA_STORAGE_DIR", "./memories")' in text
