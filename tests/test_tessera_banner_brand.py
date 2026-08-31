from argparse import Namespace
from io import StringIO
from pathlib import Path

from rich.console import Console

from tessera.cli import cmd_banner
from tessera.display import (
    TESSERA_BANNER_LINES,
    TESSERA_TAGLINE,
    print_banner,
)


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TESSERA_BANNER = (
    "████████╗███████╗███████╗███████╗██████╗  █████╗ ",
    "╚══██╔══╝██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗",
    "   ██║   █████╗  ███████╗███████╗██████╔╝███████║",
    "   ██║   ██╔══╝  ╚════██║╚════██║██╔══██╗██╔══██║",
    "   ██║   ███████╗███████║███████║██║  ██║██║  ██║",
    "   ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝",
)


def test_banner_constant_is_the_canonical_tessera_wordmark() -> None:
    assert TESSERA_BANNER_LINES == EXPECTED_TESSERA_BANNER
    assert len(TESSERA_BANNER_LINES) == 6
    assert TESSERA_TAGLINE.startswith("Temporal Evolving State Synthesis")
    assert TESSERA_TAGLINE.endswith("Atomic Memories")


def test_rich_banner_renders_tessera_wordmark_and_tagline() -> None:
    output = StringIO()
    console = Console(
        file=output,
        force_terminal=False,
        color_system=None,
        width=120,
    )

    print_banner(console)

    rendered = output.getvalue()
    for line in EXPECTED_TESSERA_BANNER:
        assert line.rstrip() in rendered
    assert TESSERA_TAGLINE in rendered
    assert " █████╗ ███╗   ███╗███████╗███╗   ███╗" not in rendered


def test_plain_banner_identifies_tessera(capsys) -> None:
    cmd_banner(Namespace(plain=True))

    rendered = capsys.readouterr().out
    assert rendered == f"Tessera — {TESSERA_TAGLINE}\n"


def test_active_runtime_has_no_legacy_amem_identity() -> None:
    forbidden = ("AMem", "AMEM", "A-Mem", "A_MEM")
    for path in (ROOT / "tessera").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path}: active runtime contains {token!r}"


def test_research_citation_remains_intact() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "A-MEM: Agentic Memory for LLM Agents" in readme
