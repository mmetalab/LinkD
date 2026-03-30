# LinkD: Multi-Evidence Supported Drug Discovery Platform

LinkD is an integrated platform that combines drug-target interaction binding affinity, electronic health records, CRISPR drug response, and clinical trial data into a unified system with AI-powered natural language analysis. It provides four interconnected modules for comprehensive drug discovery research.

## Live Demo

> **URL**: [https://linkd-agent.onrender.com](https://linkd-agent.onrender.com) *(available after deployment)*
>
> **Data**: [Zenodo DOI: [10.5281/zenodo.19241152](https://doi.org/10.5281/zenodo.19241152)](https://doi.org/10.5281/zenodo.19241152) (~16 GB)

## Modules

| Module | Description | Key Data |
|--------|-------------|----------|
| **LinkD-DTI** | Drug-target interaction binding affinity explorer | 1,068 targets with pKd values, 20K+ binding pairs |
| **LinkD-Select** | Drug selectivity profiling via UMAP clustering | 14,981 drugs, selectivity scores, 3 drug types |
| **LinkD-Pheno** | Phenotype-drug associations from EHR data | 41K+ Mount Sinai + 693 UK Biobank cancer associations |
| **LinkD-Agent** | AI-powered multi-step analysis agent | Supports OpenAI, Google Gemini, Anthropic Claude |

## Quick Start

```bash
# 1. Create environment
conda create -n ttdrug python=3.12
conda activate ttdrug
conda install nodejs

# 2. Install dependencies
pip install -r requirements.txt
cd interactive_web_server/frontend && npm install && npm run build && cd ../..

# 3. (Optional) API keys for LLM features
cp .env.example .env
# Edit .env — add GEMINI_FREE_KEY for free mode, or OpenAI/Claude keys

# 4. Launch
cd interactive_web_server && ./start.sh
# Opens at http://localhost:8000
```

Other modes:
```bash
./start.sh dev      # Dev mode: FastAPI hot reload + Vite dev server
./start.sh gradio   # Legacy Gradio interface on port 7860
```

## Data

### Download from Zenodo

```bash
# Auto-download (used by Render during build)
python scripts/download_data.py

# Or manually download from Zenodo and extract to project root:
# Database/, DrugTargetMetrics/, EHR_Results/, DrugResponse/, Target_Disease_Association/
```

### Data Sources

| Directory | File | Records | Description |
|-----------|------|---------|-------------|
| Database/ | onco_genes.csv | 1,029 | Oncogene and tumor suppressor gene info |
| Target_Disease_Association/ | drug_target_disease.csv | 276,147 | Drug-target-disease associations (ChEMBL) |
| Target_Disease_Association/ | causal_gene_disease.csv | 13,008 | Causal gene-disease links (Open Targets) |
| DrugTargetMetrics/ | drug_selectivity_metrics.csv | 14,981 | Drug selectivity scores |
| DrugTargetMetrics/ | target_binding_stats.csv | 1,068 | Target binding statistics (pKd) |
| DrugTargetMetrics/ | target_centric_pan/ | 20,000+ | Per-target binding affinity (parquet, indexed) |
| EHR_Results/ | mount_sinai_drug_disease.csv | 41,120 | Mount Sinai EHR drug-disease associations |
| EHR_Results/ | uk_biobank_drug_disease.csv | 693 | UK Biobank drug-cancer associations |
| DrugResponse/ | drug_response_crispr_correlation.csv | 464,820 | CRISPR drug response (PRISM + GDSC) |

### Data Versioning

| Source | Version |
|--------|---------|
| ChEMBL | 34 |
| Mount Sinai EHR | 2024-11 |
| UK Biobank | 2024-11 |
| PRISM/GDSC | 2024-Q4 |
| Open Targets | 24.09 |

## Deployment

### Render (recommended for public hosting)

1. Push code to GitHub
2. Create Render web service → connect repo → auto-detects `render.yaml`
3. Add environment variables in Render dashboard:
   - `DATABASE_DIR` = `/opt/render/project/src/data`
   - `GEMINI_FREE_KEY` = your free Gemini API key (for LinkD-Agent free mode)
   - Optional: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
4. Deploy — first build downloads data from Zenodo (~10 min)

**Cost**: $11/mo (Render Starter $7 + 20GB disk $4)

### Zenodo (data hosting)

1. Prepare zip archives:
   ```bash
   bash scripts/prepare_figshare.sh
   # Creates 15 zip files in figshare_upload/ (~1.3 GB each max)
   ```
2. Go to https://doi.org/10.5281/zenodo.19241152 → New Upload
3. Upload all zip files from `figshare_upload/`
   - Zenodo allows up to 50 GB per record (no per-file limit issue)
4. Fill metadata:
   - **Title**: LinkD: Drug-Target-Disease Multi-Evidence Database
   - **License**: CC BY 4.0
   - **Type**: Dataset
5. Publish → copy DOI
6. Update `scripts/download_data.py` with Zenodo file URLs
7. Update this README with DOI

## Architecture

```
┌─────────────────────────────────────┐
│  React Frontend (TypeScript)        │
│  Plotly.js charts, Tailwind CSS     │
│  Pages: Home, Overview, LinkD-DTI,  │
│  LinkD-Select, LinkD-Pheno,         │
│  LinkD-Agent, About, Docs           │
└──────────────┬──────────────────────┘
               │ HTTP/JSON
┌──────────────┴──────────────────────┐
│  FastAPI Backend (Python)           │
│  /api/overview, /api/binding,       │
│  /api/selectivity, /api/ehr,        │
│  /api/agent/*, /api/health          │
│  Rate limiting (60 req/min)         │
│  Structured logging                 │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│  agent/ Python package              │
│  database_query_module.py (30+ fns) │
│  llm_planning_agent.py              │
│  llm_client.py (OpenAI/Gemini/Claude)│
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│  CSV / Parquet data (indexed)       │
│  Zenodo hosted (~16 GB)           │
└─────────────────────────────────────┘
```

## Project Structure

```
LinkD_Agent/
├── agent/                          # Python agent package
│   ├── database_query_module.py    # 30+ query functions
│   ├── llm_planning_agent.py       # Multi-step LLM planner
│   ├── llm_client.py               # Multi-model wrapper
│   └── llm_agent.py                # NL query agent
│
├── interactive_web_server/
│   ├── start.sh                    # Launch script (react/dev/gradio)
│   ├── backend/                    # FastAPI server
│   │   ├── main.py                 # App + static serving + rate limiting
│   │   ├── services.py             # DB loading, data versioning
│   │   └── routers/                # API endpoints
│   │       ├── overview.py         # GET /api/overview
│   │       ├── binding.py          # LinkD-DTI endpoints
│   │       ├── selectivity.py      # LinkD-Select endpoints
│   │       ├── ehr.py              # LinkD-Pheno endpoints
│   │       └── agent.py            # LinkD-Agent endpoints
│   ├── frontend/                   # React + TypeScript + Vite
│   │   └── src/pages/              # Home, Overview, Binding, Selectivity, EHR, Agent, About, Docs
│   └── app.py                      # Legacy Gradio fallback
│
├── scripts/
│   └── download_data.py            # Zenodo data download
├── notebooks/                      # Jupyter exploration notebooks
├── render.yaml                     # Render deployment config
├── requirements.txt
├── .env.example
└── .gitignore
```

## Web Server Pages

| Page | URL | Module | Description |
|------|-----|--------|-------------|
| Home | `/` | — | Platform overview, key stats, feature cards |
| Overview | `/overview` | — | Database statistics, records chart, phase distribution |
| LinkD-DTI | `/binding` | LinkD-DTI | 1,068 gene targets, binding landscape, evidence radar |
| LinkD-Select | `/selectivity` | LinkD-Select | UMAP landscape, 14,981 drugs, selectivity profiles |
| LinkD-Pheno | `/ehr` | LinkD-Pheno | Cancer-focused EHR, volcano plot (OR vs -log10p) |
| LinkD-Agent | `/agent` | LinkD-Agent | Free Gemini model or custom API key, plan + execute |
| About | `/about` | — | Data sources, methods, contact, license |
| Docs | `/documentation` | — | Module guides, glossary, tool comparison |

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/overview` | GET | Precomputed database statistics |
| `/api/binding/preload` | GET | Paginated gene targets with binding stats |
| `/api/binding/search` | POST | Search by gene/drug, returns landscape + radar |
| `/api/selectivity/preload` | GET | UMAP + paginated drug table |
| `/api/selectivity/search` | POST | Drug selectivity detail |
| `/api/ehr/preload` | GET | Deduplicated EHR, category filters, volcano data |
| `/api/agent/init` | POST | Initialize LLM (free Gemini or custom key) |
| `/api/agent/plan` | POST | Generate analysis plan |
| `/api/agent/execute` | POST | Execute plan, return results |
| `/api/agent/providers` | GET | Available LLM providers + models |

Interactive API docs: `http://localhost:8000/docs` (Swagger UI)

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | FastAPI server port |
| `DATABASE_DIR` | `./Database` | Data directory (override for Render) |
| `GEMINI_FREE_KEY` | — | Free Gemini API key for LinkD-Agent |
| `OPENAI_API_KEY` | — | OpenAI API key (optional) |
| `GOOGLE_API_KEY` | — | Google Gemini API key (optional) |
| `ANTHROPIC_API_KEY` | — | Anthropic Claude API key (optional) |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port conflict | `./start.sh` auto-kills existing process |
| Frontend not loading | `cd frontend && npm run build` |
| Import errors | Ensure conda env activated: `conda activate ttdrug` |
| Slow startup | Normal — CSV loading takes 10-30s |
| Agent error "no attribute client" | Use latest `agent/llm_planning_agent.py` |
| Parquet queries slow | Ensure `drug_index.json` and `target_index.json` exist |
| EHR 500 error | Check for duplicate columns — fixed in latest version |

## License

MIT License. Source code and data processing pipelines are freely available for academic use.

## Contact

- **Institution**: Icahn School of Medicine at Mount Sinai
- **Email**: cheng.wang@mssm.edu
- **GitHub**: [github.com/mmetalab/LinkD](https://github.com/mmetalab/LinkD)
