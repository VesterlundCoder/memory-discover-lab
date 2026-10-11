"""Generate a standalone Swedish scientific report with real baseline plots."""
import argparse
import base64
import html
import io
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from memorylab.common import read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="baselines/teller2025")
    parser.add_argument("--verification", default="verification_v05_final/report.json")
    parser.add_argument("--out", default="baselines/teller2025/report.html")
    args = parser.parse_args()
    root = Path(args.baseline)
    s = read_json(root/"summary.json")
    fits = read_json(root/"readout_window_noise_fit.json")
    held = read_json(root/"spatial_holdout.json")
    manifest = read_json(root/"fetch_manifest.json")["artifacts"]
    verification = read_json(args.verification)

    def load(name):
        return np.loadtxt(root/"cache"/manifest[name]["relative_path"], delimiter=";")

    windows = load("5_xaxis.csv")
    means = load("5_yaxis2_F.csv")
    low, high = load("5_yaxis2_Fmin.csv"), load("5_yaxis2_Fmax.csv")
    f = load("8b_F.csv")
    fmin, fmax = load("8b_Fmin.csv"), load("8b_Fmaxn.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.7, 4.5), constrained_layout=True)
    colors = ["#3472a2", "#277a55", "#ac5938"]
    for i, row in enumerate(fits["fits"]):
        label = "Par "+",".join(str(x) for x in row["pair"])
        axes[0].plot(windows, means[i], color=colors[i], label=label, lw=1.5)
        axes[0].fill_between(windows, low[i], high[i], color=colors[i], alpha=.12)
        axes[0].plot(windows, row["predictions"], color=colors[i], ls="--", lw=1.2)
    axes[0].axvspan(200, 600, color="#999999", alpha=.06)
    axes[0].axvspan(800, 1250, color="#3472a2", alpha=.04)
    axes[0].set(xlabel="Detektionsfönster (ns) – inte lagringstid", ylabel="Betingad medelfidelity",
                title="Path: mätdata, MC-intervall och brusmodell", ylim=(.80, 1.0))
    axes[0].legend(loc="lower left", fontsize=9)
    cells = np.arange(1, 11)
    for idx, label, marker, color in [(np.arange(0,10,2), "Kalibrering", "o", "#3472a2"),
                                      (np.arange(1,10,2), "Undanlagda celler", "s", "#ac5938")]:
        axes[1].errorbar(cells[idx], f[idx], yerr=np.stack([f[idx]-fmin[idx],fmax[idx]-f[idx]]),
                         fmt=marker, color=color, capsize=3, label=label)
    mu, se = held["fitted_average_fidelity"], held["fit_standard_error"]
    axes[1].axhline(mu, color="#277a55", label="Gemensam modell")
    axes[1].axhspan(mu-se, mu+se, color="#277a55", alpha=.1)
    axes[1].set(xlabel="Time-bin-minnescell", ylabel="Betingad medelfidelity",
                title="Spatialt holdout-test vid fast driftpunkt", xticks=cells, ylim=(.85,.97))
    axes[1].legend(loc="lower left", fontsize=9)
    for ax in axes:
        ax.grid(alpha=.18)
    image = io.BytesIO()
    fig.savefig(image, format="png", dpi=170)
    plt.close(fig)
    encoded = base64.b64encode(image.getvalue()).decode()
    point = s["operating_point"]
    ci = s["network_retrieved_fraction_95CI"]
    negatives = "".join(f"<tr><td>{','.join(map(str,r['pair']))}</td><td>{r['maximum_heldout_pointwise_z']:.2f}</td><td>Modellförkastad</td></tr>" for r in fits["negative_control_model"]["fits"])
    body = f"""<!doctype html><html lang="sv"><meta charset="utf-8"><title>WestQuant – experimentell minnesbaslinje</title>
    <style>body{{font:16px/1.55 system-ui,sans-serif;color:#193043;background:#f4f6f8;margin:0}}main{{max-width:1060px;margin:auto;padding:36px;background:white}}h1{{font-size:32px;line-height:1.15}}h2{{margin-top:32px;font-size:23px}}table{{border-collapse:collapse;width:100%;margin:18px 0}}td,th{{text-align:left;padding:9px;border-bottom:1px solid #dce3e7;vertical-align:top}}th{{background:#edf2f4}}.status{{padding:16px 20px;border-left:5px solid #277a55;background:#eef6f2}}.limit{{padding:16px 20px;border-left:5px solid #ac5938;background:#fff6ef}}img{{width:100%;height:auto}}code{{background:#eef2f4;padding:2px 5px}}pre{{overflow:auto;background:#eef2f4;padding:16px}}a{{color:#23678d}}small{{color:#496072}}@media print{{body{{background:white}}main{{padding:0}}}}</style>
    <main><small>WestQuant Memory Discovery Lab v0.5 · reproducerbar forskningsbaslinje</small>
    <h1>Öppna experimentdata till QuTiP och SeQUeNCe</h1>
    <div class="status">Dataåteranalysen är utförd, en effektiv kanal är kalibrerad och simulatorerna har körts.
    {verification['tests_run']} program- och integrationstester passerar, {verification['skipped']} är hoppade över.</div>
    <p>Baslinjen är Pr³⁺:Y₂SiO₅ i Teller et al., Physical Review X 15, 031053 (2025).
    Den är vald för öppna data och en verklig optisk skriv–lagra–läs-funktion. Den används som metodbaslinje och är ingen rangordning av dagens bästa minnen.</p>
    <p><a href="https://doi.org/10.1103/z6lc-qw2d">Publicerad artikel</a> ·
    <a href="https://doi.org/10.5281/zenodo.14929997">Författarnas öppna CSV-data, CC BY 4.0</a>.</p>
    <h2>Experimentet och vad som reproduceras</h2>
    <table><tr><th>Resultat</th><th>Beräknat ur öppna data</th><th>Publicerat</th></tr>
    <tr><td>Path-qubits, 30 tillstånd</td><td>{100*s['experimental_reanalysis']['path_six_state_average']:.3f} %</td><td>95 ± 2 %</td></tr>
    <tr><td>Time-bin-qubits, 60 tillstånd</td><td>{100*s['experimental_reanalysis']['time_bin_six_state_average']:.3f} %</td><td>91 ± 2 %</td></tr>
    <tr><td>Driftpunkt i simulatorerna</td><td>Par 5,6; path-qubit; 3 K; 606 nm</td><td>8 µs spinlagring + 10 µs AFC = 18 µs totalt</td></tr>
    <tr><td>Fidelity vid 270 ns detektionsfönster</td><td>{100*point['conditional_average_fidelity']:.3f} %, MC-std {100*point['fidelity_standard_error']:.3f} procentenheter</td><td>Ingen bakgrundssubtraktion</td></tr></table>
    <p>De 90 tillstånden reproducerar figurernas medel till flyttalsprecision. Datasetet ger {s['catalog']['observations']} katalogiserade observationer
    och {s['source_artifacts']} källartefakter med verifierade kontrollsummor. Proberna är svaga koherenta tillstånd på enfotonnivå. Fideliteten är betingad på detektion.</p>
    <h2>Jämförelser som hållits undan</h2>
    <p>Fem time-bin-celler används för kalibrering och fem andra för jämförelse. Största avvikelsen är
    {held['maximum_absolute_z']:.2f} kombinerade standardavvikelser, under den angivna gränsen 3.
    Det är ett spatialt test inom samma dataset; gemensamma systematiska fel är inte kvantifierade.
    Path-kanalen kalibreras separat. Detta är ingen oberoende experimentreplikation eller unik kanaltomografi.</p>
    <img alt="Uppmätta fideliteter mot detektionsfönster och ett spatialt holdout-test" src="data:image/png;base64,{encoded}">
    <p><small>Vänster: heldragen mätdata, skuggade MC-intervall och streckad fenomenologisk brusmodell.
    Fönster ≤600 ns används i fit, ≥800 ns jämförs; de delar fotonräkningar och är korrelerade.
    Höger: kalibreringsceller och undanlagda celler vid 295 ns detektionsfönster.</small></p>
    <h2>Negativ modellkontroll</h2>
    <p>En konstant fidelity som ignorerar detektionsfönstret missar mätdata. Den negativa kontrollen sparas, liksom passeringarna.
    Den mer flexibla brusmodellen når en parametergräns i par 5,6 och identifierar inte entydiga materialparametrar.</p>
    <table><tr><th>Path-par</th><th>Största pointwise-avvikelse, i uppmätt std</th><th>Konstantfidelity-modell</th></tr>{negatives}</table>
    <h2>Den faktiska nätverkskörningen</h2>
    <p>En CPTP-kanal med separat signalbortfall överförs till SeQUeNCe 1.2:s händelsekärna och täthetsmatrishanterare.
    Fyra seeds, {s['network_attempts']:,} försök och {s['network_retrieved_pairs']} återlästa par har körts.
    Simulerad betingad Bell-fidelity är {100*s['simulated_conditional_Bell_fidelity']:.3f} %.</p>
    <table><tr><th>Kontroll</th><th>Resultat</th></tr>
    <tr><td>Analytisk kanal mot QuTiP, största Choi-skillnad</td><td>{s['analytic_qutip_max_choi_error']:.2e}</td></tr>
    <tr><td>SeQUeNCe mot analytisk gemensam täthetsmatris</td><td>{s['network_max_density_error']:.2e}</td></tr>
    <tr><td>Förväntad framgångssannolikhet per försök</td><td>{s['network_expected_success_probability']:.8f}</td></tr>
    <tr><td>Monte Carlo-fraktion, 95 % Wilson-intervall</td><td>[{ci[0]:.8f}, {ci[1]:.8f}]</td></tr></table>
    <p>Den antagna signalacceptansen {100*point['signal_retrieval_probability']:.4f} % bygger på
    klassiskt uppmätta delöverföringar och 42 % fotonacceptans. Fiber, filter, detektor och analysförlust ingår inte.
    Nätverket antar idealt initialt Bell-par och ideal förlustflagga; fluorescensens falska heralds,
    förberedelse, länkgenerering och routing är inte validerade. Resultatet är en simulatorintegration och ingen uppmätt nätverkshastighet.</p>
    <h2>Vad som återstår före nya material bedöms</h2>
    <div class="limit"><strong>T₂ är inte bestämt.</strong> Detektionsfönster är inte lagringstid.
    Modellen accepterar endast den granskade driftpunkten 18 µs vid 3 K och avvisar extrapolation.
    Grinden för nya materialrankningar är därför fortfarande blockerad.</div>
    <p>Nästa underlag måste ge fidelity och utläsningseffektivitet vid samma varierade lagringstider,
    med temperatur, inputfotonstatistik, antal försök, signal/brusräkningar och postselektion.
    Separat uppmätt spineko-T₂ räcker inte för att certifiera ett läsbart nätverksminne.</p>
    <p>En histogramfil med oklart tidsmått är spärrad för fysikalisk inferens. Två missvisande CSV-rubriker har explicit,
    figurverifierad mappning. Datagranskningen är utförd beräkningsmässigt; extern sakkunniggranskning återstår.</p>
    <h2>Kör själv</h2><pre>python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c constraints-tested.txt -e '.[quantum,network]'
python -m memorylab reproduce examples/teller2025_baseline.json --out baselines/teller2025
# Samma körning med inkluderade källfiler och utan nätåtkomst:
python -m memorylab reproduce examples/teller2025_baseline.json --out baselines/teller2025 --offline</pre>
    <p>Fullständig parameter- och källgranskning finns i <code>BASELINE.md</code>. Maskinläsbara resultat,
    seeds, datalås, kodfingeravtryck och programversioner finns i paketet.</p>
    </main></html>"""
    Path(args.out).write_text(body, encoding="utf-8")
    print(json.dumps({"report": args.out, "size_bytes": Path(args.out).stat().st_size}))


if __name__ == "__main__":
    main()
