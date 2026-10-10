# Bradley et al. 2022: original research data

Attribution: C. E. Bradley et al., *Robust quantum-network memory based on spin qubits in isotopically engineered diamond*, npj Quantum Information **8**, 122 (2022), [article DOI](https://doi.org/10.1038/s41534-022-00637-w).

Dataset: [10.4121/16887658.v3](https://doi.org/10.4121/16887658.v3), licensed [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). The bundled files retain original bytes; no source observations or notebook contents have been modified. The analysis and plots elsewhere in this repository are adaptations with the scope described in the case report.

- `research_data.zip`: original published research-data archive (503050 bytes).
- `data_3b.json`: exact extraction of `Shared Data.zip/Shared Data/data_3b.json` from that archive.
- `DataAnalysis_RobustMemory.ipynb`: original archive notebook, retained for the observable mapping; it is not executed as our model.
- `provenance.json`: retrieval URL, source MD5 and SHA256 fingerprints.

The case loader verifies all three SHA256 fingerprints and checks that both extracted files equal their archive entries. Fig. 3b notebook code maps arrays 0–2 to time in milliseconds, transverse Bloch length and source error bars; arrays 3–5 to time in milliseconds, signed X expectation and source error bars. Published fit curves are not used as experimental targets.

See [the case report](../../../evaluation/results/bradley2022-nv0/report_sv.md) and [the audited descriptor](../../../evaluation/data/bradley2022_nv0/case.json). These observations do not identify normalized complex pure dephasing, population relaxation, or optical write/read performance.
