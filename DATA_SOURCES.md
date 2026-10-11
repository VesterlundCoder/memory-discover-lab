# Data sources and evidence boundaries

| Source | Fixed identity | Use in this article |
|---|---|---|
| Teller et al. PRX 15, 031053 (2025) | DOI `10.1103/z6lc-qw2d`; Zenodo `14929997` | Released processed state fidelities, density matrix, readout-window curves and measured-point constraints |
| Rodríguez-Moldes et al. PRL 137, 120803 (2026) | DOI `10.1103/ftkb-pkvp`; Zenodo `21532904`; arXiv `2609.02579v1` | Classical retrieval-efficiency diagnostics; distinct heralded-photon arrays remain distinct |
| Ortu et al. npj Quantum Information 8, 29 (2022) | DOI `10.1038/s41534-022-00541-3` | Five primary-text-reviewed effective spin/optical coherence references |
| Lin et al. Chemical Science 10, 548–555 (2019) | DOI `10.1039/C8SC04122A`; PMCID `PMC6335635` | Three reviewed 5 K molecular phase-memory references |
| Hu et al. Nature Communications 15, 10256 (2024) | DOI `10.1038/s41467-024-54606-2` | Two reviewed PL6 Ramsey/Hahn references with incomplete operating conditions |
| MTD-group/Molecular_Qubit_Dataset | Revision `5263b1d86b39243e7405dde5bf7c58bbd8fcd677` | 201 positive provisional entries; not treated as reviewed SI lifetimes |

Supporting methodological/software references appear in the main bibliography. The molecular systems-chart paper DOI `10.1039/D4DT02311K` supplies related context; its existence does not validate every provisional row.

The original dataset DOIs are permanent external identifiers. A fetched page's bytes and SHA-256 freeze the local version; an access date alone does not identify immutable content. The lab's source manifests retain retrieval metadata, exact paths, URLs, revisions and licenses. The final payload includes `SHA256SUMS`; the main study manifest separately identifies the original software archive.

The ten reference rows were reviewed for primary-text value, unit, observable and reported conditions. They are not independently fitted raw measurements and do not establish a full memory channel. Missing exact sample temperature, field, bath, stretch exponent or isotope distribution remains visible. Duplicate values from a study or multiple secondary-dataset entries are not independent experimental samples.

No generic molecular property, isotope mass, charge change or classical efficiency is converted to T2 without its physical model and required input parameters. Temperature at writing/storage/reading is represented separately in the model, but experimental cryostat setpoints are not asserted to be independent local thermometry.

The unchanged, licensed numerical subset needed for offline system/paper replay is tracked under `data/experimental/`. Its manifest pins each original URL, version and SHA256. Reviewed paper transcriptions remain separate from byte-verified measurement files. The historical molecular source-collection audit is not recreated by offline replay.
