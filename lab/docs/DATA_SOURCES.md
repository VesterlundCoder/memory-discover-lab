# Automatisk datahämtning

Alla källor konfigureras i JSON. Hämtaren använder tidsgräns, retries, fil- och
bytebudget, checksumma när arkivet anger den, lokal cache och oförändrade råfiler.
GitHub-filer hämtas från den commit som faktiskt hittas. Om schemat ändras får
körningen ett uttryckligt fel. Import av en fil är en transaktion.

## Kopplingar

| Connector | Inmatning | Import |
|---|---|---|
| HTTP(S) | Exakta fil-URL:er | NIST:s märkta ASCII, CIAAW:s HTML, granskad CSV eller enbart råarkiv |
| GitHub | Repository, ref och filfilter | Molekyl-qubit-CSV eller granskad CSV; valfri råfil |
| Zenodo | Record-id och filfilter | API-metadata och filernas arkivchecksummor; granskad mappning efter hämtning |
| Dryad | DOI och filfilter | API-version, paginerad fillista och nedladdningar |
| BMRB metabolomics | Valda bmse/bmsm-id | NMR-STAR chemical shifts med PyNMRSTAR |
| PubChem | Valda CID | Molekylegenskaper och valfri beräknad 3D-SDF, inte uppmätt T2 |

Defaultplanen hämtar Molecular Qubit Dataset, två Cr(IV)-experimentfiler från
Zenodo och CIAAW:s isotopfördelningar. Dessa tre liveflöden verifierades i denna
version. Den större planen innehåller även NIST, Dryad, BMRB, PubChem och kryogena
materialdata. Kontrollera verifieringsrapporten för deras faktiska teststatus;
en implementerad connector innebär inte att varje webbplats alltid är nåbar.

## Uppmätta data och okända enheter

Molecular Qubit Dataset har 149 rader i den hämtade commitversionen. T1_10,
T1_80, T2_10 och T2_80 innehåller tillsammans 421 numeriska värden. CSV-filen och
dess README fastställer inte alla enheter, pulssekvenser eller definitioner.
Importen lagrar därför source_unspecified som enhet och reported_T1/reported_T2
som mängd. Temperaturens kolumnetikett bevaras utan att automatiskt bli en
verifierad temperatur i kelvin.

Denna mappning läggs in efter originalgranskning:

{
  "columns": {
    "T1_10": {
      "unit": "us",
      "conditions": {"storage_temperature_K": 10},
      "review_source": "EXAKT originalreferens, tabell/sida och definitionsgranskning"
    }
  }
}

Exemplet visar formatet. Det godkänner inte mikrosekunder för den verkliga kolumnen.
Använd separata granskade datautdrag om olika rader har olika mätvillkor.
En source_unspecified-observation får inte bindas till en SI-parameter.

CIAAW-importen behåller intervall och parentesosäkerheter. Naturlig sammansättning
är inte isotoprenheten i ett experiment. Kärnspinn och kärnmoment lämnas okända
tills motsvarande kärndata är granskade. Radioaktiva element utan representativ
naturlig fördelning hoppas över; deras hakparentesvikt är ingen isotopfördelning.

NIST-importen bevarar massor och originalosäkerhet. Tillståndet anges separat.
Värdberoende hyperfintensorer får inte behandlas som universella isotopkonstanter.

## Fler data från andra forskningsfält

De tidigare registren i research/2026-10-09/ bevaras. De innehåller bland annat
IAEA, NIST ASD/WebBook, GISSMO, nmrXiv, spintrap, COD, NOMAD, läkemedelsdata och
negativa experiment. Övriga registerposter är forskningsspår, inte färdiga importadaptrar.

CDMS/HITRAN-spektroskopi kan ge övergångsfrekvenser, oscillatorstyrkor eller
tryckbreddning. Kvantkemiska databaser kan ge geometrier och elektroniska egenskaper.
NMR/EPR kan begränsa spinn-Hamiltonianer. Materialvetenskap kan ge fononer,
värmeledning och värdmiljöer. Varje ny numerisk fil kräver en granskningsbar
kolumnmappning och villkorsdeklaration.

Spara datakällans åtkomst- och licensuppgifter i manifestet. Hämtade råfiler och den
nya rådatakatalogen ingår inte i kodarkivet; de återskapas med data-planen.
Valda Zenodo-filer är CC BY 4.0 enligt API-metadata. Dataset utan verifierad
redistributionslicens märks uttryckligen.

## Excel och granskad CSV

extract-xlsx exporterar endast de namngivna flikarna till CSV. Formler bevaras som
text. Importera sedan med mapped_csv och deklarera om kolumnen är rådata,
experimentfit eller beräkning. Ingen formel eller fitkolumn behandlas automatiskt
som ett experimentvärde.

En mapped_csv-mappning behöver review_source, evidence_kind, subject_id eller
subject_column, conditions och measurements. Varje mätning anger value_column,
quantity, unit och valfri target_unit/uncertainty_column. Standardfel och
systematisk osäkerhet måste hållas åtskilda i källgranskningen.
