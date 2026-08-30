import re
import pytest

@pytest.fixture
def fake_llm():
    def _fake_llm(system_prompt: str, user_prompt: str) -> str:
        system_lower = system_prompt.lower()
        if "information-need" in system_lower or "need" in system_lower:
            match = re.search(r"Task instruction:\s*(.*?)(?:\n|$)", user_prompt, re.IGNORECASE)
            task = match.group(1).strip() if match else "the task"
            return f"Need to retrieve factual and procedural memory notes related to: {task}"
        
        elif "retrieval planner" in system_lower or "planner" in system_lower:
            match = re.search(r"Information need:\s*(.*?)(?:\n|$)", user_prompt, re.IGNORECASE)
            need = match.group(1).strip() if match else "query"
            clean_query = need.replace("Need to retrieve factual and procedural memory notes related to:", "").strip()
            return clean_query
            
        elif "user-state inference" in system_lower or "inference" in system_lower:
            match = re.search(r"Retrieved memory notes:\n(.*?\n\n|.*?$)", user_prompt, re.DOTALL | re.IGNORECASE)
            notes_block = match.group(1).strip() if match else ""
            
            summary_parts = [
                "### Primary Anchors of Truth (Simulated)\n"
            ]
            note_headers = re.findall(r"\[[a-zA-Z_]+\s*\|\s*([a-zA-Z0-9_\-/]+)\s*\|.*?\]", user_prompt)
            if note_headers:
                for idx, nid in enumerate(note_headers, 1):
                    summary_parts.append(f"{idx}. Provenance from note: {nid}")
                summary_parts.append("\n### Consolidated Context (Simulated)")
                summary_parts.append(notes_block)
            else:
                summary_parts.append("(No relevant memory found for this task.)")
            return "\n".join(summary_parts)
            
        else:
            return user_prompt
            
    return _fake_llm
