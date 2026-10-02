"""Public history is neutral, source-backed and explicit about target status."""
from pathlib import Path
import hashlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'docs/assets/architecture'


def test_all_six_diagrams_are_deterministic_and_mapped():
    paths=sorted(ASSETS.glob('*.svg'))
    assert len(paths)==6
    before={p.name:p.read_bytes() for p in paths}
    subprocess.run([sys.executable,str(ROOT/'scripts/render_architecture_diagrams.py')],check=True,cwd=ROOT)
    assert before=={p.name:p.read_bytes() for p in paths}
    guide=(ROOT/'docs/ARCHITECTURE_DIAGRAMS.md').read_text()
    for p in paths:
        assert p.name in guide
        doc=ET.fromstring(p.read_text())
        assert doc.attrib['role']=='img'
        assert doc.attrib['data-status'] in {'current','experimental'}
        text=' '.join(doc.itertext())
        assert '20814a47' in text
        assert 'EXPERIMENTAL TARGET' in text if doc.attrib['data-status']=='experimental' else 'CURRENT FOUNDATION' in text
        assert not any(n.tag.endswith(('script','image')) for n in doc.iter())
        assert doc.find('{http://www.w3.org/2000/svg}title').text
        assert doc.find('{http://www.w3.org/2000/svg}desc').text


def test_private_project_narratives_and_assets_are_absent():
    legacy=''.join(('L','A','O'))
    company=''.join(('B','l','i','p'))
    private_slug='-'.join(('lab','autonomous','officer'))
    forbidden=re.compile(r'(?i)(?<![a-z])'+legacy+r'(?:\b|_)|'+company+'|'+re.escape(private_slug))
    for family in ('docs','archive'):
        for p in (ROOT/family).rglob('*'):
            if not p.is_file():continue
            assert not forbidden.search(p.name),p
            if p.suffix in {'.md','.html','.svg','.py'}:
                assert not forbidden.search(p.read_text()),p


def test_historical_deck_has_same_slide_count_and_only_existing_local_images():
    text=(ROOT/'docs/slides/tessera-apresentacao.html').read_text()
    assert len(re.findall(r'<section\b',text))==22
    assert 'Historical demo' in text
    for ref in re.findall(r'<img[^>]+src="([^"]+)"',text):
        assert not ref.startswith(('http:','https:','data:'))
        assert (ROOT/'docs/slides'/ref).resolve().is_file(),ref
    assert 'tessera-hero-nobg-sm.svg' in text


def test_readme_embeds_one_architecture_diagram_and_history_has_source_links():
    text=(ROOT/'README.md').read_text()
    assert len(re.findall(r'!\[[^]]*\]\(docs/assets/architecture/',text))==1
    history=(ROOT/'docs/PR_EVOLUTION_95.md').read_text()
    assert 'Public-history normalization' in history
    assert '20814a47ec0f72d7bea0639e0b057df1ecf5cded/docs/PR_EVOLUTION_95.md' in history
    docs_map=(ROOT/'docs/README.md').read_text()
    assert 'Which document wins' in docs_map
    assert 'Legacy examples are project-neutral' in docs_map
