"""Prepare a label-blinded, no-overwrite human review packet for frozen #138 v1."""

import argparse
import json
from pathlib import Path

from benchmarks.episodes.run import FIXTURE, load_fixture, sha256


def prepare(output_dir: Path) -> None:
    fixture = load_fixture()
    blinded = {"fixture_sha256": sha256(FIXTURE), "fixture_version": fixture["fixture_version"],
               "dialogues": [{"dialogue_id": case["dialogue_id"], "turns": case["turns"]}
                             for case in fixture["dialogues"]]}
    template = json.loads(Path(__file__).with_name("annotation-template.json").read_text(encoding="utf-8"))
    if template["fixture_sha256"] != blinded["fixture_sha256"]:
        raise ValueError("annotation template does not match frozen fixture")
    # A second invocation cannot destroy a human's annotations.
    output_dir.mkdir(parents=True, exist_ok=False)
    for filename, value in (("dialogues-blinded.json", blinded),
                            ("reviewer-a.json", template), ("reviewer-b.json", template)):
        (output_dir / filename).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    prepare(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
