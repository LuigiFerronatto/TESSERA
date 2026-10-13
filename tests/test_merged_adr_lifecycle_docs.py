"""Merged decisions must not be confused with their pending runtime delivery."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('issue,pr,merge,head,decision', [
    (349, 366, 'b486e6f2c47b367fc686ae84e00b6afdd5a4f9e7', 'cf16d539afca0e903ef611a564d7de53bea3aa58', '6118666384'),
    (350, 368, '16152d78b20c1ee37a4b808f5c4d6b55b2bd4e68', 'b8ce5f72244c731700ca224da998704c65a4a876', '6118666771'),
    (361, 369, '6228ecb4f88deff1e1c445b10c29250108a8ccb6', '5e004f1e26a305ad09d5c3eda86a275fde7eefef', '6118667212'),
])
def test_merged_adr_provenance_matches_stage_index_and_roadmap(issue, pr, merge, head, decision):
    card = next((ROOT / 'docs/process/test-cards').glob(f'{issue}-*.md')).read_text()
    audit = (ROOT / f'docs/history/pr-evolution/{issue}.md').read_text()
    roadmap = (ROOT / 'docs/process/roadmap.md').read_text()
    index = (ROOT / 'docs/process/test-cards/README.md').read_text()
    for text in (card, audit):
        assert merge in text
        assert head in text
        assert f'issuecomment-{decision}' in text
        assert '`IMPLEMENTED`' in text
        assert 'NOT_APPLICABLE' in text
    assert merge in roadmap
    row = next(line for line in index.splitlines() if line.startswith(f'| #{issue} '))
    assert '`IMPLEMENTED` architecture decision' in row
    assert 'runtime pending' in row
    assert '| Merge commit | Not merged |' not in card
    assert 'Once this ADR merges' not in card
    assert 'Accepted in review' not in card
    assert f'https://github.com/LuigiFerronatto/TESSERA/pull/{pr}' in audit


def test_adr_reconciliation_preserves_failure_and_pending_runtime_boundaries():
    card349 = (ROOT / 'docs/process/test-cards/349-single-source-selection-authority.md').read_text()
    card350 = (ROOT / 'docs/process/test-cards/350-explicit-id-collision-diagnostics.md').read_text()
    card361 = (ROOT / 'docs/process/test-cards/361-mcp-startup-readiness.md').read_text()
    assert 'failed the unrelated ledger concurrent-initialization test' in card349
    assert 'runtime error code is not implemented' in card350
    assert '#190 cannot rely on' in card361
    assert 'default-timeout startup until that runtime delivery is validated' in card361
