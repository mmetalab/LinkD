"""
Shared services: database instance, helper functions, download utilities.
"""

import sys
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd

# Ensure agent package is importable
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent import load_database, LLMPlanningAgent, LLMClient, PROVIDERS

# ============================================================
# Database (loaded once at import time)
# ============================================================

print("Loading database...")
# DATABASE_DIR env var allows overriding the data location (e.g., on Render with persistent disk)
_db_dir = os.getenv("DATABASE_DIR", str(project_root / "Database"))
# load_full_data=False samples large files (>200MB) to 100K rows for fast startup
db = load_database(_db_dir, load_full_data=False)
print(f"Database loaded: {len(db.dfs)} datasets")

# Data version tracking
from datetime import datetime as _dt
DATA_VERSION = "1.0.0"
DATA_LOADED_AT = _dt.now().isoformat()
DATA_SOURCES_VERSION = {
    "ChEMBL": "34",
    "Mount Sinai EHR": "2024-11",
    "UK Biobank": "2024-11",
    "PRISM/GDSC": "2024-Q4",
    "Open Targets": "24.09",
}

# ============================================================
# Agent state (per-session, not persistent)
# ============================================================

planning_agent: Optional[LLMPlanningAgent] = None
current_plan = None
execution_history: list = []
_last_results: Dict[str, Any] = {}

# ============================================================
# Provider map
# ============================================================

PROVIDER_MAP = {
    "OpenAI": ("openai", PROVIDERS["openai"]["models"]),
    "Google Gemini": ("gemini", PROVIDERS["gemini"]["models"]),
    "Anthropic Claude": ("claude", PROVIDERS["claude"]["models"]),
}

# ============================================================
# Precompute overview
# ============================================================


def precompute_overview() -> dict:
    """Build overview data at startup. Returns JSON-serializable dict."""
    stats = db.get_statistics()
    db_info = db.get_database_info()

    # Stat cards
    cards = []
    if "drugs" in stats:
        cards.append({"label": "Unique Drugs", "value": stats["drugs"]["unique_drugs"], "color": "#238B45"})
        cards.append({"label": "Unique Targets", "value": stats["drugs"]["unique_targets"], "color": "#2171B5"})
        cards.append({"label": "Unique Diseases", "value": stats["drugs"]["unique_diseases"], "color": "#CB181D"})
        cards.append({"label": "Associations", "value": stats["drugs"]["total_records"], "color": "#756BB1"})
    if "ehr_mount_sinai" in stats:
        cards.append({"label": "EHR Mount Sinai", "value": stats["ehr_mount_sinai"]["total_records"], "color": "#FE9929"})
    if "ehr_uk_biobank" in stats:
        cards.append({"label": "EHR UK Biobank", "value": stats["ehr_uk_biobank"]["total_records"], "color": "#D94701"})
    if "drug_response" in stats:
        cards.append({"label": "Drug Response (CRISPR)", "value": stats["drug_response"]["total_records"], "color": "#1B9E77"})
    if "causal_associations" in stats:
        cards.append({"label": "Gene-Disease Links", "value": stats["causal_associations"]["total_records"], "color": "#636363"})

    # Records by source (bar chart data)
    sources_data = []
    for key, label in [("drugs", "Drug-Target-Disease Associations"), ("causal_associations", "Causal Gene-Disease Links"),
                        ("ehr_mount_sinai", "EHR Mount Sinai"), ("ehr_uk_biobank", "EHR UK Biobank"),
                        ("drug_response", "CRISPR Drug Response")]:
        if key in stats:
            sources_data.append({"source": label, "count": stats[key]["total_records"]})

    # Phase distribution
    phases_data = []
    if "drugs" in stats and stats["drugs"].get("phases"):
        phase_names = {0.5: "Preclinical", 1.0: "Phase I", 2.0: "Phase II", 3.0: "Phase III", 4.0: "Approved (IV)"}
        for k in sorted(stats["drugs"]["phases"].keys()):
            label = phase_names.get(float(k), f"Phase {k}")
            phases_data.append({"phase": label, "count": stats["drugs"]["phases"][k]})

    # Top 10 genes
    top_genes_data = []
    if "drug_target_disease" in db.dfs:
        dtd = db.dfs["drug_target_disease"]
        if "Gene" in dtd.columns:
            top = dtd["Gene"].value_counts().head(10)
            for gene, count in top.items():
                top_genes_data.append({"gene": gene, "count": int(count)})

    # Oncogene roles
    roles_data = []
    if "oncogenes" in stats and stats["oncogenes"].get("role_distribution"):
        for role, count in stats["oncogenes"]["role_distribution"].items():
            roles_data.append({"role": role, "count": count})

    # Data sources table
    sources_table = []
    for name, info in sorted(db_info.items()):
        sources_table.append({"dataset": name, "rows": info["rows"], "columns": info["column_count"]})

    return {
        "cards": cards,
        "charts": {
            "sources": sources_data,
            "phases": phases_data,
            "top_genes": top_genes_data,
            "roles": roles_data,
        },
        "sources_table": sources_table,
        "data_version": DATA_VERSION,
        "data_loaded_at": DATA_LOADED_AT,
        "source_versions": DATA_SOURCES_VERSION,
    }


# ============================================================
# DataFrame to JSON helper
# ============================================================


def df_to_records(df: pd.DataFrame, max_rows: int = 200) -> List[dict]:
    """Convert DataFrame to list of dicts, with NaN → None."""
    if df is None or df.empty:
        return []
    return df.head(max_rows).where(df.notna(), None).to_dict(orient="records")


# ============================================================
# Download helpers
# ============================================================


def save_csv(df: pd.DataFrame, name: str = "results") -> Optional[str]:
    """Save DataFrame to temp CSV, return path."""
    if df is None or df.empty:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, prefix=f"linkd_{name}_")
    df.to_csv(tmp.name, index=False)
    return tmp.name
