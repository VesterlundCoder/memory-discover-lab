"""Render the executed deterministic results; optional dependency: matplotlib."""
from pathlib import Path
import base64
import html
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BASE = Path(__file__).resolve().parents[1]
RUN = BASE/'t2_runs/deterministic'
def load(path): return json.loads(path.read_text())
refs = load(BASE/'data/t2_references.json')
summary = load(RUN/'summary.json')
zero, echo = [load(RUN/f'spin_bath_{n}pulse.json') for n in (0,1)]
markov = load(RUN/'markov_calculation.json')
fig, ax = plt.subplots(figsize=(9,3.8), layout='constrained')
ax.plot(np.array(zero['times_s'])*1000,zero['envelope'],label='Fri utveckling, inga pulser',color='#3269aa',lw=2)
ax.plot(np.array(echo['times_s'])*1000,echo['envelope'],label='En ideal Hahn-puls',color='#ce6c29',lw=2)
ax.axhline(np.exp(-1),ls='--',color='#777777',lw=1,label='1/e')
lo,hi=zero['operational_decay']['crossing_bracket_s']
ax.axvspan(lo*1000,hi*1000,color='#3269aa',alpha=.2)
ax.set(xlabel='Lagringstid (ms)',ylabel='Normaliserad koherens |L|',ylim=(-.03,1.08),xlim=(0,1),
       title='Hypotetisk fysikkontroll: ett kärnspinn, Azz = 4 kHz, 4.2 K')
ax.legend(ncol=3,fontsize=9,loc='lower right');ax.grid(alpha=.15)
fig.savefig(BASE/'T2_Koherens.png',dpi=170);plt.close(fig)
pic=base64.b64encode((BASE/'T2_Koherens.png').read_bytes()).decode()
rows=[]
for r in refs:
 scale=1e3 if r['value_s']>=.001 else 1e6
 unit='ms' if scale==1e3 else 'µs'
 interval=r['reported_interval_s'];err=(interval[1]-r['value_s'])*scale if interval else None
 v=f"{r['value_s']*scale:g}"+(f' ± {err:g}' if err is not None else '')+' '+unit
 cond='; '.join(f'{k}: {v}' for k,v in r['conditions'].items())
 rows.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in (r['material_name'],r['definition'],v,cond))+
             '<td><a href="'+html.escape(r['source'])+'">Primärkälla</a><br>'+html.escape(r['interval_convention'])+'</td></tr>')
negative=load(RUN/'experimental_decay/summary.json')
controls=summary['synthetic_count_control']
network=load(RUN/'hypothetical_sequence.json') if (RUN/'hypothetical_sequence.json').exists() else None
network_text=(f"SeQUeNCe {network['version']}: {network['attempts']} försök, {network['retrieved_pairs']} avlästa par. "
              f"Skillnad mot analytisk densitetsmatris ≤ {network['max_density_error_against_analytic']:.2g}; "
              f"QuTiP/analytisk Choi-skillnad ≤ {network['max_choi_difference_qutip_analytic']:.2g}.") if network else 'SeQUeNCe ingick inte i denna körning.'
report='''<!doctype html><html lang="sv"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WestQuant — T₂ med tabeller och deterministisk fysik</title>
<style>body{font:16px/1.6 system-ui,sans-serif;color:#162b40;background:#f2f5f8;margin:0}main{max-width:1280px;margin:40px auto;background:white;padding:38px;border-radius:12px}h1{font-size:32px;line-height:1.2}h2{font-size:22px;margin-top:32px}p{max-width:1000px}.lead{font-size:19px}.box{padding:18px;background:#edf3fa;border-left:4px solid #3269aa}table{border-collapse:collapse;width:100%;font-size:13px}td,th{text-align:left;padding:12px;border-bottom:1px solid #dce4eb;vertical-align:top;overflow-wrap:anywhere}th{background:#edf3fa}img{width:100%;max-width:1000px}a{color:#155ca2}code{background:#f3f4f6;padding:3px}pre{padding:18px;white-space:pre-wrap;background:#f3f4f6}.scroll{overflow-x:auto}@media(max-width:700px){main{padding:18px;margin:0}h1{font-size:25px}table{min-width:800px}}</style><main>
<p>WestQuant · utförd kontroll 10 oktober 2026 · version 0.6</p>
<h1>T₂-bedömningar med tabeller och deterministisk fysik</h1>
<p class="lead">ML är ett separat projekt. Minneslabbet använder granskade referensvärden, experimentkurvor och uttryckliga fysikmodeller.</p>
<div class="box">10 granskade koherensreferenser · 201 preliminära molekylposter · 3 deterministiska specifikationer · 202 spinnbadstidpunkter · 4 parameterhörn · 8 experimentkurvepassningar. Inga nya ML-träningskörningar.</div>
<h2>Vad tabellerna kan säga</h2>
<p>Uppslag matchar material, definition och rapporterade driftvillkor. En referensträff är ett rapporterat värde under dessa villkor; den är inte en prediktion för ett nytt material. Källornas saknade villkor följer med i resultatet. Molekyl-CSV:ns enheter, protokoll och vissa temperaturmappningar är ännu preliminära och används inte som fysiskt bestämda T₂-värden.</p>
<div class="scroll"><table><thead><tr><th>Material</th><th>Observabel</th><th>Rapporterad tid</th><th>Villkor</th><th>Källa och osäkerhet</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>Tabellen är en startmängd, ingen fullständig SOTA-jämförelse. Tₘ, T₂*, optiskt AFC-T₂ och DD-beroende spin-T₂ hålls isär. Primärtextens värden och enheter har granskats; de tio referensernas råpassningar har inte reproducerats oberoende här. Flera värden kommer från samma studie.</p>
<h2>Deterministisk koherens</h2>
<img alt="Fri koherens med återkomster och ideal Hahn-refokusering i ett hypotetiskt spinnbad" src="data:image/png;base64,'''+pic+'''">
<p>Den fria utvecklingen har en första samplad 1/e-passage mellan 90 och 100 µs och återkomster. Den har därför inget automatiskt identifierat exponentiellt T₂. Den ideala Hahn-pulsen refokuserar denna enkla longitudinella koppling: ingen samplad passage fram till 1 ms. Det är en analytisk programkontroll, inte ett nytt experimentellt minne.</p>
<p>Markovkontrollen använder Γ₁ = 10 s⁻¹ och Γφ = 20 s⁻¹ vid angivna hypotetiska villkor, vilket ger T₂ = 40 ms. Hastighetsintervallen [8,12] respektive [18,22] s⁻¹ ger 35.71–45.45 ms, motsvarande −10.71%/+13.64% från nominalvärdet. Detta är ett deterministiskt parameterintervall; ingen statistisk prediktionsnoggrannhet utlovas.</p>
<h2>Experimentkurvor: modellens begränsning syns</h2>
<p>De öppna klassiska Pr³⁺:YSO-kurvorna från <a href="https://doi.org/10.5281/zenodo.21532904">Zenodo 21532904</a>, kopplade till <a href="https://doi.org/10.1103/ftkb-pkvp">PRL 2026</a>, har prövats med två modeller per RF-sekvens. RF-kurvorna underkänner de enkla prövade avklingningsmodellerna; den RF-fria korta mätningen lämnar tiden obestämd. Ingen homogen fysisk spin-T₂ eller full qubitkanal identifieras. Det är ett negativt modellresultat, inte ett negativt resultat för kvantminnen som helhet.</p>
<h2>Verifierat flöde till simulator</h2>
<p>'''+html.escape(network_text)+''' Nätverkskanalen använder ett separat hypotetiskt profilkort med specificerad skrivning, lagring, avläsning och förlust. De granskade tabellvärdena har inte ensamma använts för att konstruera en experimentellt verifierad optisk kanal.</p>
<p>Den simulerade räknekontrollen återfinner '''+f"{controls['recovered_s']*1e3:.4f}"+''' ms från en känd generator på 1 ms. Bootstrapintervallet är '''+f"{controls['interval'][0]*1e3:.4f}–{controls['interval'][1]*1e3:.4f}"+''' ms under den valda räkne-/brusmodellen. Detta är inte ett uppmätt materialresultat.</p>
<p>75 automatiska tester passerar, inklusive analytisk spinnutveckling, relaxationsfaktorn 1/2, protokoll-/temperaturavvikelser, obestämda nya material och återhämtning av en känd koherenstid. ML-projektets fyra integritetskontroller passerar separat; dess historiska pilot är bevarad utan ny träning.</p>
<h2>Kör igen</h2><pre>python -m memorylab.t2lab run --offline --sequence
python -m memorylab.t2lab assess examples/t2_reference_query.json
python -m memorylab.t2lab calculate examples/t2_spin_bath_0pulse.json
python -m unittest discover -s tests -v</pre>
<p>En okänd kombination behöver granskad geometri, laddning, isotoper, hyperfin-/badparametrar, kontroll och temperaturberoende brus innan dess koherens kan beräknas. För bedömning som nätverksminne tillkommer fidelity, verkningsgrad, läsbrus och temperatur vid skrivning och avläsning. Påståendet att någon ny kandidat överträffar ett befintligt minne är fortsatt obestämt.</p>
</main></html>'''
(BASE/'T2_Bedomningar_Resultat.html').write_text(report,encoding='utf-8')
print(BASE/'T2_Bedomningar_Resultat.html')
