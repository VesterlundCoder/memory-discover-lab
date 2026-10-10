# Den första experimentella baslinjen

Detta är en reproduktion av publicerade, bearbetade experimentdata och en
kalibrerad simulering. Det är ingen ny fysisk experimentreplikation.

Källa: Markus Teller, Susana Plascencia, Samuele Grandi och Hugues de
Riedmatten, *Quantum Storage of Qubits in an Array of Independently
Controllable Solid-State Quantum Memories*, Physical Review X 15, 031053
(2025), https://doi.org/10.1103/z6lc-qw2d.
Öppna experimentdata: https://doi.org/10.5281/zenodo.14929997, version v1,
CC BY 4.0. Attribution till upphovspersonerna gäller även de inkluderade
källfilerna. Huvudartikel, supplement, metadata, kontrollsummor och
ursprungliga CSV-filer ingår i `baselines/teller2025/cache`.

## Vad som faktiskt har reproducerats

90 tillståndsfideliteter används: sex ingångstillstånd i fem path-par och
sex tillstånd i tio time-bin-celler. Fideliteterna är överlapp
`<psi|rho_out|psi>`, utan bakgrundssubtraktion. De är betingade på
detektion. Proberna är svaga koherenta tillstånd på enfotonnivå, inte
idealiska Fock-tillstånd eller ett uppmätt lagrat Bell-par.

Medel över sex Pauli-egentillstånd reproducerar artikelns medelfideliteter.
Tolkningen som en Haar-medelfidelity för en enda kanal förutsätter en
linjär qubit-kanal och lämplig, i praktiken tillståndsoberoende
postselektion. Förluster och SPAM är inte separat identifierade av dessa
medelvärden. Kraus-modellen använder en isotrop kanal som en uttrycklig
modellhypotes: `E(rho)=(1-p)rho+p I/2`, `p=2(1-F_avg)`.
Andra kanaler kan ge exakt samma medelfidelity.

## Granskad driftpunkt som körs i simulatorerna

| Parameter | Värde | Källa och status |
|---|---:|---|
| Material | Pr3+:Y2SiO5 | Huvudartikel, avsnitt II |
| Minnespar | 5,6; path-kodning | Huvudartikel, figurer 2–5 |
| Kryostattemperatur | 3 K | Rapporterad temperatur; inte tre oberoende temperaturmätningar |
| Optisk övergång | 606 nm | Huvudartikel, nivåschema |
| AFC-rephasering | 10 µs | Huvudartikel, avsnitt II–III |
| Lagring i spintillstånd | 8 µs | Huvudartikel, avsnitt III |
| Total optisk in–ut-tid | 18 µs | Huvudartikel, avsnitt III |
| Detektionsfönster | 270 ns | Figur 3–5; inte lagringstiden |
| Medelfidelity | 0,9671968089 | `5_yaxis2_F.csv`, par 5,6 vid 270 ns |
| Fidelityosäkerhet | 0,0051670280 | Halva avståndet Fmax−Fmin; MC-standardavvikelse |
| AFC-effektivitet | 0,16 ± 0,01 | Supplement, tabell I; klassiskt ljus |
| Tvåvägs optisk överföring | 0,42 ± 0,02 | Supplement, tabell I; klassiskt ljus |
| Demultiplexande AOD | 0,50 ± 0,04 | Supplement, tabell I |
| Accepterad fotonandel | 0,42 | Huvudartikel; avrundat, osäkerhet saknas |
| T1, T2 | Ej identifierade | Ingen lagringstidsserie i de använda data |
| Isotopanalys av prov | Ej angiven | Ingen verifierad isotopanrikning antas |

Signalens effektiva acceptans sannolikhet blir
`0.16*0.42*0.50*0.42=0.014112`. Det är en härledd signalmodell som använder
klassiskt uppmätta delöverföringar. Den utesluter fiberkoppling, filter,
detektorer och eventuell analys-postselektion och är därför **inte** en
uppmätt fullständig nätverkseffektivitet. Den propagaterade osäkerheten
0,0015824 antar oberoende delöverföringsfel och en exakt accepterad
fotonandel. Den sista osäkerheten och kovarianserna är okända.
Nätverkets konfidensintervall omfattar Monte Carlo-variation, inte denna
parametrosäkerhet.

## Datagranskning och holdout

Figur 4:s medel över sex tillstånd återskapar figur 5 vid 270 ns till
flyttalsprecision. Figur 8a:s tillstånd återskapar figur 8b på samma sätt.
Den publicerade täthetsmatrisen i 3b överensstämmer också med figur 4:s
X-tillstånd. Dessa kontroller avser samma experimentdata och är
datakonsistenskontroller, inte oberoende experiment.

Time-bin-cellerna 1,3,5,7,9 används för kalibrering av en gemensam
betingad kanal. Cellerna 2,4,6,8,10 hålls undan. Det är ett test inom
samma dataset; gemensamma systematiska fel och kovarians saknas. En
passering inom tre kombinerade standardavvikelser certifierar därför
bara denna begränsade approximationsmodell. Path-modellen i nätverket
kalibreras separat på par 5,6; time-bin-testet validerar inte dess
fullständiga kanaltomografi.

En modell med ändlig puls och konstant opolariserad bakgrund kalibreras
på detektionsfönster upp till 600 ns och jämförs med minst 800 ns, för
tre path-par. Mellanområdet används inte. Fönstren bygger på överlappande
fotonräkningar, så jämförelsen är ingen oberoende statistisk validering.
En parameter hamnar på sin gräns i par 5,6. Parametrarna tolkas därför
inte som entydigt bestämda materialegenskaper. En modell med konstant
fidelity över detektionsfönstret körs också och dess misslyckande sparas.

Tre filproblem dokumenteras i `data_quality.json`:

- 8a-filens rubrik anger en annan ordning än data. Data har basis 0–5
  följt av cell 1–10. Det verifieras genom figur 8b.
- Fmin/Fmax för figur 5 nämner fem par i rubriken men innehåller tre rader.
  Parordningen verifieras genom figur 4.
- 3a:s metadata säger sekunder, men dess axel saknar rubrik och sträcker
  sig till 1183.278. Filen sparas och spärras för fysikalisk tidsinferens.

## Körningar och resultatfiler

```bash
python -m memorylab reproduce examples/teller2025_baseline.json --out baselines/teller2025
python -m memorylab reproduce examples/teller2025_baseline.json --out baselines/teller2025 --offline
python -m memorylab simulate baselines/teller2025/measured_point_profile.json --times 0.000018 --backend qutip --out runs/my_point.json
python -m memorylab sequence baselines/teller2025/network_device.json baselines/teller2025/network_device.json examples/teller2025_network_workload.json --seed 20261010 --out runs/my_sequence.json
PYTHONPATH=. python scripts/verify_lab.py --cross-backend --out verification_local
```

`simulate --times 0.001` och ändrad temperatur avvisas: modellen saknar
underlag där. Ingen exponentiell livslängd har antagits.

`examples/teller2025_baseline.json` anger datalås, manuell parameter-
transkription med källplatser, hypoteser, splits, seeds och körantal.
Analysen är retrospektiv; den är inte prospektivt förregistrerad.

Resultat i `baselines/teller2025/`:

- `experimental_reanalysis.json`: publicerade medel och källkonsistens.
- `spatial_holdout.json`: fem undanlagda time-bin-celler.
- `readout_window_noise_fit.json`: brusmodell och negativ kontrollmodell.
- `measured_point_profile.json`: ändlig, källförankrad driftpunkt.
- `channel_samples.json`, `qutip_channel_samples.json`: Kraus och Choi.
- `network_device.json`: återanvändbar nätverksadapter.
- `sequence_runs/`: fyra verkliga SeQUeNCe 1.2-körningar, 100 000 försök
  per seed, 400 000 totalt.
- `summary.json`: exakta resultat, versionsinformation och kontroller.
- `catalog.sqlite`, `observations.json`: observationer med enheter och proveniens.
- `discovery_gate.json`: tydlig spärr för nya materialrankningar.

SeQUeNCe-adaptern ändrar en nyckels kanal i hela den gemensamma
täthetsmatrisen, bevarar intrassling, modellerar signalbortfall explicit
och applicerar den absoluta ålderskanalen en gång. Heltalsklockan har
pikosekundsupplösning. Ingen extra standardminnesdekoherens läggs på.

Nätverkskörningen antar ett idealt initialt Bell-par, oberoende minnen,
en minnesplats per nod, ideal förlustflagga och 1 ms mellan försök. Den
använder SeQUeNCes händelsekärna och kvanttillståndshanterare, inte dess
hela routingstack. Nätverksfidelity är simulerad och är inte experimentets
uppmätta qubit-fidelity. Falska heralds från fluorescens, konvertering från
koherenta prober till verkliga enfotoninstrument, förberedelse och
verklig länkgenerering återstår att validera.

## Nästa gate för nya kombinationer

För att bedöma längre lagring måste nästa dataset mäta **fidelity och
utläsningssannolikhet vid samma lagringstider**, med temperatur, protokoll,
inputfotonstatistik, signal/brusräkningar, antal försök och postselektion.
En tidsserie av ren spinekoamplitud eller av detektionsfönstrets bredd
räcker inte. Temperaturvariationer måste mätas eller komma från en
separat validerad modell. En fullständig brus- och förlustinstrumentmodell
behövs innan realistiska nätverkshastigheter används för ranking.

De befintliga PySCF/PyCCE/Maxwell–Bloch-adaptrarna kan därefter bära
nya mikroskopiska hypoteser. Denna baslinje ger det mät- och
simulatorflöde som de måste jämföras med; den gör inte materialegenskaper
för okända kombinationer identifierbara på egen hand.
