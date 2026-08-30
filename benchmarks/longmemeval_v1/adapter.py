"""Deterministic session-level projection into native TESSERA documents."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from . import DATASET_SHA256, SOURCE_COMMIT, SOURCE_REPOSITORY


@dataclass(frozen=True)
class SessionDocument:
    memory_id: str
    session_id: str
    frontmatter: Dict[str, Any]
    body: str

    @property
    def text(self) -> str:
        header = yaml.safe_dump(
            self.frontmatter, allow_unicode=True, sort_keys=True, default_flow_style=False
        ).strip()
        return f"---\n{header}\n---\n{self.body}"


def stable_memory_id(question_id: str, session_id: str) -> str:
    return f"longmemeval-v1/{question_id}/{session_id}"


def _body(session_date: str, turns: List[Dict[str, str]]) -> str:
    lines = ["# LongMemEval V1 session", "", f"Session timestamp: {session_date}", ""]
    for index, turn in enumerate(turns, 1):
        lines.extend((f"## Turn {index}", f"{turn['role']}: {turn['content']}", ""))
    return "\n".join(lines).rstrip() + "\n"


def session_document(
    instance: Dict[str, Any],
    session_id: str,
    session_date: str,
    turns: List[Dict[str, str]],
    dataset_sha256: str = DATASET_SHA256,
) -> SessionDocument:
    question_id = instance["question_id"]
    answer_ids = {str(value) for value in instance["answer_session_ids"]}
    session_id = str(session_id)
    memory_id = stable_memory_id(question_id, session_id)
    frontmatter = {
        "active_connections": [],
        "benchmark": "longmemeval-v1",
        "dataset_sha256": dataset_sha256,
        "entities": [],
        "episode_id": question_id,
        "has_answer": session_id in answer_ids,
        "id": memory_id,
        "node_type": "factual",
        "question_id": question_id,
        "question_type": instance["question_type"],
        "session_date": str(session_date),
        "session_id": session_id,
        "source_commit": SOURCE_COMMIT,
        "source_repository": SOURCE_REPOSITORY,
        "tags": [],
    }
    return SessionDocument(memory_id, session_id, frontmatter, _body(str(session_date), turns))


def project_instance(
    instance: Dict[str, Any], dataset_sha256: str = DATASET_SHA256
) -> List[SessionDocument]:
    documents: List[SessionDocument] = []
    seen = set()
    for session_id, session_date, turns in zip(
        instance["haystack_session_ids"],
        instance["haystack_dates"],
        instance["haystack_sessions"],
    ):
        stable_id = str(session_id)
        if stable_id in seen:
            continue
        seen.add(stable_id)
        documents.append(
            session_document(instance, stable_id, session_date, turns, dataset_sha256)
        )
    return documents


def write_instance_corpus(
    instance: Dict[str, Any], corpus_dir: Path, dataset_sha256: str = DATASET_SHA256
) -> List[SessionDocument]:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    if any(corpus_dir.iterdir()):
        raise ValueError(f"corpus directory must be empty: {corpus_dir}")
    documents = project_instance(instance, dataset_sha256)
    for document in documents:
        filename = hashlib.sha256(document.memory_id.encode("utf-8")).hexdigest() + ".md"
        (corpus_dir / filename).write_text(document.text, encoding="utf-8")
    return documents
