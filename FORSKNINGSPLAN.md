# Ett simuleringslabb för att upptäcka bättre optiskt åtkomliga kvantminnen

Datum: 2026-10-09. Litteratursökning gjord detta datum. Planen gäller fysisk materialdesign
och användning i kvantnätverk. Den förutsätter inte att ett bättre material kommer hittas.

## 1. Forskningsfråga och rätt analysenhet

Kan en kombination av isotop, laddningstillstånd, kemisk struktur/värdmaterial och
kontrollprotokoll förbättra den användbara lagringen av fotoniska qubits vid jämförbara
driftvillkor och resurskostnader?

En kandidat är inte ett grundämne. Den är:
`species + isotope + charge + electronic/nuclear encoding + host/site + temperature
+ magnetic field + optical cavity/interface + control protocol`.

Målet är att förbättra användbara minnen för kvantnätverk jämfört med relevanta
demonstrerade skriv–lagra–läs-system under jämförbara temperatur- och driftkrav.
Timslång isolerad spinnkoherens definierar inte ensam denna SOTA. Använd Paretofront för T2, fidelity,
skriv/läseffektivitet, bandbredd, moder och driftkostnad. Jämför samma kvanttillstånd,
lagringstid och kontrollbudget. Skilj Ramsey T2*, Hahn-echo T2, DD-T2 och optisk T2.

## 2. Laddningshypotesen

En bunden optisk excitation ändrar inte laddningen. Neutralisering av en negativ jon
innebär fotodetachment:

\[ A^-+\hbar\omega\to A+e^- .\]

Den fria elektronens energi, spinn och rörelsemängd kan bära information om den inkommande
qubiten. Räkna därför det gemensamma sluttilståndet och spåra ut elektron/miljö.
En neutral atom med lång livstid är otillräcklig om den reducerade minneskanalen redan
förlorat koherensen. Neutralisering innebär dessutom att en elektrisk jonfälla inte längre
håller partikeln på samma sätt; modellera kvarhållning och återinfångning.

En mer förankrad variant är att först mappa information till kärnspinnet och därefter ändra
laddningen för att reducera elektroninducerat brus. Återställ sedan optisk åtkomst vid
läsning. Båda laddningsövergångarnas koherensfel och stokastiska timing måste räknas in.
Laddning i en kristalldefekt/donator är inte identisk med laddning hos en fri atom.

## 3. Närmaste forskning och baslinjer

| Arbete | Visat resultat | Vad det inte etablerar |
|---|---|---|
| Wang et al., PRX Quantum 6, 010302 (2025) | Eu3+:YSO-kärnspinn: över 13 h koherens vid 125 mK och över 18 h i spektralt utvalt subensemble; 6 h vid 6 K | Komplett fotoniskt minne med motsvarande fidelity och effektivitet |
| Ma et al., Nature Communications 12, 2381 (2021) | Koherent ljuslagring en timme med AFC, ZEFOZ och DD | En timmes generell enkel-foton-processfidelity; försöket använder ljuspulser och interferens |
| Saeedi et al., Science 342, 830 (2013) | Joniserade 31P-donatorer i 28Si: 39 min kärnspinnskoherens vid rumstemperatur med DD | Rumstempererad skrivning/läsning av nätverksfotoner; dessa steg använder kyla |
| Nature Materials, DOI 10.1038/s41563-026-02539-0 (2026) | Optisk avläsning av koherent kontrollerade kärnspinn i Eu-baserad molekylkristall | Färdigt högpresterande nätverksminne |
| Roggors et al., arXiv:2605.10077 (2026), preprint | Enskild karbenmolekyl med spinn–foton-gränssnitt; DD-koherens på millisekundskala vid 4.5 K | Timslång spinnkoherens; optisk spektral stabilitet är ett annat mått |
| Nature Communications, DOI 10.1038/s41467-026-77060-8 (2026) | Kavitetförstärkt optisk kontroll och avläsning av 167Er-kärnspinn i YSO, telecomkompatibelt | Universell överlägsenhet över andra minnen |
| Walter et al., PRL 113, 063001 (2014) | Bundna optiska övergångar i La− | Demonstrerat kvantminne eller bevisad koherent neutraliseringscykel |

Detta är en riktad litteraturgenomgång, inte ett fullständigt aktuellt rekordregister.
Ingen kandidat får deklareras global rekordhållare utan en utvidgad och jämförbar genomgång.

## 4. Labbets fem fysiknivåer

1. **Evidensregister.** Börja med 118 element och fem laddningar som granskningsposter.
   Importera atomnivåer, övergångsstyrkor och jonisationsenergier från NIST ASD; negativ
   jonbindning från specialiserad litteratur/NIST-referenser och elektronaffiniteter från
   WebBook. Dokumentera täckningsluckor. Isotoper, molekylgeometri, värdmaterial och
   laddningsstabilitet måste läggas till före kandidatbedömning. ”Saknas” betyder okänt.
2. **Elektronstruktur.** Lätta atomer/molekyler: PySCF med lämplig korrelerad metod.
   Anjoner kräver diffusa basfunktioner och explicit kontroll av bindning mot kontinuum.
   Tunga/open-shell-system kräver relativistiska och ofta multireferensmetoder med
   specialistgranskning. Beräkna nivåer, övergångsdipoler, hyperfin- och g-tensorer,
   spinn–ban-koppling, laddningströsklar och fältderivator. Använd oberoende metod i finalisterna.
   Vanlig DFT-energi eller optisk livstid får inte omvandlas direkt till T2.
3. **Miljö och koherens.** Specificera kärnspinnbad, isotoprenhet, paramagnetiska föroreningar,
   fononer, strain, laddningsfluktuationer, magnetiskt/elektriskt brus, temperatur och
   pulsfel. PyCCE är ett relevant verktyg för spinnbad; fononer och tekniskt brus kräver
   ytterligare modeller. Jämför Ramsey, Hahn och DD, med realistisk effekt- och värmebudget.
   CCE-klusterordning och badradie ska konvergeras. Exportera hela koherenskurvan.
4. **Skriv–lagra–läs.** Modellera signal- och kontrollfält, nivåstruktur, spontan emission,
   läckage, detachment, kavitet och vågpaket med öppensystemdynamik. Specificera fotonens
   encoding; pilot använder time-bin med angiven pulsbredd. Räkna komplett kanal inklusive
   förlust. Testa sex qubittillstånd och Bell-par med orörd referens. Jämför en realistisk
   classical measure-and-prepare-baseline med samma inputfördelning och postselektion;
   2/3 är endast standardgränsen för uniforma deterministiska en-qubit-fall.
5. **Nätverk.** Exportera tidsberoende kanal, erasure, wavelength, bandbredd, kapacitet,
   kontroll-/resetlatens och osäkerhet. SeQUeNCe/NetSquid behöver egna testade adaptrar.
   Mappa inte amplitude damping till en Werner-depolariseringsmodell utan approximationstest.
   Mät levererade par/s över fidelitytröskel, väntetider och minnesbelastning med samma
   arbetslaster, eventordning, ljusförlust och heraldinglatens.

## 5. Hypoteser och tillåten evidens

| ID | Testbart påstående | Falsifiering/begränsning |
|---|---|---|
| H1 laddning | Full skriv–laddningsbyte–lagring–återställning–läsning förbättrar genomsnittlig processfidelity med minst 0.01 vid en förutbestämd lagringstid jämfört med samma system utan laddningsbyte | Övre 95%-gräns under 0.01: nyttokrav fail; förlorad koherens eller låg återhämtningssannolikhet kan förklara utfallet |
| H2 miljö | En specificerad värd/isotopvariant ger minst 2× koherenstid och högst 0.01 sämre komplett fidelity vid samma driftvillkor | Båda kraven måste styrkas; DD-budget och subensembleurval räknas som resurser |
| H3 system | Ny profil ger minst 20% högre goodput vid end-to-end Bell-fidelity ≥0.90 och matchad kapacitet/kostnadsram | Övre CI under 20%: nyttokrav fail; bättre T2 räcker inte |

Trösklarna är provisoriska ingenjörsmål, inte kända experimentresultat. Frys dem efter
piloten och före konfirmatoriska testdata. Nedre CI över krav = pass; övre CI under krav =
fail; annars inconclusive. För non-inferiority i H2 krävs separat övre gräns för fidelityförlust.
H1–H3 är skilda evidensnivåer. Materialberäkning bevisar inte hårdvarufunktion.
En absolut rekordhypotes kräver ny litteraturbenchmark och fysisk verifiering.

## 6. Etapper, exakt körbudget och beslut

**E0 — kärnvalidering, vecka 1–2.** Kör de nio kodtesterna. Verifiera atomenergi/nivåer mot
litteratur för H/He och en relevant multilevel-baslinje innan bred screening. Kontrollera
Hermitesk Hamiltonian, spår, positivitet, SI-enheter och analytiska gränsfall.
Nuvarande kodtester validerar endast den analytiska qubitkanalen, inte atomfysik.

**E1 — reproduktion/pilot, vecka 3–4.** Reproducera ett Eu:YSO- och ett laddningsstyrt
31P:28Si-fall med explicit kontrollprotokoll. Gör skillnad mellan passad modell och
oberoende prediktion. Gate: avvikelser ska ligga inom publicerad osäkerhet plus dokumenterad
numerisk tolerans; annars stoppa kandidaten. Kända detaljer som saknas får inte ersättas
av justering till önskad T2. Kalibrera CPU/GPU-tid och minne på tre storlekar.

**E2 — screening, vecka 5–7.** Registret har exakt 590 poster men det är inte 590 simuleringar.
Tolv startspår finns i candidates.json. För varje spår definieras tre FYSISKT relevanta
miljökonfigurationer (inte samma temperaturer för alla), tre kontrollprotokoll och tjugo
oberoende badrealiseringar: högst 12 × 3 × 3 × 20 = **2 160 pilotkörningar** när samtliga
spår klarat evidensgate. Om K spår klarar gate blir antalet 180K. För jämförelser dela
samma genererade bad, inte bara seednummer. Backendkonvergens och metodreplikation räknas
separat och bestäms efter pilot. Tre kontrollprotokoll = Ramsey, Hahn, en låst DD-sekvens.
Finalister väljs via Paretofront, aldrig på bästa seed.

**E3 — nätverk och konfirmation, vecka 8–10.** Högst tre finalister + tre tillämpliga
baslinjer = sex profiler. Planerad matris: profiler × kedja/stjärna/ring × 10/50/100 km per
länk × två trafiknivåer (0.2/0.7 av en gemensam baslinjes kapacitet) × två backendadaptrar
× tjugo arbetslaster = högst **4 320 körningar**. Vid P profiler: 720P.
En gemensam fysisk modell måste vara validerad i båda backends först. E3 körantal är
provisoriskt; konfirmatoriskt antal bestäms från önskad CI-bredd/pilotvarians. Använd nya
arbetslaster, låst Fmin=0.90, samma genererade ankomst-/förlustfiler och parad analys.
Konfirmatoriska material-/badkörningar ingår inte i pilotens 2 160 och dimensioneras efter
pilot; denna plan låtsas inte ange en slutlig total innan detta är känt.

Masterseed pilot=20261009. Separata strömmar: bath, technical_noise, workload, tuning.
Held-out masterseed=20261109; inga held-out data används för modellval. `stable_seed` i
lab.py använder SHA256 och stabila ID:n. Molekyler hålls isär på kemisk scaffold/värd
i det separata ML-projektet. Minneslabbet använder tabelluppslag och deterministisk fysik.

Statistisk enhet: oberoende bad/sample för material, arbetslastkörning för nätverk.
Tidssteg/shots är inte oberoende repliker. Använd parad eller hierarkisk bootstrap och
Holm-korrigering för den låsta hypotesfamiljen. Beräkningsosäkerhet och modellbias ska
redovisas separat; fler seeds gör inte felaktig fysik korrekt.

Alla försök får status success, invalid_physics, numerical_failure, timeout eller
missing_data. Behåll misslyckanden; en teknisk retry med samma config/seed och explicit
logg är tillåten. Registrera git-commit, backend- och beroendelås, config-hash, raw data,
solverkonvergens, maskin/resurser och seedmanifest. Ingen molnkörning ingår i startpaketet.
Kostnader för kvantkemi måste skattas från pilot; GPU-timmar är inte rimligt standardmått
för alla metoder. Lås resursbudget och timeouts innan E2/E3 körs.

## 7. Figurer och acceptanskriterier

- F1: predikterade/uppmätta nivåer med eV/osäkerhet, per species och metod.
- F2: |rho01(t)|/|rho01(0)|, tid i sekunder, per kontroll och miljö; inga sammanblandade T2.
- F3: full processfidelity och retrieval probability mot tid, med osäkerhet separat.
- F4: T2–fidelity–effektivitet Paretofront vid låst lagringstid och driftkostnad.
- F5: goodput och 95% CI mot trafik, per backend och kandidat.
- F6: laddningsbyte/host/isotop/DD-ablation, inklusive kontrollernas latens och värme.

Om E1 misslyckas: förbättra fysikmodellen, ingen materialscreening. Om laddningsbytet
förstör koherens: stoppa det protokollet, inte alla jonminnen. Om materialvinsten försvinner
i nätverket: redovisa den som lokal materialvinst, ingen nätverksförbättring. Om E3 håller:
bered experimentförslag med en atom-/materialfysiker och ett optiskt kvantminneslabb.

Billigaste avgörande nästa arbete: modellera två elektron/miljö-slutkanaler för ett konkret
laddningsbytesprotokoll och bestäm om deras överlapp räcker för en koherent minneskanal.
Den analytiska överlappsillustrationen i lab.py är ett pedagogiskt gränsfall; faktiska
spridningsamplituder har inte beräknats.

## 8. Källor och programvarudokumentation

- https://doi.org/10.1103/PRXQuantum.6.010302
- https://doi.org/10.1038/s41467-021-22706-y
- https://doi.org/10.1126/science.1239584 ; författarmanuskript https://arxiv.org/abs/2303.17734
- https://doi.org/10.1038/s41563-026-02539-0
- https://arxiv.org/abs/2605.10077 (preprint)
- https://doi.org/10.1038/s41467-026-77060-8
- https://doi.org/10.1103/PhysRevLett.113.063001
- https://www.nist.gov/pml/atomic-spectra-database
- https://webbook.nist.gov/chemistry/ea-ser/
- https://www.nist.gov/publications/binding-energies-atomic-negative-ions-iii
- https://pyscf.org/user/index.html
- https://pycce.readthedocs.io/en/latest/ ; metodartikel https://arxiv.org/abs/2107.05843

Versionslås för framtida externa backends ska tas från faktiskt installerad och testad
miljö. Det här offlinepaketet installerar inga externa backends.

## 9. Reviderat huvudmål: användbar minnestid och temperatur, v0.2

Användarens precisering styr prioriteringen: minnena ska lagra ett nätverksrelevant
kvanttillstånd och kunna leverera det med tillräcklig kvalitet. Kartlägg litteratur först,
återanvänd tillförlitliga mätdata och simulera bara luckor och nya konstruktioner.

Definiera användbar tid utifrån fullkanalens villkorade fidelity, återhämtningssannolikhet,
latens och aktivitet vid ett givet termiskt protokoll. Rapportera både fasta jämförelsetider
och tröskelpassager. Trösklar väljs per nätverksuppgift; inget enda universellt minimum
antas. T2_idle, T2_active och T2_under_DD lagras separat med exakta protokoll. Om decay
inte är exponentiell används kurvan, inte ett godtyckligt enda T2-värde.

Termiskt protokoll: T_write, T_store, T_read, temperaturkurva under övergång, ramp-/settlingtid,
koherensförlust under ramp, återhämtningsfel, kyl-/kontrolleffekt och cykeltid. Separera
minnesprovets temperatur från detektorernas. Högre driftstemperatur är ett eget Pareto-mål.
En kall skrivning/läsning med varm lagring är inte samma system som komplett varm drift.

Evidens hålls i fyra fysiska lager: atom-/isotopdata; värdmaterial/lokal Hamiltonian;
demonstrerad skriv–lagra–läs; nodfunktion under nätverksaktivitet. Detta är olika former
av funktionell evidens, inte en automatisk ranking av publikationers trovärdighet.
För varje värde: källa/version, tabell/figur, enhet, mät- eller beräkningsmetod, osäkerhet,
prov, isotoprenhet, temperatur, fält, kontrollsekvens, postselektion och kompatibla övriga
parametrar. Numeriska parametrar från olika experiment får inte sättas ihop till ett
”superminne” utan gemensam validering. Icke rapporterat = null.

Nuclear spin I och kärnans magnetiska moment kan vara isotopspecifika ingångsvärden.
Hyperfintensorer, quadrupolkoppling och dekoherens är däremot också beroende av elektroniskt
tillstånd, värdmaterial, symmetri och lokala störningar. En isotop har inte ett enda
universellt T2. Uppmätta värden ska villkoras på det experiment de kommer från.

Källkvalitet bedöms genom tydlig metod, felbudget, raw data, oberoende reproduktion,
korrigeringar och samsyn mellan relevanta mätningar. Peer review/preprint anges, men är
inte ensam kvalitetsgate. Spinnavläsningsfidelity, SPAM och fotonisk processfidelity
får inte blandas. Svaga koherenta pulser hålls isär från heralded single-photon inputs.

Ny viktig jämförelse: Lv et al., arXiv:2511.12537v2 (preprint). Vid 1.65 K rapporteras
88.0 +/- 2.1 procent qubitfidelity efter 5.6 s och 8.2 procent effektivitet. Separat
rapporteras 27.6 +/- 0.5 s 1/e-lagringslivslängd. Dessa får inte läsas som visad
88 procent fidelity vid 27.6 s. Källan är en nödvändig baslinje inför nyhetspåståenden:
https://arxiv.org/html/2511.12537v2

För aktiv minnesfunktion är även detta arbete relevant:
https://doi.org/10.1038/s41534-022-00637-w
Det granskar kärnspinnets stabilitet under upprepade entanglement-primitiver och visar
att laddningsinstabilitet kan vara en begränsning. Aktivt protokoll, inklusive den
utelämnade optiska pi-pulsen, måste jämföras exakt.

Nästa konkreta leverans är en källgranskad benchmarkkatalog som täcker fotoniska
absorptionsminnen, emissiva repeaternoder och hybridminnen i separata uppgiftsklasser.
Först därefter låses kandidater och konfirmatoriska gates. De tidigare E2/E3-körbudgetarna
är fortfarande preliminära och måste omprövas mot denna operationella benchmark.
