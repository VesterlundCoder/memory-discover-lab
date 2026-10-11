# WestQuant Memory Discovery Lab — Discovery Screening v1

David Vesterlund · utkast 2026-10-11 · bygger på repo `VesterlundCoder/memory-discover-lab`
(main `2a9cc25`, `paper/final-validation-manuscript` `7647782`, `validation/protocol-convergence-crosssim` `9358173`)

Del A är planen (svenska). Del B är en självbärande kodningsprompt (engelska, eftersom kod, konfigurationer och paper är på engelska) att klistra in i en kodagent från repots rot.

---

# DEL A — PLAN

## A0. Syfte och vad screeningen får påstå

**Mål:** Gå igenom *alla* kandidater och kombinationer som projektets databaser innehåller och sålla fram en kort, rangordnad lista av kandidater som är värda fortsatt arbete för framtida kvantminnen, med en tydlig lista över vad som saknas för var och en.

**Screeningen är en triage, inte en upptäckt.** Systemets egna gates (`discovery_gate.json`, runnerns `discovery`-stage, `prediction_purpose: material_prediction`-certifikatet) säger att ingen kandidat får en materialprediktion utan granskade data, konvergens och oberoende fysikgranskning. Screeningen ska därför producera:

1. **Fysikaliskt motiverade övre gränser** (t.ex. kärnspinnbad-begränsad koherens) – inte "T2 för materialet".
2. **Evidensnivå per kandidat** (vad som är mätt, beräknat, antaget, saknas).
3. **Krav-kartor** för nätverksnytta ("om kandidaten ska slå Teller-baslinjen i två-nodsuppsättningen krävs η ≥ X och T2 ≥ Y") – inte påståenden om att den gör det.
4. **En retrospektiv kalibrering** mot mätta värden som avgör om rankingen alls är trovärdig. Om kalibreringen faller redovisas det som ett negativt resultat och rankingen märks "otillförlitlig".

Det gör resultatet publicerbart även om ingen kandidat blir en vinnare, i linje med systempappret.

## A1. Inventering — vad som finns i projektet

| # | Källa (i repot) | Innehåll | Licens/status | Roll i screeningen |
|---|---|---|---|---|
| S1 | MTD-group/Molecular_Qubit_Dataset @ `5263b1d` – `Relaxation_time_data_08_02_24.csv` | 123 rader, 201 positiva T1/T2-poster vid "10" och "80" K; formel, spinn, lösningsmedel, koncentration, artikel-URL | **Licens ej angiven** – cachas lokalt, ej i Git | Kandidatuniversum (molekyler) + kalibreringsmål |
| S2 | MTD `cifs_of_molecules.zip` (`include_structures=True` i `t2data.fetch_sources`) | Kristallstrukturer (CIF) per molekyl-nummer | Samma som S1 | **Geometri → kärnspinnbad** (huvudmotorn i Tier 2) |
| S3 | `lab/data/t2_references.csv` | 10 primärgranskade värden: 5 Eu:YSO (Ortu), 3 V(IV)-komplex (Lin), 2 SiC PL6 (Hu) | Granskade transkriptioner | Ankare/baslinjer; kalibrering |
| S4 | `data/experimental/teller2025/` | 90 fidelitetsvärden, operating point Pr:YSO | CC BY 4.0, bundlad | Nätverksbaslinje (att slå/jämföra mot) |
| S5 | `data/experimental/pr2026/` | Klassiska retrieval-kurvor + heraldade fotonarrayer | CC BY 4.0, bundlad | Negativ kontroll; brus/effektivitetsdata |
| S6 | Bradley 2022 (4TU, branch `experiment/bradley2022-nv0-ramsey`) | 24 13C/NV⁰-observabler | CC BY 4.0 | Defektfamiljens ankare |
| S7 | NV 2025 figshare 29092316 (`include_nv=True`) | NV-rådata | CC BY 4.0 | Valfri extra defektkalibrering |
| S8 | `examples/all_elements.json` | 118 element × laddning {−1,0,1,2,3} × 2S {0..3}, max 5000 | Inventering, ej bedömd | Kandidatuniversum (atomer/joner) |
| S9 | `examples/new_combinations.json` + generatorn | Laddning/spinn/isotop/värd-varianter | Mjukvarumall | Kombinationsmotor |
| S10 | CIAAW-abundanser, NIST-isotopmassor | Isotopabundanser, massor (`nuclear_spin_I: None`!) | Evaluerade referenser | Isotopvarianter; **kärnspinn I och γ saknas – måste läggas till** |
| S11 | Dryad `10.5061/dryad.v6wwpzh55` (molecular optical) | Optiska egenskaper för molekyler | Verifiera (CC0 antas) | Tier 4: optiskt gränssnitt |
| S12 | Zenodo 6828667 (Cr host matrix 2022) | Fig 3b/3d-data | Verifiera | Kalibrering/kontext för Cr-qubits |
| S13 | PubChem (CID 241, 702), BMRB bmse000001 | Geometri/NMR-exempel | Källspecifik | Endast mjukvarutest – ej minneskandidater |
| S14 | CMB-S4 Cryogenic_Material_Properties | Termisk ledningsförmåga | Verifiera | Termisk budget (Tier 5, sekundärt) |

**Kända luckor som inte fylls i tysthet:** kärnspinn I, gyromagnetiska kvoter och kvadrupolmoment (PyCCE har en egen tabell som måste jämföras mot granskad källa), NIST ASD-nivåer för atomer/joner, elektronaffiniteter för negativa joner, värd-CIF:er för Y₂SiO₅/diamant/SiC. Dessa hamnar i "Extension"-listan (A9) och kräver ditt godkännande eftersom de ligger utanför de databaser som redan finns i projektet.

## A2. Kandidatuniversum och kombinatorik

En kandidat är (som i FORSKNINGSPLAN): `species + isotope pattern + charge + spin + host/site + field + temperature + control protocol (+ optical interface)`.

| Familj | Bas | Kombinationsaxlar | Grovt antal (verifieras i Tier 0) | Djupaste möjliga tier med projektets data |
|---|---|---|---|---|
| Molekylspinn (S1/S2) | ~123 molekyler (antal med CIF fastställs) | isotopmönster ×6 (naturlig; perdeutererad; ¹³C-utarmad; ¹⁵N; deut.+¹³C-utarmad; deut.+¹³C+¹⁵N) × fält ×2 (0,35 T X-band; 1,2 T Q-band) × protokoll ×3 (Hahn, CPMG-2, CPMG-8) × miljö ×2 (ren kristall; frusen lösning när lösningsmedel anges) | ≈ 123 × 6 × 2 × 3 × 2 ≈ 8 900 profiler; × 20 badrealisationer ≈ 180 000 CCE-körningar | Tier 2–5 |
| Referensmaterial (S3, S6) | Eu:YSO, V(IV), SiC PL6, ¹³C/NV | Används som ankare, inte varieras utan värd-CIF | 4 system | Kalibrering + Tier 5 |
| Fångad atom/jon (S8) | 118 × 5 × 4 = 2 360 rå | Paritetsfilter (elektronantal vs 2S) ungefär halverar; isotoper med I>0 | ~1 200 efter paritet; × isotoper | **Tier 1 endast** (nivådata saknas) |
| Negativ jon | Delmängd av S8 med laddning −1 | Kräver komplext χ | – | **Blockerad** (redovisas som blockerad) |
| Sällsynta jordarter/defekter i nya värdar | – | Kräver värd-CIF | – | Extension X1 |

Talen ovan är tak. Den faktiska matrisen bestäms i Tier 0 och fryses i preregistreringen innan produktionskörning.

## A3. Screeningtrappan

```
Tier 0  Inventering & normalisering      (alla källor → en kandidattabell, evidens, licens, dubletter)
Tier 1  Regelbaserad fysikfiltrering     (alla ~10⁴ kombinationer, sekunder per post)
Tier 2  Kärnspinnbadsgräns via CCE       (molekyler med geometri; konvergenscertifikat)
G2    ── Retrospektiv kalibreringsgate mot mätta T2/Tm ──
Tier 3  T1-/fonongräns och temperatur    (rapporterade T1; inga ab initio-påståenden)
Tier 4  Optiskt gränssnitt               (Dryad + kända protokoll; annars "koherens-only")
Tier 5  Minneskanal & nätverkskrav       (topp-K; scenarioenveloper; SeQUeNCe + QuNetSim)
Tier 6  Pareto-ranking & kandidatdossierer
```

### Tier 0 — Inventering och normalisering
- Kör `datasets` med `data_plan_extended.json` plus `t2data.fetch_sources(include_structures=True, include_nv=True)`; frys `source_lock.json`.
- Bygg `screening/universe.sqlite` (ny tabell bredvid katalogen, samma immutabla ID-semantik) med en rad per baskandidat: familj, formel, laddning, 2S, värd/lösningsmedel, geometri-hash (CIF), källrad, evidensnivå, licens.
- Matcha MTD-rader ↔ CIF-filer (`(\d+)\.cif` ↔ `number`), räkna och logga omatchade.
- Enhetsgranskning av MTD-kolumner (`T1_10, T1_80, T2_10, T2_80`, enheter saknas i CSV): granska en **stratifierad delmängd** mot originalartiklarna och lägg in `reviewed_mapping` med `review_source`. Ogranskade rader förblir `source_unspecified` och får inte användas i kalibreringen.
- **Utdata:** `inventory_report.json` (antal per familj/källa, omatchade, licensstatus, luckor).

### Tier 1 — Regelbaserad fysikfiltrering (alla kombinationer)
Billiga, deterministiska kontroller, inga livstider:
- elektronantal/2S-paritet (finns i generatorn), Kramers/icke-Kramers;
- kärnspinnsinnehåll: antal och täthet av magnetiska kärnor per isotopmönster (kräver I/γ-tabell, S10 + granskad källa);
- förekomst av tunga atomer (spinn-bana-proxy: max Z), centralkärnans I (hyperfin/klockövergångspotential, endast som flagga);
- för atomer/joner: isotoper med I>0 och udda/jämn elektronstruktur → "hyperfin-klockqubit möjlig?" som flagga; i övrigt `missing_data: NIST ASD`.
- **Utdata:** `tier1_features.parquet` + flaggor; inget filtreras bort tyst – en kandidat som stoppas får status och orsak.

### Tier 2 — Kärnspinnbadsbegränsad koherens (huvudberäkningen)
Etablerad metod: CCE på bad byggda från struktur (jfr Kanai m.fl., PNAS 119, e2121808119 (2022), 12 000 värdmaterial; Canarie, Jahn & Stoll, JPCL 11, 3396 (2020), organiska radikaler – **verifiera referenserna innan de citeras**).
- **Bad:** CIF → superceller (ASE/PyCCE `BathCell`) → isotoper placeras slumpvis enligt isotopmönstret (20 realisationer). Punktdipol-hyperfin för kärnor utanför `r_exclusion`; kärnor inom `r_exclusion` (spinntäthetsområdet) antingen (a) uteslutna med flagga eller (b) DFT-hyperfin (Tier 2b, nedan).
- **Centralspinn:** S från MTD `spin` (granskad), g = 2,0023 isotropt **som uttryckligt antagande** (`assumption: free_electron_g`), position = metallatom eller radikalcentrum.
- **Frusen lösning:** när MTD anger lösningsmedel och mätningen är i lösning läggs ett lösningsmedelsbad till (slumpade protoner/deuteroner vid lösningsmedlets täthet, deklarerad modell). Kristall- och lösningsvillkor jämförs aldrig med varandra.
- **Konvergens per profil** (certifikatet från `9358173`): CCE-ordning (2→3), `r_bath`, `r_dipole`, antal realisationer, tidsgrid. En profil utan certifikat får status `unconverged`, inget värde.
- **Utdata per profil:** hela |L(t)|-kurvan, första samplade 1/e-korsning (som i pappret – inte ett exponentiellt T2), stretch-exponent som deskriptor, spridning över realisationer.
- **Tier 2b (GPU, valbar):** DFT-hyperfin för kärnor nära centralspinnet med gpu4pyscf på H100 för den delmängd där punktdipolfelet dominerar. Flagga tunga/öppna skal-komplex (V, Cu, Cr) som "metodosäkerhet hög".

### G2 — Retrospektiv kalibreringsgate (avgör om rankingen duger)
- Målvärden: MTD T2 vid låg temperatur (`T2_10`), **endast enhetsgranskade rader**, matchade på miljö (kristall/lösning) och fält där det går, plus de tre Lin V(IV)-referenserna (S3).
- **Förväntan:** CCE-gränsen ska vara ≥ uppmätt Tm (det är en övre gräns), och rangordningen ska korrelera.
- **Förregistrerade kriterier (fylls i och fryses före körning):** Spearman ρ ≥ ρ₀ (förslag 0,5) med 95 % bootstrap-CI vars nedre gräns > 0; andel brott mot övre gränsen (CCE < mätt/1,5) ≤ f₀ (förslag 10 %).
- **Holdout:** dela molekyler efter källartikel/scaffold; 30 % hålls ute med separat masterseed (`20261109`) och används en enda gång.
- **Utfall:** pass → produktion i `discovery`-stage med kalibreringsrapporten som `baseline_reproduction` (runnern kräver hash). Fail eller inconclusive → screeningen körs vidare i `exploration`-stage, rankingen märks otillförlitlig, och felmoderna analyseras (lösningsmedel, metylrotorer, elektron-elektron-bad, spektral diffusion).

### Tier 3 — T1- och temperaturgräns
- Använd rapporterade T1 (10/80 K) endast för granskade rader; `T2 ≤ 2T1` som tak **inom Markovmodellen** (pappret varnar för att använda det universellt).
- Ingen fonon-T1 från struktur (utanför projektets validerade modeller). Saknas T1: status `T1_unknown` och kandidaten kan bara rankas på kärnbadsgränsen.
- Rapportera "användbar koherens" = min(kärnbadsgräns, T1-gräns) med båda delarna synliga.

### Tier 4 — Optiskt gränssnitt
- Matcha molekyler mot Dryad-datan (S11): finns optisk övergång, linjebredd och spinnselektivitet?
- Klass A: dokumenterat optiskt spinngränssnitt; B: optisk övergång men ingen spinnselektiv avläsning; C: inget känt → **koherens-only-kandidat** (behålls, men får ingen nätverksexport utan uttryckligt `allow_hypothetical`).

### Tier 5 — Minneskanal och nätverkskrav (topp-K, K ≤ 30)
- Bygg memory recipes med lagringsmodellen `coherence_table` från Tier 2-kurvan (pure-coherence-tabellen: L(0)=1, |L|≤1, ingen extrapolation) + Markov-T1 från Tier 3.
- I/O är okänt → **tre scenarioenveloper** (pessimistisk/nominell/optimistisk η_w, η_r, depolarisering, brus) som explicit `hypothetical`. Teller-punkten (S4) och Bradley-fallet (S6) körs som ankare i samma arbetslast.
- Kör två-nodsarbetslasten i SeQUeNCe och QuNetSim (parade spår, som i pappret).
- **Huvudresultat är inversen:** minsta η_w·η_r och största tillåtna läsbrus för att nå F_B ≥ 0,90 och kvalitetskvalificerad takt ≥ Teller-baslinjen vid lagringsålder t ∈ {1, 10, 100 ms, 1 s}. Det svarar på "vad skulle krävas", inte "vad den gör".

### Tier 6 — Ranking och dossierer
- **Ingen enskild poäng.** Paretofront över (kärnbadsgräns vid fast protokoll, T1-tak, optisk klass, nätverkskrav, isotopkostnad/komplexitet, evidensnivå, metodosäkerhet).
- Robusthet: en kandidat räknas som "framträdande" bara om den ligger på eller nära fronten i alla tre I/O-scenarier och över badrealisationer, aldrig på bästa seed.
- **Dossier per finalist (≤ 15):** kurvor, konvergenscertifikat, antaganden, saknade data, vilket experiment som skulle avgöra (t.ex. "Hahn-Tm i deutererad kristall vid 0,35 T, 10 K"), närmaste mätta referens.

## A4. Beräkningsbudget (uppskattning – kalibreras i pilot P0)

| Del | Volym | Uppskattning | Resurs |
|---|---|---|---|
| Tier 0–1 | ~10⁴ poster | minuter | laptop |
| Tier 2 pilot P0 | 10 molekyler × 2 mönster × 1 fält × 3 protokoll × 5 realisationer + konvergenssvep | ~300–600 körningar | CPU, för att mäta s/körning |
| Tier 2 produktion | ≤ ~180 000 CCE-körningar (tak från A2) | om ~0,5–2 CPU-min/körning: ~1 500–6 000 CPU-h | HPC/CPU-noder; PyCCE med MPI |
| Tier 2b DFT-hyperfin | ~50–120 strukturer | grovt 1–10 GPU-h/struktur | **≤ 1 000 av de 5 000 H100-timmarna**; resten reserveras |
| Tier 5 | K ≤ 30 × 3 scenarier × 4 åldrar × 2 simulatorer × 8 seeds | ~6 000 arm-körningar | CPU |

Budgeten låses efter P0. Om P0 visar > 5 CPU-min per körning minskas matrisen (färre realisationer eller protokoll) **före** produktion, inte efter att resultat setts.

## A5. Preregistrering och reproducerbarhet
- `screening/PREREGISTRATION.md`: matris, trösklar (ρ₀, f₀, F_B-gräns, åldrar), seeds (pilot `20261011`, produktion `20261012`, holdout `20261109`), split, stoppregler, vilka figurer som görs. SHA-256 av filen skrivs in i varje körnings manifest. Ändringar efter frysning loggas som avvikelser.
- Allt körs från en **taggad release** (efter paper-fixarna), aldrig från ocommittade ändringar. Varje tier skriver `manifest.json` (käll-, konfigurations- och kodfingeravtryck, miljö, seeds) och `claim_map.json` som paper-skripten kan läsa.
- MTD-rådata och CIF:er committas inte (licens). Härledda tabeller publiceras först efter licensbedömning.

## A6. Stoppregler och risker
| Risk | Konsekvens | Åtgärd |
|---|---|---|
| G2 faller | Rankingen otillförlitlig | Redovisa negativt; analysera felmoder; ingen "upptäckt" |
| Lösningsmedelsbad dominerar | Molekylvarianterna skiljer sig knappt | Rapportera; prioritera kristall-/deutereringsaxeln |
| Metylrotorer/elektronbad saknas i modellen | Systematisk överskattning | Flagga per molekyl (räkna CH₃-grupper, koncentration) |
| Punktdipolfel nära centrum | Fel nära-fält | Tier 2b eller uteslutningsradie med flagga |
| PyCCE-isotopkonstanter ogranskade | Fel γ/Q | Jämför mot granskad tabell innan produktion (S10-luckan) |
| Licens på MTD oklar | Kan inte publicera härledd data | Kontakta MTD-gruppen; publicera aggregat/kod |
| Kombinatorisk explosion | Budget sprängs | Tak i A2, låst efter P0 |

## A7. Milstolpar (förslag)
| Vecka | Milstolpe | Gate |
|---|---|---|
| 1 | Tier 0 inventering, enhetsgranskning av stratifierad MTD-delmängd | inventory_report klar |
| 2 | Tier 1 för alla; I/γ-tabell granskad; P0-pilot CCE | P0-tidsmätning, budget låst |
| 3 | Preregistrering fryst; kalibreringskörning (G2) | **G2 pass/fail** |
| 4–5 | Tier 2 produktion (+2b) | konvergenscertifikat ≥ 95 % av profilerna |
| 6 | Tier 3–4 | – |
| 7 | Tier 5 nätverkskrav för topp-K | parade simulatorer överens |
| 8 | Tier 6 Pareto, dossierer, rapport | intern granskning |

## A8. Leverabler
1. `screening/results/` – alla kurvor, certifikat, manifest, claim maps.
2. **Kandidatlista + dossierer** (≤ 15 finalister) med "saknas för att avgöra"-checklistor.
3. **Kalibreringsrapporten (G2)** – kan i sig bli ett kort paper ("Hur väl förutsäger strukturbaserad CCE uppmätta Tm i molekylqubit-databasen?").
4. Underlag till ett andra paper ("Discovery screening with evidence tiers") och till separata ML-T2-projektet (kurvor och features exporteras, men ingen ML-träning görs här).
5. Experimentförslag till samarbetspartner (t.ex. Bristol-kontexten) för de 2–3 starkaste.

## A9. Extensions (utanför nuvarande databaser – kräver ditt beslut)
- **X1** Värd-CIF:er (COD, CC0) för Y₂SiO₅, YVO₄, CaWO₄, diamant, 4H-SiC, Si → Kanai-liknande värd × isotoprenhets-screening för RE/defekter.
- **X2** NIST ASD-nivåer → Tier 2 för atomer/joner (hyperfina klockövergångar, magnetisk känslighet).
- **X3** Elektronaffiniteter (NIST WebBook) → avblockerar negativa joner till Tier 1.
- **X4** Granskad kärndatatabell (I, γ, Q) från IAEA/NUBASE → ersätter beroendet av PyCCE:s inbyggda tabell.

Siffrorna för tid och kostnad i planen är uppskattningar. Piloten ska ersätta dem innan något låses. Prompten utgår från att du kör från en taggad release efter paper-fixarna, och ber om taggen om den saknas. Referenserna Kanai m.fl. (PNAS 2022) och Canarie/Jahn/Stoll (JPCL 2020) är markerade "verifiera innan citering".

---

# DEL B — KODNINGSPROMPT

> Paste everything below into the coding agent from the repository root.

---

## Context

You are working in `VesterlundCoder/memory-discover-lab`, the WestQuant Memory Discovery Lab (Python package `lab/memorylab`). Read these before writing code: `README.md`, `lab/README.md`, `lab/FORSKNINGSPLAN.md`, `lab/docs/MODEL_CONTRACT.md`, `lab/docs/EXTENDING.md`, `lab/docs/DATA_SOURCES.md`, `DATA_SOURCES.md`, `paper.tex` (sections 2–4 and the extended-validation section). Also read the modules `catalog.py`, `importers.py`, `datasets.py`, `t2data.py`, `t2assessment.py`, `models.py`, `spin.py`, `backends.py` (`pycce_coherence`), `runner.py`, `network.py`, `sequence_adapter.py`, and the convergence-certificate and QuNetSim code introduced on branch `validation/protocol-convergence-crosssim` (`9358173`).

**Base:** Branch from the latest tagged release `<RELEASE_TAG>` (ask me for it if it does not exist; do not branch from a commit with uncommitted changes). Create branch `screening/discovery-v1`.

## Goal

Build and run **Discovery Screening v1**: an evidence-tiered triage of *every* candidate and combination available from the project's existing data sources, to shortlist possible future quantum-memory candidates. The screening produces bounded physical estimates, evidence levels, missing-data checklists and network-requirement maps. It must not produce material predictions unless the existing gates allow it.

## Non-negotiable rules

1. **Do not modify or bypass production guards** (`models.validate`, runner stage checks, reference-query restrictions, coherence-table checks, the `material_prediction` certificate requirement, source-hash checks). New code calls them; it never patches them.
2. **No T2 from formulas, isotope masses, fingerprints or ML.** The only lifetimes are (a) reviewed observations and (b) outputs of declared physical models with convergence certificates, labelled `computed` and scoped as *nuclear-spin-bath-limited coherence bound* (or similar).
3. **Every record carries** `evidence_kind`, provenance (artifact SHA-256), the conditions, explicit assumptions (`assumptions: [...]`) and a `status` from: `success`, `unconverged`, `missing_data`, `unsupported_physics`, `blocked`, `numerical_failure`, `timeout`, `invalid_config`. Nothing is dropped silently; a filtered candidate keeps its row with a reason.
4. **Report the first sampled 1/e crossing with its bracket, the curve and the window**, never "T2 = x" for a non-exponential curve. No crossing in the window means "no crossing in the window", not infinity.
5. **Licensing:** MTD CSV and CIFs (`license: not_verified`) are cached under an ignored path and never committed. Derived per-molecule tables stay in `screening/results/private/` (git-ignored) until I approve publication; aggregate statistics may be committed.
6. **Seeds:** pilot `20261011`, production `20261012`, holdout `20261109`. Derive streams with the existing `common.seed(master, identity, stream, replicate)`. Holdout data is touched exactly once, by the G2 script, after preregistration is frozen.
7. **Stop and ask me** at each gate marked ⛔ below. Do not continue past a failed gate on your own.
8. Write tests alongside each module (pytest, under `lab/tests/screening/`). Each phase must leave `make test` green.
9. Do not add data sources beyond those listed in Phase 0 without asking me (see "Extensions").

## Package layout to create

```
lab/memorylab/screening/
__init__.py
inventory.py        # Phase 0: source sync, universe table, CIF matching, unit-review hooks
nucdata.py          # nuclear spin I, gamma, Q table + cross-check vs PyCCE's table
universe.py         # combination enumeration (isotope patterns, fields, protocols, environments)
tier1.py            # rule-based features/flags
bath.py             # CIF -> supercell -> isotope realisations -> PyCCE bath; solvent bath model
tier2_cce.py        # CCE runs + convergence certificate per profile
tier2b_dft.py       # optional gpu4pyscf hyperfine for near nuclei (feature-flagged)
calibration.py      # G2 retrospective calibration (rank correlation, bound violations, holdout)
tier3.py            # T1/temperature bounds from reviewed observations
tier4.py            # optical-interface matching (Dryad), classes A/B/C
tier5_network.py    # recipes, I/O envelopes, paired SeQUeNCe/QuNetSim, inverse requirement maps
rank.py             # Pareto fronts, robustness across scenarios/realisations
report.py           # dossiers, figures, claim maps, manifests
screening/
PREREGISTRATION.md  # frozen before production (hash recorded in every manifest)
configs/*.json      # one config per phase; every number used in a run lives here
results/            # committed: aggregates, manifests, claim maps
results/private/    # git-ignored: per-molecule outputs derived from unlicensed data
```

CLI: add the subcommand `python -m memorylab screen <phase> --config screening/configs/<phase>.json --out screening/results/<phase>` with phases `inventory | tier1 | pilot | calibrate | tier2 | tier2b | tier3 | tier4 | tier5 | rank | report`. Reuse `runner.py` for job enumeration, checkpointing, timeouts and resume (add a new `task` type `coherence_bound`, not a fork of the runner). Respect `resources.max_workers/timeout_s/max_runs`.

## Phase 0 — Inventory (`screen inventory`)

- Sync sources: `examples/data_plan_extended.json` via `datasets.synchronize`, and `t2data.fetch_sources(include_structures=True, include_nv=True)`. Freeze `source_lock.json`. Also load the bundled `data/experimental/*`, `lab/data/t2_references.csv` and the Bradley data from the release.
- Build `screening/results/private/universe.sqlite` (immutable IDs, same semantics as `catalog.py`) with one row per base candidate and family: molecular (MTD rows), reference systems (10 references + Teller + Bradley), atoms/ions (`examples/all_elements.json` expanded with the generator), and generator combinations (`examples/new_combinations.json`).
- Match MTD rows to CIFs (`<number>.cif`). Parse with ASE; record the formula match between CIF and `chemForm` (counterions and solvent molecules separately). Unmatched or mismatched rows get `status: missing_data` and a reason.
- **Unit review hook:** produce `unit_review_queue.csv`, a stratified sample (by source paper, metal, solvent class) of MTD rows with the original-paper URL. ⛔ *Stop and let me review units and conditions.* Reviewed rows enter via `importers.molecular_csv` `mapping.columns` with `review_source`. Only reviewed rows may be used in calibration.
- Output `inventory_report.json`: counts per family/source, CIF match rate, licence status, the list of data gaps (I/γ/Q, NIST ASD, electron affinities, host CIFs).

**Acceptance:** report generated; counts reconcile with the source files; tests cover CIF↔row matching and the schema-change guard.

## Phase 0b — Nuclear data (`nucdata.py`)

- Build a nuclear table (isotope → I, γ in rad s⁻¹ T⁻¹, Q in barn, natural abundance from CIAAW S10) **from a single cited reviewed source that I approve** (propose IAEA/NUBASE or NIST; ⛔ ask before fetching). Cross-check against PyCCE's built-in table; write `nucdata_crosscheck.json` listing all discrepancies above 0.1 %. PyCCE runs must be fed the reviewed values (override PyCCE's defaults explicitly).

## Phase 1 — Tier 1 features (`screen tier1`)

For every universe row and combination:
- electron-count/2S parity (reuse the generator's check), Kramers flag;
- per isotope pattern: magnetic-nucleus count and density within 10/20/30 Å (from CIF), ¹H/²H/¹³C/¹⁴N/¹⁵N fractions, methyl-group count (CH₃ rotor flag), max Z (spin–orbit proxy flag), central-nucleus I;
- atoms/ions: I>0 isotopes, hyperfine-qubit-possible flag; everything else `missing_data: atomic_levels (NIST ASD not in project)`; negative ions `blocked: electron_record_overlap_chi_unavailable`.

Isotope patterns (molecules): `natural`, `perdeuterated`, `C13_depleted_99.99`, `N15`, `deut+C13dep`, `deut+C13dep+N15`. Mark every pattern except `natural` as `evidence_kind: hypothetical` (synthetic chemistry not verified).

**Acceptance:** `tier1_features.parquet` covers 100 % of rows; tests for parity, density counting on a small hand-made CIF, and methyl detection.

## Phase 2 — Pilot (`screen pilot`)

- 10 molecules (stratified across metals/radicals and with reviewed T2 values), 2 isotope patterns, field 0.35 T, protocols Hahn/CPMG-2/CPMG-8, 5 realisations, plus convergence sweeps: CCE order 2→3, `r_bath` {20, 30, 40} Å, `r_dipole` {6, 8, 10} Å, realisations {5, 10, 20}, and time-grid doubling.
- **Bath construction (`bath.py`):** supercell from CIF large enough for `r_bath`; place isotopes per pattern with the bath seed stream; point-dipole hyperfine (record `assumption: point_dipole`) for nuclei beyond `r_exclusion` (default 3 Å; configurable); nuclei inside are excluded with flag `near_nuclei_excluded:N` unless Tier 2b supplies tensors. Central spin: S from reviewed `spin`, `g=2.0023` isotropic (`assumption: free_electron_g`), position at the metal atom or the radical-centre atom declared in config.
- **Solvent bath:** if the reviewed measurement condition is frozen solution, add a solvent nuclear bath (random positions at the solvent's number density, isotope pattern applied, exclusion around the molecule). Keep crystal and solution profiles separate in IDs and never compare them.
- Use the existing `backends.pycce_coherence` contract (conventional CCE, normalised pure coherence, unit conversions) or extend it in a backward-compatible way that accepts a prebuilt `BathArray`. The existing nonphysical-coherence check stays.
- Validate the bath builder against the exact solver (`spin.exact_coherence`) on ≤ 8-spin sub-baths, reusing the extended-validation convergence code.
- Measure the CPU time per run, the memory per run and the failure rates. Output `pilot_budget.json` with a projected production cost for the full matrix.

⛔ **Stop:** show me `pilot_budget.json` and the convergence results. I will lock the production matrix and the convergence tolerances in `PREREGISTRATION.md`.

## Phase 3 — Preregistration freeze

Generate `screening/PREREGISTRATION.md` from a template containing: the final matrix; convergence tolerances; G2 criteria (Spearman ρ₀, the bound-violation fraction f₀ with the violation definition CCE_bound < measured/1.5, a bootstrap of 2,000 resamples, and a split by source paper with 30 % holdout); Tier-5 thresholds (F_B ≥ 0.90; ages 1 ms, 10 ms, 100 ms, 1 s; the three I/O envelopes); seeds; figures; stop rules. Write the SHA-256 to `screening/PREREGISTRATION.sha256`. Every later manifest records it, and a mismatch aborts the run.

## Phase 4 — Calibration gate G2 (`screen calibrate`)

- Run Tier-2 CCE on all molecules with reviewed low-temperature T2 (the calibration set), matching the environment (crystal/solution) and the field where reported (else 0.35 T, flagged), with the protocol matched to the reported measurement (Hahn by default).
- Compute: Spearman ρ with a bootstrap CI between the CCE bound (first 1/e crossing midpoint) and the measured T2; the bound-violation fraction; the per-molecule log-ratio; and the failure-mode tags (methyl count, concentration, solvent, heavy atom, excluded near nuclei).
- Then evaluate the holdout **once** with the holdout seed.
- Output `calibration_report.json` with `status: pass|fail|inconclusive`, using the preregistered rule. If it passes, write it in the format the runner's `baseline_reproduction` gate expects (path + SHA-256) so the production runs can use stage `discovery`. Otherwise production uses stage `exploration` and every downstream output carries `ranking_reliability: unvalidated`.

⛔ **Stop and show me the report** before production.

## Phase 5 — Tier 2 production (`screen tier2`, optional `screen tier2b`)

- Run the locked matrix through `runner.py` with checkpoint/resume and resource bounds. Each profile needs a passing convergence certificate (the five refinement axes from `9358173`) to get `status: success`; otherwise `unconverged`.
- Per profile, store: the complex L(t) over realisations (mean, 16–84 % band), the first-crossing bracket, a stretched-exponent descriptor (fit only as a descriptor), the certificate and the assumptions.
- **Tier 2b (feature flag `dft_hyperfine: true`):** for structures where the excluded near nuclei change the bound by more than the tolerance in a sensitivity test (exclusion radius 2 vs 4 Å), compute hyperfine tensors with gpu4pyscf (functional, basis and relativistic treatment in config; recipe hash in the cache identity; convergence checked), map the tensors to the lab frame with explicit site mapping, and rerun. Flag open-shell transition-metal complexes `method_uncertainty: high`. Budget cap: the GPU hours in config (default 1,000 H100 h); stop when reached.

## Phase 6 — Tiers 3 and 4

- **Tier 3:** reviewed T1 at 10/80 K gives a Markov-scoped cap `2*T1` (`assumption: markov_T2_le_2T1`); report `usable_bound = min(bath_bound, T1_cap)` with both components. No phonon modelling. Missing T1 gives `T1_unknown`.
- **Tier 4:** match against the Dryad optical dataset (verify its licence first; ⛔ ask if it is not CC0/CC BY). Classes: A = optical spin interface documented; B = optical transition but no spin-selective readout; C = none known (coherence-only, no network export without `allow_hypothetical`).

## Phase 7 — Tier 5 network requirement maps (`screen tier5`)

- Select the top K ≤ 30 by the Tier-2/3 Pareto front (see Phase 8), plus the anchors (Teller operating point, Bradley effective model).
- Build memory recipes with storage model `coherence_table` from the Tier-2 curve (it must satisfy L(0)=1, |L|≤1, no extrapolation, pure dephasing only) composed with Markov T1, with `additional_dephasing_independent_of_markov: true` declared and justified in the provenance.
- I/O envelopes (all `hypothetical`): pessimistic/nominal/optimistic η_w, η_r, write/read depolarisation and background rate from config. Use the readout-background instrument (Eq. 14 in the paper).
- Run the paired two-node workload in SeQUeNCe and QuNetSim (existing adapters, shared logical traces and seeds; check that the paired outputs agree, as in the paper).
- **Inverse maps:** for each candidate and age, bisect the minimum η_w·η_r and the maximum read depolarisation that give F_B ≥ 0.90 *and* a quality-qualified rate ≥ the Teller anchor under the same workload. Output tables and heatmaps. Label all of it "requirement map under hypothetical I/O", never as a performance claim.

## Phase 8 — Ranking and dossiers (`screen rank`, `screen report`)

- Pareto fronts over: the usable bound at a fixed protocol and field; the optical class; the network requirement (lower is better); the isotope-pattern complexity; the evidence level; the method uncertainty. Robustness: a candidate is "prominent" only if it is non-dominated or within ε of the front in all three I/O envelopes and in ≥ 80 % of bath-realisation bootstrap resamples.
- Write a dossier (markdown + figures) for ≤ 15 finalists: curves, certificate, assumptions, missing-data checklist, the nearest measured reference, and the single most decisive experiment (protocol, field, temperature, isotope pattern).
- Write `screening/results/claim_map.json` (claim → source result file → SHA-256) for later paper use, a `manifest.json` per phase, and a summary `SCREENING_REPORT.md` that leads with the G2 outcome and states the evidence boundaries.

## Figures (matplotlib, from stored results only)

F1 inventory and tier funnel (counts with reasons); F2 G2 calibration scatter (log scale, bound line, holdout highlighted); F3 L(t) bands for the finalists per isotope pattern; F4 isotope-pattern ablation (ratio vs natural); F5 Pareto front with the evidence level encoded by marker; F6 network requirement heatmaps (η needed vs age) with the anchors.

## Definition of done

- All phases run from a clean clone of the tagged base with `--offline` after Phase 0 sync, and are reproducible from the manifests (rerun → identical scientific payload at 1e-10, excluding timings).
- Tests green; new code covered for bath building, isotope placement, certificate enforcement, G2 split/holdout isolation, recipe validity, the inverse search and the Pareto logic.
- No production guard modified (`git diff` on the guard modules shows additions only, or none).
- `SCREENING_REPORT.md` states the G2 outcome first, lists blocked/missing families explicitly, and contains no statements of new-material performance.

## Extensions — do NOT start without my explicit approval

X1 host CIFs (COD) for Y₂SiO₅/YVO₄/CaWO₄/diamond/4H-SiC/Si → host × isotope-purity screening for rare-earth and defect spins; X2 NIST ASD levels for atoms/ions; X3 electron affinities for negative ions; X4 replace the nuclear table source if Phase 0b reveals problems.

Start with Phase 0. Before writing code, give me a short implementation plan for Phase 0 and Phase 0b with the files you will touch.
