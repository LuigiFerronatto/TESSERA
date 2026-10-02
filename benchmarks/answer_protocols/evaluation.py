"""Evaluator-only deterministic J0; labels are joined after persisted capture."""

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from .common import digest, exact, string
from .reader import load_capture

METRIC_VERSION = "reader-j0-draft/1"


def normalized_tokens(text: str):
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def score_persisted(destination: Path, reference: Dict[str, Any]) -> Dict[str, Any]:
    # Receipt/hash verification intentionally happens before references are read.
    capture = load_capture(destination)
    exact(reference, {"question_id", "answer", "should_abstain"}, "evaluator reference")
    string(reference["question_id"], "question_id")
    string(reference["answer"], "reference answer", empty=True)
    if type(reference["should_abstain"]) is not bool:
        raise ValueError("should_abstain must be boolean")
    if digest(reference["question_id"]) != capture["request"]["question_ref"]:
        raise ValueError("reference belongs to a different persisted output")
    if reference["should_abstain"] != (not reference["answer"].strip()):
        raise ValueError("reference abstention/answer inconsistency")
    last = capture["attempts"][-1]
    result = {"schema_version": METRIC_VERSION, "question_ref": capture["request"]["question_ref"],
              "reader_capture_sha256": capture["capture_sha256"],
              "execution_mode": capture["execution_mode"], "reference_sha256": digest(reference),
              "status": last["status"], "exact_match": None, "normalized_f1": None,
              "abstention_correct": None, "judge_metrics": None}
    if last["status"] != "ok":
        return result  # Infrastructure/parse failures are not incorrect answers.
    output = last["output"]
    predicted, expected = normalized_tokens(output["answer"]), normalized_tokens(reference["answer"])
    overlap = sum((Counter(predicted) & Counter(expected)).values())
    f1 = 2 * overlap / (len(predicted) + len(expected)) if predicted or expected else 1.0
    result.update(exact_match=int(predicted == expected), normalized_f1=f1,
                  abstention_correct=output["abstained"] == reference["should_abstain"])
    return result
