# Changelog

## 2026-03-26: LinkD Branding + Publication Prep

- Renamed modules: Binding → **LinkD-DTI**, Selectivity → **LinkD-Select**, EHR → **LinkD-Pheno**, AI Agent → **LinkD-Agent**
- Platform name: "LinkD: Multi-Evidence Supported Drug Discovery Platform"
- EHR volcano plot: X = Odds Ratio, Y = -log₁₀(P-value) with drug/disease hover
- EHR deduplication: removed 59% duplicates, cancer-focused default, ICD-10/ATC category panels
- Free Gemini 2.5 Flash mode for LinkD-Agent (no API key needed)
- README rewritten with Figshare + Render deployment workflow
- All documentation updated with LinkD module branding

---

## 2026-03-25: NAR Publication Readiness

### Completed
- HTML meta tags: title, description, keywords, Open Graph tags
- Contact info + institution + hosting commitment on About page
- MIT License statement added
- Data versioning: version number, load timestamp, source versions on About page and API
- Input validation: Pydantic field validators for gene symbols, ChEMBL IDs, affinity ranges
- Rate limiting: slowapi middleware (60 req/min per IP)
- Structured logging: Python logging module + global exception handler
- Comparison table vs Open Targets, DrugBank, STRING-db on Docs page
- Documentation consolidated: 10 markdown files reduced to 5

### Deployment Setup
- `render.yaml` — Render deployment config (web service + 20GB persistent disk)
- `scripts/download_data.py` — Figshare data download script
- `DATABASE_DIR` env var support in services.py — configurable data path for cloud deployment
- Deployment workflow: GitHub (code) + Figshare (data, ~16GB) + Render (hosting, $11/mo)

### Next Steps (Infrastructure — requires deployment decisions)
- [ ] **Deploy to public URL** with HTTPS (Render, AWS, or GCP)
- [ ] **Create Dockerfile** + docker-compose.yml for reproducible deployment
- [ ] **Add ARIA accessibility labels** and test with WAVE/axe
- [ ] **Create data validation test suite** (verify known drug-target pairs)
- [ ] **Add shareable result URLs** (query params, persistent IDs)
- [ ] **Add robots.txt and sitemap.xml** for SEO
- [ ] **Add privacy policy** page
- [ ] **Mount Sinai EHR citation** — add proper reference or data sharing URL
- [ ] **Performance benchmarks** — document query times and concurrent user limits
- [ ] **Browser compatibility testing** — Chrome, Firefox, Safari, Edge

---

## 2026-03-25: FastAPI + React Web Server

- Replaced Gradio with FastAPI backend + React + TypeScript + Vite frontend
- Interactive Plotly.js charts with hover tooltips, zoom, pan (replaced matplotlib)
- Paginated database explorer with server-side filtering for Binding (1,068 genes), Selectivity (14,981 drugs), EHR (41K+ associations)
- Pre-run agent examples viewable without API key
- Added Home, About, and Documentation pages
- Download buttons for analysis results (MD, PDF)
- Parquet query speed: 120s → 0.02s via pyarrow predicate pushdown + pre-built indexes
- External database links in tables (ChEMBL, UniProt, ICD-10)
- Gradio interface kept as fallback (`./start.sh gradio`)
- Consolidated 10 markdown files down to 5

## 2025-03-25: Multi-Model Support and Cleanup

- Added multi-model LLM support (OpenAI, Google Gemini, Anthropic Claude) via `llm_client.py`
- Database Explorer now works without any API key
- Added database-only example buttons in Agent tab
- Moved all Jupyter notebooks to `notebooks/` directory
- Consolidated integration logs into this CHANGELOG
- Added `.env` support for local API key management

## 2024-12-19: Drug-Target Metrics Integration

### Data Overview
- Integrated `DrugTargetMetrics/` folder with drug-target binding affinity and selectivity metrics
- 100 parquet files in `target_centric_pan/` for per-target binding data (loaded on-demand)

### File Renames
| Original | New | Description |
|----------|-----|-------------|
| `drug_centric_pan_uniprot.csv` | `drug_selectivity_metrics.csv` | Drug selectivity scores |
| `drug_centric_pan_uniprot_umap.csv` | `drug_umap_clustering.csv` | UMAP clustering and types |
| `target_stats_sorted_onco.csv` | `target_binding_stats.csv` | Target binding statistics |
| `drug_name_clin_phase.csv` | `drug_phase_mapping.csv` | Drug-to-phase mapping |

### New Query Functions
- `get_drug_selectivity_info()` -- selectivity score, entropy, drug type
- `get_target_binding_stats()` -- avg pKd, max pKd, N_hit, TPI
- `get_drug_target_binding_affinity()` -- on-demand parquet loading for specific pairs
- `get_targets_for_drug_with_affinity()` -- all targets for a drug sorted by pKd
- `get_drugs_by_selectivity_type()` -- filter by Highly Selective / Moderate / Broad-spectrum
- `get_comprehensive_drug_target_evidence()` -- multi-source evidence aggregation

### Key Metrics
- **pKd > 7**: Strong binding (Kd < 100 nM); **> 8**: Very strong; **> 9**: Extremely strong
- **Selectivity Score**: Higher = more selective (fewer targets)
- **Drug Types**: I = Highly Selective, II = Moderate poly-target, III = Broad-spectrum
- **TPI**: Target Prioritization Index (higher = higher priority)

---

## 2024-12-19: Drug Response Data Integration

### File Rename
| Original | New |
|----------|-----|
| `result_sig_merged_prism_gdsc_1112.csv` | `drug_response_crispr_correlation.csv` |

### New Functions
- `get_drug_response_associations()` -- query by drug/gene, filter by significance/source
- `get_drug_target_evidence()` -- evidence summary with correlation analysis

### Interpretation
- **Positive correlation** (AUC/IC50 > 0): Gene knockout increases drug sensitivity (resistance factor)
- **Negative correlation** (AUC/IC50 < 0): Gene may be the drug target
- **Significant** (FDR < 0.05): Strong evidence after multiple testing correction
- Data sources: PRISM (Broad Institute), GDSC

---

## 2024-12-19: EHR Data Integration

### File Renames
| Original | New |
|----------|-----|
| `good_drug_ehr_atc_1110.csv` | `mount_sinai_drug_disease.csv` |
| `ukb_drug_ehr_atc_1110.csv` | `uk_biobank_drug_disease.csv` |

### New Functions
- `get_ehr_drug_disease_associations()` -- query by drug ID/name, ICD code, disease name, source
- `assess_prevention_risk()` -- protective vs risk-increasing counts with OR stats
- `get_drug_name_from_id()`, `get_disease_name_from_icd()` -- lookup helpers

### Interpretation
- **OR < 1**: Drug may be protective; **OR > 1**: May increase risk; **OR = 1**: No association

---

## 2024-12-19: File Reorganization

### Moves
| From | To |
|------|----|
| `Database/disease_target_gene_opentarget_by_source_1027.csv` | `Target_Disease_Association/disease_target_by_source.csv` |
| `Database/disease_target_gene_opentarget_overall_1027.csv` | `Target_Disease_Association/disease_target_overall.csv` |
| `Database/gtdb_causal_gene_disease_1027.csv` | `Target_Disease_Association/causal_gene_disease.csv` |
| `Database/known_drug_sim_icd_open_target_1027.csv` | `Target_Disease_Association/drug_target_disease.csv` |
| `Database/target_priority_gene_1107.csv` | `Target_Disease_Association/target_priority.csv` |
| `Database/onco_gene_info_1027.csv` | `Database/onco_genes.csv` |

All date suffixes removed for cleaner naming.
