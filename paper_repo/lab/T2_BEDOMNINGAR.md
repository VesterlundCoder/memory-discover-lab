# T₂ med referenstabeller och deterministisk fysik

ML är ett eget projekt, `westquant-t2-ml-project`. Minneslabbet har ingen
ML-träning eller materialregression i T₂-flödet.

## Kör hela flödet

Kör från projektets rot. För en ny installation:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c constraints-tested.txt -e '.[quantum,network]'
python -m memorylab.t2lab run --offline --sequence
```

Arkivet innehåller källcachen. `--offline` verifierar SHA-256 och förbjuder
hämtning. Utan flaggan används automatiska, versionslåsta HTTP-hämtningar.
Tillgång till källornas servrar krävs för en tom cache. GitHub-revisionen och
Zenodo-postens filer och kontrollsummor finns i `t2_data/source_lock.json`.

Valfria molekylstrukturer kräver `.[chemistry]` och:

```bash
python -m memorylab.t2lab prepare --root t2_data --structures
```

Strukturer ger inte automatiskt T₂. CIF-filer kan beskriva en kristall trots
att spinnmätningen gjordes i lösning. Strukturtolkning och atom-/isotopmappning
behöver granskas innan tensorer används i en fysisk modell.

## Databasen och tabellerna

`t2_data/t2.sqlite` utökar labbets befintliga SQLite-katalog med
`t2_references`. Tio primärgranskade referensvärden finns i
`data/t2_references.json` och den läsbara tabellen `data/t2_references.csv`.
De täcker Eu-151 i YSO, vanadiumkomplex och PL6-defekter i 4H-SiCOI.
Det är en starttabell, ingen fullständig inventering av material eller SOTA.

Definitionerna hålls isär: effektivt optiskt AFC-T₂, DD-beroende spin-T₂,
Hahn-T₂, Ramsey-T₂* och molekylärt fasminne Tₘ. Varje rad har källa,
lokalisering i artikeln, villkor, osäkerhetskonvention och kvarvarande luckor.
Granskningen gäller de rapporterade värdena; den ersätter inte rådatagranskning
eller en oberoende reproduktion av författarnas passning.

201 positiva poster från Molecular Qubit Dataset finns också i katalogen.
De förblir preliminära: original-CSV:n anger inte enhet, fält eller
mätprotokoll konsekvent. Kolumnnamnen antyder 10 och 80 K, men varje ursprunglig
mätpunkt måste fortfarande granskas. De används inte som fysiskt bestämda T₂.
De tio referensvärdena är separat granskade primärtextvärden; de innebär inte
att motsvarande CSV-rader vid andra temperaturer har verifierats.

```bash
python -m memorylab.t2lab database
python -m memorylab.t2lab assess examples/t2_reference_query.json
python -m memorylab.t2lab assess examples/t2_unknown_query.json
```

Uppslag matchar materialidentitet, exakt definition och alla rapporterade
villkor. Saknade eller avvikande frågevillkor ger ingen tillämpbar tid.
Villkor som källan inte anger kan inte verifieras. Även en träff lämnar
referensradens dokumenterade dataluckor öppna. Ingen interpolation görs mellan
temperaturer, laddningar, isotoper, värdmaterial eller pulssekvenser.

## Deterministiska beräkningar

```bash
python -m memorylab.t2lab calculate examples/t2_markov_calculation.json
python -m memorylab.t2lab calculate examples/t2_spin_bath_0pulse.json
python -m memorylab.t2lab calculate examples/t2_spin_bath_1pulse.json
```

Markovmodellen använder `1/T₂ = Γ₁/2 + Γφ`, där Γ₁ är populationsrelaxation
och Γφ är oberoende ren dephasing. Ett uppmätt totalt T₂ får inte återanvändas
som ren dephasing och sedan adderas till T₁. Relationens giltighet är begränsad
till denna brusmodell. Temperaturberoende måste specificeras för de angivna
hastigheterna; modellen extrapolerar det inte från kemisk formel.

Angivna parameterintervall utvärderas i fyra hörn för de två hastigheterna.
Resultatet är ett deterministiskt intervall under ett explicit antagande om
vilka parameterkombinationer som är möjliga. Det är inte ett statistiskt
konfidensintervall eller en utlovad procentuell prediktionsnoggrannhet.

Spinnbadet använder isotopernas spinn, Zeemanvektorer, hyperfintensorer,
eventuella kvadrupol- och partensorer och en angiven temperatur. Hamiltonianer
anges i Hz och utvecklingen innehåller faktorn 2π. Tensorerna måste ligga i
laboratorieramen. Kontrollpulserna är ideala CPMG-pulser. Modellen utelämnar
tvärgående elektronrelaxation, fononer, ospecificerad omgivning och optisk
överföring. Oberoende Markovbidrag kan adderas explicit en gång.

Utdata är komplex koherens, dess belopp och ett numeriskt intervall för den
första samplade 1/e-passagen. Återkomster visas. Om ingen passage finns inom
tidsfönstret rapporteras fönstret, inte ett oändligt uppmätt T₂. Mellanliggande
passager kan missas; gör en tätare grid innan ett numeriskt intervall används.
Ingen exponentiell tid tilldelas automatiskt ett oscillerande ändligt bad.

De medföljande nya beräkningsexemplen är uttryckligen hypotetiska
programkontroller, inte förutsägelser för de granskade referensmaterialen.
En okänd kombination kräver först granskad geometri, laddning, isotoper,
spinn-Hamiltonian och brusparametrar. Enbart isotopmassor och formel räcker inte.

## Experimentell negativ kontroll

Zenodo 21532904 hör till Rodríguez-Moldes/Appas et al., PRL 137, 120803 (2026),
DOI 10.1103/ftkb-pkvp. De öppna klassiska lagringseffektivitetskurvorna för
Pr³⁺:YSO vid 3 K prövas med exponentiell och sträckt exponentiell modell:
fyra kurvor gånger två modeller, åtta passningar.

RF-kurvorna har modulationer och avvisar de prövade enkla modellerna. Den
RF-fria korta kurvan ger inte en välbestämd tid inom mätfönstret. Detta är
negativa resultat för modellerna, inte bevis för att materialet saknar koherens.
Effektivitetens förlusttid konverteras inte till ett homogent spin-T₂ utan en
granskad fysikalisk koppling. G²-korrelation är inte qubitfidelity, och den
separata fotondatans tidsaxel har en dokumenterad olöst offset mot artikeltexten.

## Forskningskontrakt och verifiering

Fråga: Kan ett rapporterat koherensvärde användas vid de specificerade
lagringsvillkoren, eller kan koherensen beräknas från oberoende fysikparametrar?

* H1: En korrekt villkorsfråga återfinner rätt referens och definition; ändrad
  temperatur eller okänt material ger ingen ny T₂-prediktion.
* H2: Ett enda kärnspinn med enbart longitudinell koppling ger den analytiska
  fria koherensen `cos(π A t)` och full refokusering med en ideal Hahn-puls.
* H3: De klassiska Pr-kurvorna behöver mer fysik än de prövade rena
  exponentmodellerna. Modellspecifikationens förkastande redovisas.

Deterministiska kontroller har ingen slumpseed. Kontrollen med simulerade
binomialräkningar använder seed 20261010, 21 tider gånger fyra faser och 4000
försök per fas. Parametrisk bootstrap: 60 replikat för denna kontroll och 30
per experimentkurvemodell. Holdout håller samtliga faser vid en utvald tid
utanför passningen. Dessa är program-/modellkontroller, inte nya experiment.
De granskade tiderna och CSV-raderna är inte tio respektive 201 oberoende
experiment; flera hör till samma studie och provserie.

Körningen inkluderar tre deterministiska specifikationer, 202 spinnbadstidpunkter,
fyra parameterhörn och åtta experimentkurvepassningar. Nätverkskontrollen
använder ett uttryckligen hypotetiskt profilkort med separat skrivning,
lagring och avläsning, tre kanalåldrar, två noder och 2000 försök med seed
20261010. QuTiP kontrolleras mot den analytiska kanalen, och SeQUeNCe kör
sin faktiska händelsekärna. Ett T₂-värde ensamt exporteras aldrig som ett
experimentellt verifierat optiskt minne.

Gates: granskade enheter/definitioner och analytiska kontroller ska passera;
enkla experimentkurvemodeller kan underkännas; en okänd kandidats T₂ och
påståenden om bättre nätverksminne förblir obestämda utan ytterligare data.
Fidelity, verkningsgrad, läsbrus och temperatur vid skrivning/lagring/avläsning
behöver valideras tillsammans innan en kandidat bedöms bättre.

`t2_runs/deterministic/summary.json` och `t2_runs/tests_v06.log` visar de
utförda kontrollerna. Diagrammet i resultatrapporten visar fri utveckling och
ideal återfokusering; referenstabellen visar skillnaden mellan observabler.
Nästa steg är att granska fler primära mätserier och köra konvergenskontroller
för realistiska bathstorlekar, pulsbrister och temperaturberoende brus.
