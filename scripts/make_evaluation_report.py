"""Render the executed evaluation addendum; does not modify the original paper."""
from pathlib import Path
import csv,json,statistics
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold")
ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'evaluation/results'
load=lambda n:json.loads((RESULTS/n/'summary.json').read_text())
one=load('step1-executed');two=load('step2-software-control');three=load('step3-executed');four=load('step4-executed')
out=ROOT/'evaluation/reports';out.mkdir(parents=True,exist_ok=True)
styles=getSampleStyleSheet()
for name in styles.byName:
    styles[name].fontName = 'DejaVuSans-Bold' if name in ('Title','Heading1','Heading2','Heading3') else 'DejaVuSans'
styles.add(ParagraphStyle(name='TextSmall',parent=styles['BodyText'],fontSize=8,leading=10.5,spaceAfter=5))
styles['BodyText'].fontSize=9;styles['BodyText'].leading=12;styles['BodyText'].spaceAfter=7
styles['Heading1'].fontSize=17;styles['Heading1'].leading=21
styles['Heading2'].fontSize=13;styles['Heading2'].leading=16
styles['Title'].fontSize=23;styles['Title'].leading=27
story=[]
def p(t,style='BodyText'):story.append(Paragraph(t,styles[style]))
def heading(t):p(t,'Heading2')
def table(rows,widths):
    cells=[[Paragraph(escape(str(c)),styles['TextSmall']) for c in row] for row in rows]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef6')),('VALIGN',(0,0),(-1,-1),'TOP'),
       ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#bac5d4')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
       ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(t);story.append(Spacer(1,10))
def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#bac5d4'));canvas.line(44,38,551,38)
    canvas.setFont('DejaVuSans',8);canvas.drawString(44,25,'WestQuant | System evaluation addendum | 10 October 2026')
    canvas.drawRightString(551,25,str(doc.page))
p('WestQuant Memory Discovery Lab','Title')
p('Executed system evaluation addendum','Heading1')
p('David Vesterlund | WestQuant | 10 October 2026','TextSmall')
p('Repository: https://github.com/VesterlundCoder/memory-discover-lab','TextSmall')
p('<b>Outcome.</b> The lab agrees with an independently written NumPy/SciPy reference on the declared matched workload. Seven constructed contract faults are blocked with passing positive controls. Local performance and checkpoint tests pass. A second-family control is executable, but a second experimental physical baseline remains pending.')
heading('1. Executed matched comparison')
p('Both arms receive identical reviewed conditions. The reference imports no lab channel constructor: it exponentiates the column-vectorized Lindblad generator, then independently constructs the erasure-inclusive Choi matrix. One experiment-constrained optical point and twelve hypothetical Markov profiles cover 73 channel-age points. The two source parsers consume the same SHA256-verified experimental files.')
table([['Metric','Executed result','Gate'],['Profiles / channel-age points','13 / 73','Specified workload'],
       ['Full Choi maximum error',f"{one['max_full_choi_error']:.5g}",'<= 1e-8'],
       ['Six-state output maximum error',f"{one['max_state_error']:.5g}",'<= 1e-8'],
       ['Conditional fidelity maximum error',f"{one['max_fidelity_error']:.5g}",'<= 1e-8'],
       ['Acceptance maximum error',f"{one['max_acceptance_error']:.5g}",'<= 1e-8'],
       ['Processed fidelity scalars','90; maximum discrepancy 0','<= 1e-8']], [225,155,127])
table([['Experimental file','Values','Mean (both arms)'],['4.csv','30',f"{one['data_results'][0]['mean_direct']:.10f}"],
       ['8a.csv','60',f"{one['data_results'][1]['mean_direct']:.10f}"]],[180,95,232])
p('The source is Teller et al., Zenodo record 14929997, version v1 (DOI 10.5281/zenodo.14929997). These are released processed fidelities, not independent raw-count measurements. The measured optical operating point does not identify physical spin T2.','TextSmall')
heading('Local construction timing')
p(f"Five randomized-order warm repeats per arm: median lab {one['median_construction_s']['westquant']:.5f} s and direct reference {one['median_construction_s']['direct']:.5f} s. Export, metadata and validation costs are not equalized; file IO, fitting, network events and downstream solvers are excluded. These are descriptive local timings, not evidence of end-to-end speed superiority.")
p('The configuration, seed, actual timing order, input hashes, package environment, thread settings and source fingerprints are retained in evaluation/results/step1-executed. Results are retrospective, not prospectively preregistered.','TextSmall')
story.append(PageBreak())
p('Interpretation and existing workflows','Heading1')
p('Agreement verifies that integration preserves the supplied equations and processed data. It does not establish new physics, a new material lifetime, less researcher effort or general superiority over custom scripts. General workflow engines can host the same domain contracts.')
related=json.loads((ROOT/'evaluation/config/related_tools.json').read_text())
table([['Tool','Existing capability / relationship','Step-1 execution']]+[[r['tool'],r['existing_capability']+' '+r['relationship'],r['execution']] for r in related['tools']],[85,322,100])
p('AiiDA already supports provenance and caching. It was audited through its documentation, not installed and benchmarked against this lab. The contribution evaluated here is reusable quantum-memory condition, evidence, age and channel semantics. The table is a scoped documentary comparison, not an exhaustive novelty claim.')
heading('Primary documentation')
for r in related['tools']:p(escape(r['tool']+': '+r['source_url']),'TextSmall')
heading('Matched conventions')
p('Qubit states are column-vectorized; frequencies are in Hz and evolution includes 2*pi. Population relaxation and independent pure dephasing are separate rates. Depolarization uses E(rho)=(1-p)rho+p*I/2. State-independent retrieval failure is represented by an orthogonal erasure outcome. Choi matrices are unnormalized with trace equal to input dimension. Absolute-age write-store-read channels are applied once to the original input state.')
story.append(PageBreak())
p('Additional executed checks and remaining evidence','Heading1')
table([['Step','Implemented and executed','Remaining limitation'],
       ['2: second family',f"41-point molecular-spin software control passes (max normalized residual {two['max_normalized_error']:.3g}); hypothetical interface exported with opt-in",'Real audited curve, Hamiltonian and optical interface are still required'],
       ['3: ablations',f"{three['blocked_cases']}/{three['invalid_contract_cases']} invalid contracts blocked; all positive controls pass",'Constructed faults, not researcher error incidence'],
       ['4: performance','Nine cold studies; 108 cold jobs and 108 checkpoint reuses; invariant channel results','Single environment; bounded small models; no claim of large-scale scalability'],
       ['Tests','75 original + 7 evaluation tests pass','Independent external reproduction pending']], [88,292,127])
perf=list(csv.DictReader((RESULTS/'step4-executed/performance.csv').open()))
rows=[['Workers','Jobs per study','Cold median [min,max], s','Resume median, s']]
for w in [1,2,4]:
    selected=[r for r in perf if int(r['workers'])==w]
    cold=[float(r['cold_s']) for r in selected];warm=[float(r['resume_s']) for r in selected]
    rows.append([w,12,f'{statistics.median(cold):.3f} [{min(cold):.3f}, {max(cold):.3f}]',f'{statistics.median(warm):.4f}'])
table(rows,[62,95,215,135])
p('Each worker uses one native numerical thread. Times include subprocess startup, calculation and artifact IO. Resume reuses terminal-result checkpoints. Parent peak RSS and largest terminated child peak RSS are recorded separately, not as aggregate concurrent memory. Missing-data and actual process-timeout probes pass. Resume from a completed partial checkpoint succeeds; no forced crash or power-loss test was performed.','TextSmall')
heading('Reproduce from a fresh clone')
for command in ['git clone https://github.com/VesterlundCoder/memory-discover-lab.git','cd memory-discover-lab','python -m venv .venv','source .venv/bin/activate','python -m pip install -e ./lab','python scripts/evaluate_system.py step1 --out evaluation/results/new-step1','python -m unittest discover -s evaluation/tests -v']:
    p(escape(command),'TextSmall')
p('First-run step 1 automatically fetches two pinned Zenodo files and verifies their hashes. Full original article reproduction needs optional dependencies and source retrieval; see evaluation/README.md. Unverified third-party caches are absent from the public repository.','TextSmall')
heading('Next physical and publication gates')
p('A measured second-family case must provide reviewed complex pure-dephasing observations, uncertainties, model parameters, isotope/composition, tensor frames, temperature, field and pulse conditions. A coherence curve alone cannot validate an optical quantum memory. Independent clean-environment reproduction and scientific review are reserved for the author and colleagues. No hardware experiment, new-material T2 prediction, statistical prediction error margin, better-than-SOTA result, DOI or peer-review acceptance is claimed.')
SimpleDocTemplate(str(out/'WestQuant_System_Evaluation_Step1.pdf'),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=42,bottomMargin=48,
                  title='WestQuant: Executed System Evaluation',author='David Vesterlund').build(story,onFirstPage=footer,onLaterPages=footer)
print(out/'WestQuant_System_Evaluation_Step1.pdf')
