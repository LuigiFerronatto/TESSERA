"""Small invented fixture, never benchmark/model data or a QA evaluation."""

from .frozen import capture_evidence, digest


def synthetic_capture():
    def hit(memory_id, body, selected, related=None):
        fingerprint = digest([memory_id, body])
        provenance = {
            "schema_version": 1, "evidence_id": "ev_" + fingerprint[:16],
            "memory_id": memory_id, "fingerprint": fingerprint,
            "source": {"document_id": "doc_" + digest(memory_id)[:16],
                       "path": memory_id + ".md", "document_hash": digest(body),
                       "content_hash": digest(body), "format": "markdown"},
            "span": {"start_line": 1, "end_line": len(body.splitlines())},
            "extraction": {"method": "synthetic_document", "inferred": False},
        }
        evidence = None
        if selected is not None:
            evidence = {
                **provenance, "evidence_id": "ev_" + digest(selected)[:16],
                "fingerprint": digest(selected),
                "span": {"start_line": len(body.splitlines()), "end_line": len(body.splitlines())},
                "extraction": {"method": "synthetic_selected_span", "inferred": False},
            }
        return {"id": memory_id, "score": 0.75, "body": body,
                "relevant_evidence": selected, "related_ids": related or [],
                "provenance": provenance, "evidence": evidence}

    selected = "The workshop keeps the blue toolkit beside the north door."
    body = " ".join(["Routine inventory context."] * 160) + "\n" + selected
    second = "The spare toolkit is kept on the upper shelf."
    queries = [
        {"query_id": "synthetic-late-span", "query": "Where is the blue toolkit?", "hits": [
            hit("workshop/tools", body, selected, ["workshop/spares"]),
            hit("workshop/spares", second, second),
        ]},
        {"query_id": "synthetic-no-selected-span", "query": "What is the equipment rental price?",
         "hits": [hit("workshop/hours", "The workshop opens in the morning.", None)]},
        {"query_id": "synthetic-empty", "query": "Which satellite is closest?", "hits": []},
    ]
    return capture_evidence(
        queries, tessera_commit="0" * 40, retrieval_contract_commit="0" * 40,
        retrieval_configuration={"fixture": "invented-presentation-controls-v1", "retrieval": None},
    )
