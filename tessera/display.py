"""
Rich-powered terminal UI helpers for the `tessera` CLI.

Goals:
  - Make it visually obvious what's a **file/location** (dim, monospace,
    prefixed with a folder icon) vs what's **retrieved context/content**
    (colored panel, prefixed by memory type) — this was explicitly requested
    after `tessera start --use-llm` output mixed both without visual distinction.
  - Color-code by node type consistently across every command (list/query/
    start): factual=blue, preference=magenta, procedural_anchor=green,
    tag=dim grey.
  - Degrade gracefully: every renderer here also has a plain-text fallback
    (used automatically when stdout isn't a TTY, or when `--plain`/`NO_COLOR`
    is set) so piping into `grep`/`head`/a file never breaks.

This module has ZERO side effects at import time (no I/O), so it's cheap
to import even from `tessera list --paths-only` scripting paths that skip it.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Iterable, List, Optional

TYPE_STYLE = {
    "factual": "bold blue",
    "preference": "bold magenta",
    "procedural_anchor": "bold green",
    "tag": "dim white",
}

TYPE_LABEL = {
    "factual": "FACTUAL",
    "preference": "PREFERENCE",
    "procedural_anchor": "PROCEDURAL_ANCHOR",
    "tag": "TAG",
}


def _use_color(force_plain: bool = False) -> bool:
    """
    Decides whether to render with Rich color/formatting at all.
    Off when: --plain passed, NO_COLOR env var set (https://no-color.org/),
    stdout isn't a TTY (piped into a file/grep/head), or `rich` isn't
    installed for some reason (defensive — it's a hard dependency, but a
    broken environment shouldn't crash a "list my memories" command).
    """
    if force_plain:
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TESSERA_NO_COLOR") is not None:
        return False
    # Explicit opt-in to force color even when stdout isn't a TTY (e.g.
    # piping into `less -R`, or capturing output for a screen recording).
    force_color = os.environ.get("FORCE_COLOR") is not None or os.environ.get("TESSERA_FORCE_COLOR") is not None
    if not sys.stdout.isatty() and not force_color:
        return False
    try:
        import rich  # noqa: F401
    except ImportError:
        return False
    return True


def get_console(force_plain: bool = False):
    """Returns a rich.Console honoring the same _use_color() decision, or
    None if plain-text should be used instead (caller falls back to print())."""
    if not _use_color(force_plain):
        return None
    from rich.console import Console

    # Rich's own Console() does its own independent isatty() check and will
    # silently drop color if stdout isn't a TTY — even if we already decided
    # color should be forced (FORCE_COLOR/TESSERA_FORCE_COLOR, e.g. piping into
    # `less -R` or capturing a screen recording). Pass force_terminal=True
    # in that case so Rich doesn't second-guess us.
    force_color = os.environ.get("FORCE_COLOR") is not None or os.environ.get("TESSERA_FORCE_COLOR") is not None
    if force_color and not sys.stdout.isatty():
        return Console(force_terminal=True)
    return Console()


def print_banner(console=None) -> None:
    """
    Prints the Tessera ASCII banner (generated once via `npx oh-my-logo "Tessera"
    sunset --filled` and hardcoded here — no network/npx dependency at
    runtime). Silently skipped when color is disabled.
    """
    if console is None:
        return
    from rich.text import Text

    banner_lines = [
        " █████╗ ███╗   ███╗███████╗███╗   ███╗",
        "██╔══██╗████╗ ████║██╔════╝████╗ ████║",
        "███████║██╔████╔██║█████╗  ██╔████╔██║",
        "██╔══██║██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║",
        "██║  ██║██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║",
        "╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝",
    ]
    gradient = ["#ff9966", "#ff8b61", "#ff805d", "#ff7458", "#ff6a5f", "#ffa34e"]
    text = Text()
    for line, color in zip(banner_lines, gradient):
        text.append(line + "\n", style=color)
    text.append("Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories\n", style="dim italic")
    console.print(text)


def _type_style(node_type: Optional[str]) -> str:
    return TYPE_STYLE.get(node_type or "", "white")


def _type_label(node_type: Optional[str]) -> str:
    return TYPE_LABEL.get(node_type or "", (node_type or "?").upper())


# ---------------------------------------------------------------------------
# `tessera list`
# ---------------------------------------------------------------------------

def render_list_table(rows: List[tuple], console) -> None:
    """
    rows: list of (node_id, node_type, filename, filepath).
    Renders a colored Rich table: id, type (colored by TYPE_STYLE), and the
    filepath in dim/monospace — visually distinct from the id/type columns
    so it always reads as "location", not "content".
    """
    from rich.table import Table

    table = Table(show_lines=False, header_style="bold", box=None, pad_edge=False)
    table.add_column("ID", style="white", no_wrap=False)
    table.add_column("TIPO", no_wrap=True)
    table.add_column("ARQUIVO", style="dim", no_wrap=False)

    for node_id, node_type, _filename, filepath in rows:
        table.add_row(
            node_id,
            f"[{_type_style(node_type)}]{_type_label(node_type)}[/{_type_style(node_type)}]",
            f"📄 {filepath}",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# `tessera query`
# ---------------------------------------------------------------------------

def render_query_results(results: List[Dict[str, Any]], console, *, show_related: bool, show_body: bool, show_debug: bool = False) -> None:
    """
    One Rich Panel per hit. Panel title = colored [type | id | score] header
    (this is the "context/content" identity). The filepath is rendered
    *inside* the panel but on its own dim line prefixed with 📄, immediately
    visually distinguishable from the body text below it.
    """
    from rich.panel import Panel
    from rich.text import Text

    for i, r in enumerate(results, 1):
        node_type = r.get("type")
        style = _type_style(node_type)
        header = Text()
        header.append(f"[{i}] ", style="bold")
        header.append(r["id"], style=f"bold {style}" if "bold" not in style else style)
        header.append("  ")
        header.append(_type_label(node_type), style=style)
        header.append(f"  score={r['score']:.4f}", style="dim")

        body = Text()
        
        # Relevant Evidence Section (Phase 2)
        if r.get("relevant_evidence"):
            body.append("Relevant evidence\n", style="bold underline")
            body.append(f"\"{r['relevant_evidence']}\"\n\n", style="italic")

        filepath = r.get("filepath") or r.get("filename") or ""
        if filepath:
            body.append(f"📄 Source: {filepath}\n", style="dim")
            
        if r.get("related_ids"):
            body.append(f"🔗 Related: {', '.join(r['related_ids'])}\n", style="dim cyan")
            
        # Debug Explanations (Phase 1)
        if show_debug and r.get("score_explain"):
            exp = r["score_explain"]
            body.append("\nScore Explanation\n", style="bold yellow")
            body.append(f" ├─ final score:    {r['score']:.3f}\n", style="yellow")
            body.append(f" ├─ lexical tfidf:  {exp.get('lexical_tfidf', 0.0):.2f}\n", style="dim yellow")
            body.append(f" ├─ lexical overlap:{exp.get('lexical_overlap', 0.0):.2f}\n", style="dim yellow")
            body.append(f" ├─ composite lex:  {exp.get('lexical_score', 0.0):.2f}\n", style="dim yellow")
            body.append(f" ├─ title:          {exp.get('title', 0.0):.2f}\n", style="dim yellow")
            body.append(f" ├─ metadata:       {exp.get('metadata', 0.0):.2f}\n", style="dim yellow")
            body.append(f" ├─ raw pagerank:   {exp.get('raw_pagerank', 0.0):.4f}\n", style="dim yellow")
            body.append(f" ├─ normalized rel: {exp.get('normalized_relations', 0.0):.2f}\n", style="dim yellow")
            body.append(f" ├─ relations contr:{exp.get('relations_contribution', 0.0):.2f}\n", style="dim yellow")
            body.append(f" ├─ type_boost:     {exp.get('type_boost', 1.0):.1f}x\n", style="dim yellow")
            body.append(f" └─ recency_boost:  {exp.get('recency_boost', 1.0):.1f}x\n", style="dim yellow")

        if show_body:
            if filepath or r.get("related_ids") or r.get("relevant_evidence") or (show_debug and r.get("score_explain")):
                body.append("\n")
            body.append("Full memory\n", style="bold")
            body.append("───────────\n", style="dim")
            body.append(r.get("body", ""))

        console.print(Panel(body, title=header, border_style=style, title_align="left"))


# ---------------------------------------------------------------------------
# `tessera start` (orchestrator pipeline result)
# ---------------------------------------------------------------------------

def render_start_result(result, console) -> None:
    """
    Renders an OrchestratorResult with clear visual separation between:
      - pipeline metadata (need / query / stores queried) — dim panel
      - each raw memory actually retrieved — one colored panel per note,
        file path on its own dim line (same convention as render_query_results)
      - the final consolidated context — a distinct, highlighted panel,
        since this is the synthesized answer, not raw memory content
    """
    from rich.panel import Panel
    from rich.text import Text

    meta = Text()
    meta.append("🧠 Necessidade de informação: ", style="bold")
    meta.append(f"{result.information_need}\n")
    meta.append("🔎 Consulta de busca planejada: ", style="bold")
    meta.append(f"{result.retrieval_query}\n")
    meta.append("🗂️  Gavetas consultadas: ", style="bold")
    meta.append(f"{', '.join(result.stores_queried)}\n")
    meta.append("📚 Memórias brutas recuperadas: ", style="bold")
    meta.append(str(len(result.raw_memories)))
    console.print(Panel(meta, border_style="dim", title="Pipeline", title_align="left"))

    if result.raw_memories:
        console.print()
        console.rule("[bold]Memórias usadas como evidência[/bold]", style="dim")
        render_query_results(
            result.raw_memories, console, show_related=True, show_body=False
        )

    console.print()
    console.rule("[bold yellow]Contexto Consolidado[/bold yellow]")
    console.print(Panel(result.consolidated_context, border_style="yellow"))


# ---------------------------------------------------------------------------
# Plain-text fallbacks (used automatically when color is off)
# ---------------------------------------------------------------------------

def print_list_plain(rows: List[tuple]) -> None:
    id_width = max((len(node_id) for node_id, _, _, _ in rows), default=0)
    type_width = max((len(node_type) for _, node_type, _, _ in rows), default=0)
    for node_id, node_type, filename, _ in rows:
        print(f"{node_id.ljust(id_width)}  {node_type.ljust(type_width)}  {filename}")


# ---------------------------------------------------------------------------
# `tessera init` / `tessera write` / `tessera index` / `tessera skills` — small commands,
# but still following the "arquivo é sempre dim/📄, resultado é sempre
# destacado" convention so every Tessera output reads consistently.
# ---------------------------------------------------------------------------

def render_init_result(console, storage_dir: str, node_count: int) -> None:
    from rich.panel import Panel
    from rich.text import Text

    body = Text()
    body.append("📄 ", style="dim")
    body.append(f"{storage_dir}\n", style="dim italic")
    body.append(f"{node_count} nó(s) já encontrado(s)/indexado(s)", style="bold green")
    console.print(Panel(body, title="✔ Diretório inicializado", border_style="green", title_align="left"))


def render_write_result(console, filepath: str, node_id: str, node_type: str, connections: List[str]) -> None:
    from rich.panel import Panel
    from rich.text import Text

    body = Text()
    body.append(f"{node_id}  ", style=f"bold {_type_style(node_type)}")
    body.append(_type_label(node_type), style=_type_style(node_type))
    body.append("\n📄 ", style="dim")
    body.append(f"{filepath}\n", style="dim italic")
    if connections:
        body.append("🔗 conexões explícitas: ", style="cyan")
        body.append(", ".join(connections), style="dim cyan")
    console.print(Panel(body, title="✔ Nota gravada", border_style=_type_style(node_type), title_align="left"))


def render_index_result(console, storage_dir: str, node_count: int, edge_count: int,
                         cache_pkl: str, cache_json: str) -> None:
    from rich.panel import Panel
    from rich.text import Text

    body = Text()
    body.append("📄 ", style="dim")
    body.append(f"{storage_dir}\n\n", style="dim italic")
    body.append(f"{node_count}", style="bold cyan")
    body.append(" nós, ")
    body.append(f"{edge_count}", style="bold cyan")
    body.append(" arestas\n")
    body.append("📄 cache: ", style="dim")
    body.append(f"{cache_pkl}\n", style="dim italic")
    body.append("📄 cache (legível): ", style="dim")
    body.append(f"{cache_json}", style="dim italic")
    console.print(Panel(body, title="✔ Índice reconstruído", border_style="cyan", title_align="left"))


def render_skills_install_result(console, paths: List[str], storage_dir: str) -> None:
    from rich.panel import Panel
    from rich.text import Text

    body = Text()
    body.append(f"{len(paths)} âncora(s) procedimental(is) instalada(s) em ", style="bold green")
    body.append(f"{storage_dir}\n\n", style="dim italic")
    for p in paths:
        body.append("📄 ", style="dim")
        body.append(f"{p}\n", style="dim italic")
    console.print(Panel(body, title="✔ Skills instaladas", border_style="green", title_align="left"))


def render_skills_list_result(console, skill_ids: List[str]) -> None:
    from rich.table import Table

    table = Table(show_lines=False, header_style="bold", box=None, pad_edge=False)
    table.add_column("SKILL (âncora procedimental)", style=_type_style("procedural_anchor"))
    for skill_id in skill_ids:
        table.add_row(skill_id)
    console.print(table)


# ---------------------------------------------------------------------------
# `tessera doctor` / `tessera quickstart`
# ---------------------------------------------------------------------------

def render_doctor_report(console, report) -> None:
    """report: tessera.diagnostics.DoctorReport"""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    table = Table(show_lines=False, header_style="bold", box=None, pad_edge=False)
    table.add_column("", width=2)
    table.add_column("CHECAGEM")
    table.add_column("DETALHE")
    for check in report.checks:
        if check.ok:
            icon = "[bold green]✔[/bold green]"
        elif not check.required:
            icon = "[yellow]○[/yellow]"  # optional, failed but harmless
        else:
            icon = "[bold red]✘[/bold red]"
        name_style = "" if check.ok else ("dim" if not check.required else "bold red")
        detail = check.detail
        if not check.ok and check.hint:
            detail += f"\n[dim yellow]💡 {check.hint}[/dim yellow]"
        table.add_row(icon, f"[{name_style}]{check.name}[/{name_style}]" if name_style else check.name, detail)

    summary_style = "bold green" if report.all_ok else "bold red"
    summary_text = "✔ tudo OK" if report.all_ok else "✘ alguma checagem falhou — veja as dicas acima"
    border = "green" if report.all_ok else "red"

    console.print(Panel(
        Text(f"📄 {report.storage_dir}", style="dim italic"),
        title="🩺 tessera doctor", border_style=border, title_align="left",
    ))
    console.print(table)
    console.print(f"\n[{summary_style}]{summary_text}[/{summary_style}]")


def print_doctor_report_plain(report) -> None:
    print(f"tessera doctor — storage_dir: {report.storage_dir}")
    for check in report.checks:
        if check.ok:
            mark = "OK  "
        elif not check.required:
            mark = "OPT "
        else:
            mark = "FAIL"
        print(f"  [{mark}] {check.name}: {check.detail}")
        if not check.ok and check.hint:
            print(f"         hint: {check.hint}")
    print("\nRESULTADO:", "tudo OK" if report.all_ok else "alguma checagem obrigatória falhou")


def render_quickstart_plan(console, plan, applied: bool) -> None:
    """plan: tessera.diagnostics.QuickstartPlan"""
    import json as _json

    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.text import Text

    body = Text()
    body.append("📄 projeto: ", style="dim")
    body.append(f"{plan.project_root}\n", style="dim italic")
    body.append("🔍 tipo detectado: ", style="dim")
    body.append(f"{plan.detected_project_type}\n", style="cyan")
    body.append("📄 storage_dir proposto: ", style="dim")
    body.append(f"{plan.storage_dir}\n", style="bold green")
    console.print(Panel(body, title="🚀 tessera quickstart", border_style="green", title_align="left"))

    console.print("\n[bold]Cole isso no seu config MCP[/bold] "
                  "([dim].mcp.json[/dim] / [dim].gemini/settings.json[/dim] / Claude Desktop):\n")
    console.print(Syntax(_json.dumps(plan.mcp_config_block, indent=2, ensure_ascii=False), "json", theme="ansi_dark"))

    if applied:
        console.print("\n[bold green]Ações executadas:[/bold green]")
        for action in plan.actions_taken:
            console.print(f"  [green]✔[/green] {action}")
    else:
        console.print(
            "\n[dim yellow]💡 Isso foi só um plano — nada foi criado no disco ainda. "
            "Rode de novo com --apply para criar storage_dir e indexar.[/dim yellow]"
        )


def print_quickstart_plan_plain(plan, applied: bool) -> None:
    import json as _json

    print(f"tessera quickstart — projeto: {plan.project_root}")
    print(f"tipo detectado: {plan.detected_project_type}")
    print(f"storage_dir proposto: {plan.storage_dir}\n")
    print("Cole isso no seu config MCP (.mcp.json / .gemini/settings.json / Claude Desktop):")
    print(_json.dumps(plan.mcp_config_block, indent=2, ensure_ascii=False))
    if applied:
        print("\nAções executadas:")
        for action in plan.actions_taken:
            print(f"  - {action}")
    else:
        print("\n(plano apenas — nada foi criado no disco; rode com --apply para aplicar)")


# ---------------------------------------------------------------------------
# `tessera stats` — index composition breakdown (notes vs. internal tag/entity
# nodes), added to answer "why does `tessera list` show 200 but the index has
# 272 nodes?" without needing to inspect graph.json by hand.
# ---------------------------------------------------------------------------

def render_stats_result(console, storage_dir: str, type_counts: Dict[str, int],
                         edge_count: int) -> None:
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    note_types = {"factual", "preference", "procedural_anchor"}
    note_count = sum(n for t, n in type_counts.items() if t in note_types)
    internal_count = sum(n for t, n in type_counts.items() if t not in note_types)
    total = note_count + internal_count

    header = Text()
    header.append("📄 ", style="dim")
    header.append(f"{storage_dir}\n\n", style="dim italic")
    header.append(f"{note_count}", style="bold green")
    header.append(" notas de memória reais  ", style="green")
    header.append(f"+ {internal_count}", style="bold dim")
    header.append(" nós internos (tag/entity, usados pelo DW-PR)  ", style="dim")
    header.append(f"= {total}", style="bold cyan")
    header.append(" nós no grafo, ")
    header.append(f"{edge_count}", style="bold cyan")
    header.append(" arestas")
    console.print(Panel(header, title="📊 Estatísticas do índice", border_style="cyan", title_align="left"))

    table = Table(show_lines=False, header_style="bold", box=None, pad_edge=False)
    table.add_column("TIPO DE NÓ")
    table.add_column("QTD", justify="right")
    table.add_column("O QUE É")
    explain = {
        "factual": "nota real (.md) — fato/decisão",
        "preference": "nota real (.md) — preferência/feedback",
        "procedural_anchor": "nota real (.md) — procedimento/anti-padrão",
        "tag": "nó sintético — agrupa notas com a mesma tag (não é um arquivo)",
        "entity": "nó sintético — agrupa notas que citam a mesma entidade (não é um arquivo)",
    }
    for node_type, count in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        style = _type_style(node_type) if node_type in TYPE_STYLE else "dim white"
        table.add_row(
            f"[{style}]{_type_label(node_type)}[/{style}]",
            str(count),
            explain.get(node_type, "nó auxiliar do grafo"),
        )
    console.print(table)


def print_stats_plain(storage_dir: str, type_counts: Dict[str, int], edge_count: int) -> None:
    note_types = {"factual", "preference", "procedural_anchor"}
    note_count = sum(n for t, n in type_counts.items() if t in note_types)
    internal_count = sum(n for t, n in type_counts.items() if t not in note_types)
    total = note_count + internal_count
    print(f"storage_dir: {storage_dir}")
    print(f"{note_count} notas reais + {internal_count} nós internos = {total} nós no grafo, {edge_count} arestas")
    for node_type, count in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {node_type}\t{count}")
