"""Verify the website's Python example using the real TESSERA public API.

Run from the repository root: .venv/bin/python website/scripts/capture-example.py
All engine writes are confined to a temporary fixture directory.
"""

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tessera import Connection, TesseraEngine  # noqa: E402


def main():
    with tempfile.TemporaryDirectory(prefix="tessera-site-fixture-") as fixture:
        previous = Path.cwd()
        try:
            os.chdir(fixture)
            engine = TesseraEngine(storage_dir="./memories")
            engine.write_memory_note(
                mem_id="atlas/launch-plan", mem_type="factual", episode_id="planning",
                content="September 1, 2026. The Atlas launch is scheduled for September 12.",
                tags=["atlas", "launch"], entities=[],
            )
            engine.write_memory_note(
                mem_id="atlas/launch-update", mem_type="factual", episode_id="update",
                content="September 8, 2026. The Atlas launch is moved to September 26 to finish accessibility testing.",
                tags=["atlas", "launch"], entities=[],
                active_connections=[Connection(target_memory_id="atlas/launch-plan", relation_type="related_to")],
            )
            before = {str(p): p.read_bytes() for p in Path("memories").rglob("*.md")}
            # Execute the exact code presented in the page, not a similar approximation.
            import re
            from html import unescape
            page = (REPO / "website/index.html").read_text()
            code = unescape(re.search(r'<code id="query-code">(.*?)</code>', page, re.S).group(1))
            namespace = {}
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(code, "website-python-example", "exec"), namespace)
            results = namespace["results"]
            assert {r["id"] for r in results} == {"atlas/launch-plan", "atlas/launch-update"}
            for result in results:
                assert result["relevant_evidence"] and result["provenance"] and result["evidence"]
                assert result["score_explain"] and result["body"]
                assert result["related_ids"]
                source = Path(result["filepath"])
                lines = source.read_text().splitlines()
                span = result["evidence"]["span"]
                start, end = span["start_line"], span["end_line"]
                assert start is not None and end is not None
                assert result["relevant_evidence"] in "\n".join(lines[start - 1:end])
                assert result["provenance"]["source"]["document_hash"]
                # Stable, portable capture; omit temporary absolute paths.
                result["filepath"] = str(source.relative_to(Path.cwd())) if source.is_absolute() else str(source)
            assert before == {str(p): p.read_bytes() for p in Path("memories").rglob("*.md")}
            target = REPO / "website/verification/retrieval.json"
            target.write_text(json.dumps(results, indent=2, default=str) + "\n")
            print("PASS: exact website query; two retained notes; source spans, provenance, relation IDs; sources unchanged.")
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    main()
