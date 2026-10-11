# Modeller, enheter och adaptrar i v0.4

Varje materialkandidat har ett eget id, familj, sammansättning, laddning, elektronspinn,
platsspecifika isotoper, geometri, värdmaterial och proveniens. Saknade egenskaper är
okända. Kandidatgenerering bevisar varken bindning, metastabilitet eller minnesfunktion.

Observationer och simulatorrecept är olika objekt. Ett simulatorrecept väljer en fysikmodell
och anger vilka observationer/beräkningar/antaganden som motiverar parametrarna. Resultatet
är en beräkning även när indata är experimentella.

## Familjer

| Familj | Implementerade lagringsbeskrivningar | Gräns |
|---|---|---|
| Atomensemble | Markovkanal; villkorsbunden koherenstabell | Effektiv skriv/läs-kanal måste anges; MaxwellBloch ger separat klassisk fältutbredning |
| Fångad atom/jon | Markovkanal; koherenstabell | Geometri/elektronik kan beräknas med PySCF; inga livstider härleds automatiskt |
| Sällsynt jordartsjon i fast material | Markovkanal; exakt litet spinnbad; PyCCE; koherenstabell | Värd, spinnnivåer, optisk protokollverkningsgrad och kopplingar måste specificeras |
| Spindefekt | Samma fyra lagringsbeskrivningar | Strukturspecifika hyperfintensorer krävs; modellens källor måste vara oberoende |
| Molekylspinn | Samma fyra lagringsbeskrivningar | Ett läkemedelsfragment eller NMR-spektrum är inte automatiskt ett kvantminne |
| Negativ jon | Markovkanal eller koherenstabell; fotodetachment med given miljööverlappning | Överlappningen är en inparameter; verktyget löser inte kontinuumelektronens vågfunktion |

Det är sex familjegrenar och flera återanvända fysikmodeller. Familjnamnet ändrar inte
Hamiltonianen magiskt. AFC/EIT/DLCZ, detaljerade optiska kaviteter, kvantprickar,
optomekaniska minnen och generella icke-Markovska process-tensorer är inte fullständigt
implementerade här.

## Lagring, temperatur och brus

Internt används sekunder, Hz, tesla, kelvin och ångström. Ett tensorfält har också
koordinatram. Hz och rad/s omvandlas med 2π. PyCCE får ms, kHz, G och rad/ms/G.
Ett isotopbyte identifierar atomplatsen; isotopmassan skapar inte en hyperfintensor.

Markovmodellen använder populationsrelaxation Γ1 och **ren** defasning Γφ.
För konstant temperatur är T2 = 1/(Γ1/2 + Γφ). Vid ändrad temperatur används angivna
temperaturmodeller och giltighetsintervall. Konstant koefficient över ett intervall
är ett uttryckligt modellantagande. En temperaturramp accepteras inte som en
kostnadsfri förändring: thermal_transition_s måste vara noll i denna version.
Olika fasta temperaturer under skrivning, lagring och läsning är tillåtna, men
övergångens genomförbarhet är inte validerad.

Exakt spinnbad:

- H0 = Hb + m0 A·I och H1 = Hb + m1 A·I i approximationen för ren centralspindefasning.
- Kärn-Zeeman, hyperfin-, kvadrupol- och angivna parvisa spinnkopplingar ingår.
- L(t) = Tr[U0 ρb U1†], med termisk badtäthet vid angiven lagringstemperatur.
- Ideala CPMG-pulser växlar grenarna. Logisk kontrollram återställs vid läsning.
- Dimensionen begränsas; större bad kräver CCE och en konvergensstudie.
- Tvärgående centralspinkopplingar och fononer måste modelleras separat.

PyCCE-adaptern stöder konventionell CCE för normaliserad ren koherens. gCCE kräver
en mer fullständig densitetsmatrisrekonstruktion och accepteras inte av denna adapter.
Öka klusterordning, badradie och konnektivitetsradie och jämför L(t) före materialslutsatser.
Badets standardisotopkonstanter kommer från PyCCE:s referenstabell; jämför dem med
granskade kärndata innan de används som experimentellt belägg.

Koherenstabeller behåller komplex fas och revivals. De måste börja med L(0)=1,
ha |L|≤1 och matcha temperatur och kontroll. Linjär interpolation används enbart
inom tabellen. En tabell som redan omfattar populationsrelaxation accepteras inte
som ett oberoende defasningsbidrag.

## Kanal och nätverk

Skriv- och läsdepolarisering, lagringskanal och tillståndsoberoende förlust sätts ihop.
Utkanalen är CPTP från en qubit till tre tillstånd: 0, 1 och erasure. Choi-matris och
Krausoperatorer exporteras. Villkorad genomsnittlig qubitfidelity, villkorad
entanglement fidelity och retrieval probability är separata mått.

Fidelity använder **kvadrerad** Uhlmann/Jozsa-konvention, inte QuTiP:s rotfidelity.
unconditional_target_overlap är framgångssannolikheten gånger den villkorade
genomsnittliga överlappningen. Vid noll retrieval är villkorad fidelity odefinierad
och rapporteras som null.

Nätverksadaptern erbjuder density matrices och heraldat förlustutfall. Två qubits
kan behandlas som en gemensam sammanflätad täthetsmatris. En ålderskanal appliceras
en gång på ursprungstillståndet. Inkrementell applicering av samma ålderskanal skulle
räkna brus två gånger och kan vara ogiltig vid revivals; API:t avvisar den operationen.

Den inbyggda tvånodsbenchmarken har oberoende länkattempts och fast lagringsålder.
Den har ingen repeaterkö, kapacitetskonflikt, routing eller dead-time-modell.
SeQUeNCe, NetSquid och WestQuant-Network behöver anropa detta API från sina
respektive händelsehanterare. Deras versionsspecifika klasser ingår inte i paketet.

## Externa beräkningar

PySCF beräknar vertikal HF/DFT-energi och valfri TDA vid given geometri. Cachen omfattar
geometri, laddning, 2S, recept och backendversion. Born–Oppenheimer-elektroniken beror
inte på isotopmassan vid samma kärngeometri. Isotopspinn och värdmiljö måste kopplas in
via sina egna modeller.

ORCA- och QE-adaptrarna skriver riktiga indatafiler och kör angiven lokal binär med
timeout. QE kräver cell, pseudopotentialer och k-punkter. PyCCE kan importera ORCA/QE:s
kopplingsdata; koordinatram och atomplatser behöver granskas efter import.
ORCA/QE-binärerna ingår inte och kördes inte i den här verifieringen.

PyCCE 1.1.1 använder två borttagna API-namn. Adaptern återställer NumPy:s unicode_
som str_ och SciPy:s flyttade isintlike. Det ändrar dtype-/indatakontroll, inte
Hamiltonianen. Denna kompatibilitet kontrolleras mot en exakt enspinnlösning.

MaxwellBloch ger klassisk puls-/fältutbredning i backendens egna normaliserade enheter.
En fysisk skalfaktor måste väljas för koppling till SI-enheter. Ingen qubitfidelity
eller kvantminnesverkningsgrad uppfinns från en klassisk fältkurva.
