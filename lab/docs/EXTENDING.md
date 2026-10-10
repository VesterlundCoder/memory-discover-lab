# Utvidga labbet

## Ny datakälla

Lägg en exakt URL i HTTP-connectorn eller välj version och filfilter i
GitHub/Zenodo/Dryad. Lägg en importer i importers.py som producerar observationer
med mängd, enhet, villkor, osäkerhet, evidenstyp och källposition.
Registrera den i import_artifact. Skriv ett test som skulle upptäcka en ändrad
kolumnordning, fel enhet eller sammanblandning av experiment och fit.

Importera negativa resultat med samma objekt som positiva resultat. Saknat
optiskt gränssnitt, uppmätt avläsningsbrus eller avsaknad av en klockövergång
är observationer/experimentvillkor, inte ett skäl att radera kandidaten.

## Ny familjemodell

Lägg familjen i catalog.FAMILIES och dess tillåtna fysikbeskrivningar i
models.FAMILY_MODELS. Implementera familjens skriv/läs-, dynamik- och
brusbeskrivning. Returnera MemoryChannel när den logiska qubitkanalen
och ett tillståndsoberoende heraldat förlustutfall är motiverade.
Vid tillståndsberoende heralding behövs ett kvantinstrument med olika
Krausgrenar; denna versions MemoryChannel-contract ska då utvidgas.

Verifiera en analytisk gräns eller ett referensproblem, CPTP, solverkonvergens
och en experimentell baslinje under samma villkor. Lägg först därefter
familjen i discovery-studier.

## Nya kombinationer

Generatorn ger okända laddnings-, spinn-, isotop- och värdvarianter.
Laddningsändring kan kräva ny elektronstruktur och optimerad geometri.
Värdändring kan kräva nya hyperfintensorer, deformationer och fononer.
Isotopändring behöver kontrollerad platstilldelning, kärnspinn och
gyromagnetiska/kvadrupolära data. Återanvänd inte ett gammalt T2 som om
det vore ett elementvärde.

När inputs finns kan samma experimentrunner söka temperatur,
kontrollsekvens, optisk brusbudget och retrieval. Runnern får parameterfält
via grid med punktseparerade nycklar. Expensive elektronik är en separat
cache och räknas inte om för varje kontrollpuls.

## Nätverk

Använd load_device / MemoryDevice.retrieve i simulatorns läshändelse.
Håll ett ursprungligt gemensamt tillstånd för lagrade sammanflätade qubits.
Vid felutfall signalera förlust till nätverkets egna protokoll.
För en ny lagringsålder: beräkna kanalen på den åldern, inte via
godtycklig extrapolation av en tabell.

Mappa sekunder till nätverkets egna tidsenheter, kontrollera heraldingens
händelseordning och använd read_latency_s i schemaläggningen. Testa att
minnesbrus inte också läggs på av simulatorns standardminne.
Nätverks- och materialmodellerna behöver därefter korsvalideras med ett
gemensamt spår, samma seeds, samma mätdefinitioner och samma händelseordning.
