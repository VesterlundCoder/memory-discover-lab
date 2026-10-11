# WestQuant Memory Discovery Lab — v0.6

## Nytt: T₂ från granskade tabeller och deterministiska beräkningar

ML är ett eget projekt. Läs [T2_BEDOMNINGAR.md](T2_BEDOMNINGAR.md) för
källgranskning, tabelluppslag, spinnbad, temperaturvillkor och körda resultat.

```bash
python -m memorylab.t2lab run --offline --sequence
```

Tio granskade referensvärden och 201 preliminära molekylposter ingår.
Den öppna klassiska Pr-baslinjen används även som negativ modellkontroll.
Nya kombinationer får inte ett T₂-värde utan tillräckligt fysikunderlag.
Deterministiska kontrollfall och nätverkskanalen är uttryckligen hypotetiska.

## Nytt: experimentdata till verkliga simulatorer

Den första öppna baslinjen är Teller et al., PRX 15, 031053 (2025),
DOI 10.1103/z6lc-qw2d, data DOI 10.5281/zenodo.14929997.
Läs [BASELINE.md](BASELINE.md) för granskade parametrar, osäkerheter,
detektionsfönster, negativa modellresultat och vetenskapliga begränsningar.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c constraints-tested.txt -e '.[quantum,network]'
python -m memorylab reproduce examples/teller2025_baseline.json --out baselines/teller2025
```

Det kommandot hämtar låsta öppna data, granskar kontrollsummor, reproducerar
experimentella medelfideliteter, gör ett spatialt holdout-test, bygger en
fysisk effektiv qubit-kanal och kör både QuTiP och fyra SeQUeNCe-försök.
Alla hämtade källfiler och utförda baslinjeresultat ingår i arkivet.
För en helt lokal omkörning lägger du till `--offline`; flaggan förbjuder
nätåtkomst i baslinjehämtningen. En ofullständig cache ger ett fel.

Baslinjen är en **ändlig driftpunkt**, inte ett uppmätt T2 eller en
mikroskopisk materialmodell. `discovery_gate.json` blockerar jämförelser
om bättre nya material tills tidsberoende fidelity, effektivitet och
brus är validerade tillsammans. De äldre minnesscenarierna nedan är
fortfarande uttryckligen syntetiska programtester.

Körbart Pythonlabb för datahämtning, materialinventering, fysikmodeller,
kalibrering, systematiska körningar och export till kvantnätverk.
Basfunktioner: Python 3.10+. SeQUeNCe 1.2 och det fullständiga flödet
kräver Python 3.12+. Verifierat i Linux; Mac-installation
ingår inte i den utförda verifieringen.

## Börja här

Packa upp arkivet, öppna westquant-memory-lab i VS Code och kör:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[all]'
python -m memorylab doctor
python -m unittest discover -s tests -v
python -m memorylab pipeline examples/pipeline_full.json --out runs/my_lab
```

Det sista kommandot hämtar data, importerar observationer, genererar 16
isotop/laddningskombinationer, gör två begränsade PySCF-beräkningar,
kör 36 minnesscenarier och exporterar 36 kanalsamlingar.
Minnesscenarierna är **hypotetiska programtester**. De påstår inte att H2
eller någon hämtad molekyl har de angivna optiska minnesegenskaperna.

Mindre installation: python -m pip install -e . och examples/pipeline.json.
Det flödet använder NumPy/SciPy utan PySCF. Installera valfri extra
quantum, chemistry, spin, propagation eller datasets när du behöver den.

## Gemensamt flöde

1. Data-planen väljer källor, filer och budgetar.
2. Råfiler och versionsmanifest sparas; importadaptrar fyller SQLite.
3. Kandidatgeneratorn varierar laddning, 2S, värd och isotop per atomplats.
4. Elektronstruktur och kopplingar beräknas/importeras med separat cache.
5. Familjmodellen ger koherens och full skriv–lagra–läs-kanal.
6. Runnern varierar parametrar, separerar seeds och checkpointar.
7. Nätverksadaptern exporterar Kraus/Choi, förlust, latens och fidelity.

Importen gör inte molekylfingeravtryck eller isotopmassa till ett T2.
En saknad optisk gränsyta eller okänd enhet förblir saknad.

## Kör delarna separat

```bash
python -m memorylab datasets examples/data_plan.json
python -m memorylab catalog data/catalog.sqlite
python -m memorylab catalog data/catalog.sqlite --table observations --out data/observations.json
python -m memorylab generate examples/new_combinations.json
python -m memorylab generate examples/all_elements.json --out data/all_elements.json
python -m memorylab run examples/study.json --dry-run
python -m memorylab run examples/study.json --out runs/study
python -m memorylab run examples/cross_backend_study.json --out runs/cross
python -m memorylab electronic examples/h2_candidate.json examples/pyscf_recipe.json
python -m memorylab simulate examples/pycce_profile.json --times 0,0.00005,0.0001 --out runs/pycce.json
python -m memorylab propagate examples/lambda_eit.json
python -m memorylab external orca examples/h2_candidate.json examples/orca_recipe.json
```

Samma run-kommando mot samma mapp återupptar checkpointade jobb.
ORCA/QE-exekvering kräver --execute och en lokalt installerad binär.
QE behöver periodisk cell, input_data, pseudopotentials och kpts.
couplings orca/qe output_file importerar kopplingsdata genom PyCCE.

## Koppla till nätverk

```bash
python -m memorylab simulate examples/trapped_atom_ion_profile.json --times 0,0.01,1 --out runs/samples.json
python -m memorylab export runs/samples.json --allow-hypothetical --out runs/device.json
python -m memorylab network runs/device.json runs/device.json examples/network_workload.json --allow-hypothetical
```

API för nätverkets händelsehanterare:

```python
import numpy as np
from memorylab.network import load_device

device = load_device("runs/device.json", allow_hypothetical=True)
input_state = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)
result = device.retrieve(input_state, age_s=0.01, rng=np.random.default_rng(17))
if result["success"]:
    retrieved_state = result["density_matrix"]
```

För sammanflätade tvåqubitsystem: gemensam 4×4 täthetsmatris och
subsystem=0 eller 1. Använd ursprungstillståndet vid slutlig läsning;
applicera inte ålderskanalen på nytt vid varje tick.

Detta är ett fungerande gemensamt API och en tvånodsbenchmark.
Versionsspecifika SeQUeNCe/NetSquid/WestQuant-Network-klasser ingår inte.

## Kalibrering och baslinjer

fit tar JSON med times_s, pure_coherence_amplitude, standard_errors,
conditions och provenance. Den testar en normaliserad exponentiell modell,
rapporterar chi2 och parameterosäkerhet och avvisar tydliga revivals.

baseline jämför modellrecept med uppmätta optiska driftpunkter vid samma
temperaturer, kontroll och protokoll. Spinn-T2 validerar inte en full
nätverkskanal. Rapportens pass/fail gäller de angivna driftpunkterna.

discovery-steg kräver baseline_reproduction med pass-status, rapportens
sökväg och SHA-256. exploration är scenarioforskning före baslinjegaten.
Medföljande konfigurationer använder software_smoke.

Parameterbindning från katalogen finns i calibration.bind_observations
och pipeline. Bindningen behöver mängd, verifierad enhet, urvalsvillkor,
transform och uttrycklig modellmotivering. Se docs/DATA_SOURCES.md.

## Resultat och reproducerbarhet

Varje run-id bygger på konfiguration, backendversioner och källkodshash.
Jobbet får job.json, result.json, worker.log och vid framgång channels.json.
Seeds för spinnbad, parameterosäkerhet och nätverk separeras.
Osäkerhetsströmmen är reserverad; automatisk Monte Carlo över
parameterosäkerhet är inte implementerad. Deterministiska replikat
ger därför inte empiriska konfidensintervall.

Statusar: success, timeout, invalid_config, missing_data,
unsupported_physics, backend_unavailable, numerical_failure, runtime_error.
Gate-fail kan förekomma i en tekniskt lyckad körning.
Terminala jobb återanvänds; ändrad konfiguration får nytt id.
Undvik två samtidiga runnerprocesser mot samma output-mapp.

verification/ innehåller tester, miljöversioner, datahämtningens manifest,
kanaljämförelse och körsammanfattningar. scripts/verify_lab.py återskapar
verifieringen. Råfiler och den nya rådatakatalogen ingår inte i kodarkivet;
de återskapas med data-planen.

Ingen ny kandidat har visats slå SOTA och ingen experimentell
fullminnesbaslinje har reproducerats i denna leverans.

## Nästa grundforskningssteg

Granska art/laddning/isotop/nivåer, optisk koppling, T1/ren defasning,
kopplingstensorer, temperaturförlopp, skriv/läsbrus och retrieval.
Reproducera en experimentell baslinje och gör solver- och
parameterkonvergens innan resultaten används som materialprediktioner.

Läs docs/MODEL_CONTRACT.md och docs/DATA_SOURCES.md.
v0.3:s forskningsregister, negativa resultat och lab.py bevaras som
tidigare underlag. Deras äldre versionsbeskrivningar är historik.
