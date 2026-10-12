"""Presentation-only adapter for the established #155 initialization plan."""
from typing import Dict
from .init_flow import InitializationPlan
from .presentation import say

def render_initialization_plan(plan: InitializationPlan, *, dry_run: bool) -> None:
    payload = plan.to_dict()
    sources = payload["sources"]
    say("\nInitialization plan:")
    say(f"  Scope: {plan.mode}")
    say(f"  Project: {plan.project_root or '-'}")
    say(f"  Configuration: {plan.config_path}")
    say(f"  Store id: {plan.store_id}")
    say(f"  Generated memories: {plan.generated_memory_store}")
    say(f"  Source mode: {plan.source_mode}")
    say(f"  Selected project sources: {sources['selected_count']} files")
    say(f"  Derived index: {plan.index_path}")
    say(f"  Ignored: {sources['ignored_count']} (discovery only; no files changed)")
    say(f"  Forbidden: {sources['forbidden_count']}")
    say("  Source files modified: 0")
    say(f"  Configuration changes: {', '.join(plan.config_changes) or 'none'}")
    say(f"  Ignore changes: {', '.join(plan.ignore_changes) or 'none'}")
    say("  Indexing: will start after confirmation")
    if plan.current_configuration is not None:
        say("  Existing configuration: loaded and compared")
        _render_configuration_summary("Current", plan.current_configuration)
        if plan.proposed_configuration is not None:
            _render_configuration_summary("Proposed", plan.proposed_configuration)
    if plan.warnings:
        say("  Warnings:")
        for warning in plan.warnings:
            say(f"    - {warning}")
        symlink_warnings = [
            warning for warning in plan.warnings
            if warning.startswith(("unsafe_symlink:", "outside_root:"))
        ]
        if symlink_warnings:
            say(
                "  Symlink policy: these entries were ignored during discovery; "
                "they are not selected, followed, written to configuration, or added to .tessera-ignore."
            )
    if plan.preflight_problems:
        say("  Preflight problems:")
        for problem in plan.preflight_problems:
            say(f"    - {problem}")
    if dry_run:
        say("\nDRY RUN — no changes made")


def _render_configuration_summary(label: str, mapping: Dict) -> None:
    store = mapping.get("store", mapping)
    sources = mapping.get("sources", {}).get("roots", [])
    index = mapping.get("index", {})
    say(f"  {label}:")
    say(f"    Generated memories: {store.get('path', '-')}")
    if sources:
        include_count = sum(len(root.get("include", [])) for root in sources)
        say(f"    Source allow-list entries: {include_count}")
    say(f"    Derived index: {index.get('path', '-')}")



def show_existing_configuration(current, path):
    say("This project already has TESSERA configured.")
    say(f"Configuration: {path}")
    say(f"Memory store: {current.store.path}")
    say(f"Derived index: {current.resolved_index().path}")
    say("Current sources are preserved when you choose Keep.")


def show_discovery(discovery):
    say("\nKnowledge sources found")
    for cluster in discovery.clusters:
        marker = "x" if cluster.recommended else (" " if cluster.selectable else "!")
        count = cluster.recommended_count + cluster.supported_count
        detail = f"{count} selectable"
        if cluster.forbidden_count:
            detail += f", {cluster.forbidden_count} forbidden"
        say(f"  [{marker}] {cluster.path:<28} {detail}")
    for item in discovery.files:
        if "/" in item.path:
            continue
        marker = "x" if item.selected_by_default else " " if item.selectable else "!" if item.classification == "FORBIDDEN" else "-"
        say(f"  [{marker}] {item.path:<28} {item.classification.lower()}")
