# Contributing to TESSERA

Start with an [issue](https://github.com/LuigiFerronatto/TESSERA/issues/new/choose).
For a bug, include the version, a minimal reproduction, expected behavior and
actual output. Remove credentials and private source content from examples.

For a behavior change, use the [Test Card template](.github/ISSUE_TEMPLATE/test-card.md)
to define one hypothesis, its baseline and its success criteria. Check the
[roadmap](docs/ROADMAP.md) for existing ownership, dependencies and selected work;
an open or READY card is not automatically selected for implementation.

## Develop and test

Use Python 3.9 or newer in a virtual environment. Keep the environment outside
the checkout so repository inventory checks do not scan installed dependencies:

```bash
python -m venv ../tessera-dev-env
source ../tessera-dev-env/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -ra
```

On Windows, activate `..\tessera-dev-env\Scripts\Activate.ps1` in PowerShell.
Changes to MCP also need the optional dependencies on Python 3.10 or newer:
`python -m pip install -e ".[dev,mcp]"`. CI runs the base suite and built-artifact
checks on Python 3.9 and 3.12, and the installed MCP protocol checks on 3.12.

Start with tests that reproduce the affected behavior. Keep fixtures small,
deterministic and project-agnostic. Basic retrieval does not require provider
credentials. Follow the [architecture](docs/ARCHITECTURE.md) and
[output contract](docs/OUTPUT_CONTRACT.md) when changing public behavior.

## Submit a pull request

Use the [PR template](.github/pull_request_template.md). Link the owning issue,
describe the user-visible change and provide reproducible evidence, limitations
and the proposed decision. Keep unrelated changes in separate issues.

Declare `Benchmark applicability: REQUIRED`, `SMOKE_ONLY` or `NOT_APPLICABLE`
with a rationale under the [Benchmark Ledger contract](docs/BENCHMARK_CI.md).
Run the relevant evaluation; a green unit suite alone does not establish a
retrieval-quality improvement. Record a changelog entry or a reason it is not
needed under the [change policy](docs/CHANGE_POLICY.md), and update affected docs
and the [plain-language stage record](docs/test-cards/README.md).

The [CI workflow](.github/workflows/tessera-ci.yml), independent Maintainer Audit
and Merge Governor check the exact candidate. Human review remains required.
After merge, record the canonical commit and complete the
[lifecycle reconciliation](docs/AGENTIC_GOVERNANCE.md) before starting dependent
work from fresh `main`.

## License and third-party material

The project license is [MIT](LICENSE). Submit only material you have permission
to contribute, and preserve copyright and license notices for third-party code
and assets. Keep those notices with their files.
