"""
LinkD Agent API — FastAPI backend for the LinkD Drug Discovery Agent.

Run with: uvicorn main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Add project root to path for agent imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load .env (check both project root and web server dir)
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services import db, precompute_overview

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("linkd")

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: precompute overview data."""
    app.state.overview = precompute_overview()
    logger.info("API ready.")
    yield


app = FastAPI(
    title="LinkD Agent API",
    description="Drug-Disease-Target analysis platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error. Please try again."})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from routers import overview, binding, selectivity, ehr, agent as agent_router

app.include_router(overview.router, prefix="/api", tags=["Overview"])
app.include_router(binding.router, prefix="/api", tags=["Binding"])
app.include_router(selectivity.router, prefix="/api", tags=["Selectivity"])
app.include_router(ehr.router, prefix="/api", tags=["EHR"])
app.include_router(agent_router.router, prefix="/api", tags=["Agent"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "datasets": len(db.dfs)}


@app.get("/api/agent/prerun/{name}")
def get_prerun_example(name: str):
    """Return a pre-run agent example result by name."""
    import json
    examples_dir = Path(__file__).parent.parent / "example_results"
    filepath = examples_dir / f"{name}.json"
    if not filepath.exists():
        return {"error": f"Example '{name}' not found"}
    with open(filepath) as f:
        return json.load(f)


@app.get("/api/examples")
def get_examples():
    """Return all example inputs for each module."""
    return {
        "binding": [
            {"label": "BRAF", "gene": "BRAF", "drug_id": "", "min_affinity": ""},
            {"label": "EGFR", "gene": "EGFR", "drug_id": "", "min_affinity": ""},
            {"label": "BRAF + Vemurafenib", "gene": "BRAF", "drug_id": "CHEMBL1229517", "min_affinity": ""},
            {"label": "EGFR + Erlotinib", "gene": "EGFR", "drug_id": "CHEMBL553", "min_affinity": "7.0"},
        ],
        "selectivity": [
            {"label": "Vemurafenib", "drug_id": "CHEMBL1229517", "selectivity_type": "All"},
            {"label": "Erlotinib", "drug_id": "CHEMBL553", "selectivity_type": "All"},
            {"label": "Highly Selective", "drug_id": "", "selectivity_type": "Highly Selective"},
            {"label": "Broad-spectrum", "drug_id": "", "selectivity_type": "Broad-spectrum"},
        ],
        "ehr": [
            {"label": "CHEMBL716", "drug_id": "CHEMBL716", "drug_name": "", "icd_code": "", "disease_name": "", "source": "Both"},
            {"label": "Aspirin", "drug_id": "", "drug_name": "aspirin", "icd_code": "", "disease_name": "", "source": "Both"},
            {"label": "Prostate Cancer (C61)", "drug_id": "", "drug_name": "", "icd_code": "C61", "disease_name": "", "source": "Both"},
            {"label": "Melanoma (MS)", "drug_id": "", "drug_name": "", "icd_code": "", "disease_name": "melanoma", "source": "Mount Sinai"},
        ],
        "agent": [
            {"label": "Lung Cancer Repurposing", "query": "Find all drugs on target or those that can be repurposed for lung cancer"},
            {"label": "Vemurafenib-BRAF Evidence", "query": "How strong is the evidence that vemurafenib binds to BRAF, and does real-world clinical data support this interaction?"},
            {"label": "EGFR Target Landscape", "query": "Which drugs most potently target EGFR, and how does EGFR rank among druggable oncology targets?"},
            {"label": "BRAF Melanoma Therapies", "query": "What therapeutic options exist for melanoma patients through BRAF-targeted drugs?"},
        ],
    }


# ============================================================
# Serve React frontend build (single-port deployment)
# ============================================================

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Serve static assets (JS, CSS bundles)
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{path:path}")
    def serve_frontend(path: str):
        """Serve React SPA — all non-API routes return index.html."""
        file = frontend_dist / path
        if file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/")
    def no_frontend():
        return {"message": "Frontend not built. Run: cd ../frontend && npm run build"}
