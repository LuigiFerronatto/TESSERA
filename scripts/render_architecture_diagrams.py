"""Regenerate six editable SVG contract diagrams. No runtime or external assets."""
from pathlib import Path
import textwrap
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/architecture'
BASELINE = '20814a47 / 2026-10-02'


def el(parent, tag, attrs=None, text=None):
    x = ET.SubElement(parent, '{'+NS+'}'+tag, {k:str(v) for k,v in (attrs or {}).items()})
    if text is not None:x.text=text
    return x


def text(parent,x,y,value,size=21,color='#142b45',weight='normal'):
    return el(parent,'text',{'x':x,'y':y,'font-size':size,'fill':color,'font-weight':weight,'font-family':'DejaVu Sans, Arial, sans-serif'},value)


def box(parent,x,y,w,h,title,body,status='current'):
    future=status=='experimental'
    el(parent,'rect',{'x':x,'y':y,'width':w,'height':h,'rx':6,'fill':'#fff7ed' if future else '#edf5fb','stroke':'#b85b0e' if future else '#28597a','stroke-width':2,'stroke-dasharray':'8 5' if future else 'none'})
    text(parent,x+18,y+34,title,18 if w<250 else 22,weight='bold')
    for i,line in enumerate(textwrap.wrap(body,width=max(15,int((w-36)/10)))):
        text(parent,x+18,y+66+i*26,line,18)


def arrow(parent,x1,y1,x2,y2,label=None):
    el(parent,'line',{'x1':x1,'y1':y1,'x2':x2,'y2':y2,'stroke':'#516a7e','stroke-width':2,'marker-end':'url(#arrow)'})
    if label:text(parent,(x1+x2)/2-60,(y1+y2)/2-12,label,16)


def canvas(title,subtitle,status='current'):
    s=ET.Element('{'+NS+'}svg',{'width':'1400','height':'540','viewBox':'0 0 1400 540','role':'img','data-status':status})
    el(s,'title',text=title);el(s,'desc',text=subtitle)
    el(s,'rect',{'width':1400,'height':540,'fill':'#ffffff'})
    defs=el(s,'defs');m=el(defs,'marker',{'id':'arrow','viewBox':'0 0 10 10','refX':9,'refY':5,'markerWidth':8,'markerHeight':8,'orient':'auto-start-reverse'});el(m,'path',{'d':'M0 0 L10 5 L0 10 z','fill':'#516a7e'})
    text(s,44,53,title,32,weight='bold');text(s,44,89,subtitle,18,'#516a7e')
    label='EXPERIMENTAL TARGET: conditional, not delivered' if status=='experimental' else 'CURRENT FOUNDATION: audited canonical baseline'
    text(s,44,489,label,18,'#a44b00' if status=='experimental' else '#23506c',weight='bold')
    text(s,44,520,'Baseline '+BASELINE+'     Sources and limits: docs/ARCHITECTURE_DIAGRAMS.md',14,'#516a7e')
    return s


def save(name,svg):
    OUT.mkdir(parents=True,exist_ok=True);ET.indent(svg,space='  ');ET.ElementTree(svg).write(OUT/name,encoding='unicode',xml_declaration=True)


def main():
    s=canvas('Agent and TESSERA responsibilities','The consuming agent owns decisions. TESSERA supplies scoped source-backed evidence.')
    box(s,44,170,330,210,'Consuming agent','Task interpretation, tools, decisions and final answer')
    box(s,536,170,360,210,'TESSERA','Canonical writes, indexing, retrieval and inspectable provenance')
    box(s,1050,170,305,210,'Source records','Generated Markdown and selected external documents')
    arrow(s,374,216,531,216,'request');arrow(s,536,330,379,330,'evidence');arrow(s,1050,235,901,235,'read');arrow(s,896,330,1045,330,'gated write')
    save('agent-boundary.svg',s)
    s=canvas('Memory lifecycle','Source truth stays separate from disposable projections and retrieval results.')
    nodes=[('Sources','Canonical text and explicit scope'),('Normalize','Identity, metadata and source hashes'),('Derived views','Graph / lexical index and Evidence Ledger'),('Retrieve','Ranked candidates and exact-or-null spans'),('Inspect','Consuming agent checks source evidence')]
    for i,(a,b) in enumerate(nodes):
        x=44+i*272;box(s,x,185,224,215,a,b)
        if i<4:arrow(s,x+224,290,x+265,290)
    save('memory-lifecycle.svg',s)
    s=canvas('Current Foundation architecture','These components exist on the dated baseline. Optional assistance is separate.')
    box(s,44,145,350,110,'Configuration','Generated store, readable sources, derived index')
    box(s,44,300,350,125,'Source input','Markdown and TXT; canonical normalization and segmentation')
    box(s,536,190,360,190,'Deterministic core','Write gate, incremental graph, TF-IDF and structured evidence')
    box(s,1050,145,305,110,'Public surfaces','Python API, CLI and optional stdio MCP')
    box(s,1050,300,305,125,'Optional assistance','Explicit provider, heuristic baseline and free-text output')
    arrow(s,394,200,531,240);arrow(s,394,360,531,330);arrow(s,896,250,1045,200);arrow(s,896,335,1045,355)
    save('foundation-current.svg',s)
    s=canvas('Experimental cognitive-continuity target','Owner cards define each missing contract. This diagram does not select defaults.','experimental')
    nodes=[('Construction','#138 episodes; #136 extraction; #137 lineage'),('Durable evolution','#73 revisions; #15 time; #16 supersession'),('Evidence state','#139 / #140 planning; #141 state; #20 sufficiency'),('Working context','#169 Context Compiler; #167 task packets'),('Agent lifecycle','#171 semantic API; #196 hooks; #19 admission')]
    for i,(a,b) in enumerate(nodes):
        x=44+i*272;box(s,x,175,224,235,a,b,'experimental')
        if i<4:arrow(s,x+224,290,x+265,290)
    save('target-experimental.svg',s)
    s=canvas('Experimental roadmap','Conceptual research progression. Dependencies and selection remain in ROADMAP.','experimental')
    nodes=[('Foundation','Current source, safety, config and retrieval baseline','current'),('Intelligence','Planned model profiles and optional semantic retrieval','experimental'),('Adaptive','Planned admission and retrieval-strategy decisions','experimental'),('State','Planned temporal, conflict and contextual reconstruction','experimental'),('Learning','Planned utility feedback and experience evaluation','experimental')]
    for i,(a,b,c) in enumerate(nodes):
        x=44+i*272;box(s,x,185,224,215,a,b,c)
        if i<4:arrow(s,x+224,290,x+265,290)
    save('roadmap-experimental.svg',s)
    s=canvas('Structured evidence anatomy','Illustrative field groups from the current retrieval contract, not a new schema.')
    box(s,44,170,395,230,'Identity and content','Memory ID, type, body and source path')
    box(s,502,170,395,230,'Provenance','Evidence ID, document identity, version hashes and exact-or-null spans')
    box(s,960,170,395,230,'Retrieval context','Relevance score and related IDs; freshness checked separately')
    text(s,44,446,'Relevance does not establish authority, confidence, validity or sufficient evidence.',20,'#516a7e')
    save('structured-evidence.svg',s)

if __name__=='__main__':main()
