from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "release.yml"


def test_release_workflow_is_tagged_and_separates_build_from_publish() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'tags: ["v[0-9]+.[0-9]+.[0-9]+"]' in text
    assert "name: Build and attest release artifacts" in text
    assert "name: Publish to PyPI through Trusted Publishing" in text
    assert "needs: build" in text
    assert "if: github.event_name == 'push'" in text
    assert "pypa/gh-action-pypi-publish@release/v1" in text
    assert "environment:" in text
    assert "name: pypi" in text


def test_release_workflow_scopes_oidc_to_publish_job() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    build, publish = text.split("  publish:", 1)
    assert "id-token: write" not in build
    assert "id-token: write" in publish
    assert "pull_request" not in text
    assert "RELEASE_TAG" in build
    assert "tessera-agent-memory" in build
    assert "0.0.1" in build
