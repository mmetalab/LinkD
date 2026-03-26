from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional
from services import db, df_to_records, save_csv, _last_results

router = APIRouter()


@router.get("/binding/preload")
def binding_preload(page: int = 1, page_size: int = 50, gene_filter: str = ""):
    """Return all genes with binding stats, paginated + filterable."""
    tbs = db.dfs.get("target_binding_stats")
    if tbs is None or tbs.empty:
        return {"genes": [], "total": 0, "page": 1, "page_size": page_size}

    # Build gene list with drug counts
    dtd = db.dfs.get("drug_target_disease")
    drug_counts = dtd["Gene"].value_counts().to_dict() if dtd is not None and "Gene" in dtd.columns else {}

    rows = []
    for _, r in tbs.iterrows():
        gene = str(r.get("Gene", ""))
        rows.append({
            "gene": gene,
            "drug_count": drug_counts.get(gene, 0),
            "avg_pkd": r.get("Avg_pKd"),
            "max_pkd": r.get("Max_pKd"),
            "n_hit": r.get("N_hit"),
            "tpi": r.get("TPI"),
        })

    # Filter
    if gene_filter:
        gf = gene_filter.upper()
        rows = [r for r in rows if gf in r["gene"].upper()]

    # Sort by drug count descending
    rows.sort(key=lambda x: x.get("drug_count", 0) or 0, reverse=True)

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]

    # Phases for filter dropdown
    phases = sorted([float(p) for p in dtd["phase"].dropna().unique()]) if dtd is not None and "phase" in dtd.columns else []

    return {"genes": page_rows, "total": total, "page": page, "page_size": page_size, "filters": {"phases": phases}}


from pydantic import Field, field_validator

class BindingRequest(BaseModel):
    gene: str = Field("", max_length=50)
    drug_id: str = Field("", max_length=30)
    min_affinity: Optional[float] = Field(None, ge=0, le=20)

    @field_validator("gene")
    @classmethod
    def clean_gene(cls, v: str) -> str:
        return v.strip().upper()[:50] if v else ""

    @field_validator("drug_id")
    @classmethod
    def clean_drug_id(cls, v: str) -> str:
        v = v.strip()
        if v and not v.upper().startswith("CHEMBL"):
            raise ValueError("Drug ID must start with CHEMBL (e.g., CHEMBL1229517)")
        return v


@router.post("/binding/search")
def binding_search(req: BindingRequest):
    gene = req.gene.strip().upper() if req.gene else ""
    drug_id = req.drug_id.strip() if req.drug_id else ""

    if not gene and not drug_id:
        return {"error": "Enter a gene symbol and/or drug ID."}

    result = {"stats": None, "landscape": [], "radar": None, "table": [], "table_columns": []}

    # Gene-based search
    if gene:
        binding_stats = db.get_target_binding_stats(gene=gene)
        if binding_stats:
            result["stats"] = {
                "avg_pkd": binding_stats.get("Avg_pKd"),
                "max_pkd": binding_stats.get("Max_pKd"),
                "drug_hits": binding_stats.get("N_hit"),
                "tpi": binding_stats.get("TPI"),
            }

        # Landscape: top drugs by affinity
        top_drugs = db.get_drugs_for_target_with_affinity(gene, limit=20)
        if not top_drugs.empty and "aff_local" in top_drugs.columns:
            landscape = top_drugs.sort_values("aff_local", ascending=False)
            result["landscape"] = [
                {"drug": row.get("Drug", ""), "affinity": row.get("aff_local", 0),
                 "selectivity": row.get("Selectivity_Score", 0)}
                for _, row in landscape.iterrows()
            ]

        # Table: drugs targeting gene
        drugs_df = db.get_drugs_by_target(gene)
        if not drugs_df.empty:
            cols = [c for c in ["drugId", "Drug Name", "Gene", "phase", "status", "diseaseId"] if c in drugs_df.columns]
            table_df = drugs_df[cols] if cols else drugs_df
            result["table"] = df_to_records(table_df)
            result["table_columns"] = list(table_df.columns)
            _last_results["binding_df"] = table_df

    # Drug + Gene: evidence radar
    if drug_id and gene:
        evidence = db.get_comprehensive_drug_target_evidence(drug_id, gene)
        if evidence and "sources" in evidence:
            source_keys = ["binding_affinity", "drug_response", "target_stats", "drug_selectivity"]
            labels = ["Binding Affinity", "Drug Response", "Target Statistics", "Drug Selectivity"]
            radar_values = []
            for key in source_keys:
                src = evidence["sources"].get(key, {})
                if src.get("found"):
                    radar_values.append(1.0 if src.get("strength", "moderate") == "strong" else 0.6)
                else:
                    radar_values.append(0.0)
            result["radar"] = {
                "categories": labels,
                "values": radar_values,
                "overall_strength": evidence.get("overall_strength", "unknown"),
            }

    elif drug_id and not gene:
        targets_df = db.get_targets_for_drug_with_affinity(drug_id, min_affinity=req.min_affinity)
        if not targets_df.empty:
            result["table"] = df_to_records(targets_df)
            result["table_columns"] = list(targets_df.columns)
            _last_results["binding_df"] = targets_df

    return result


@router.get("/binding/download/csv")
def binding_download_csv():
    df = _last_results.get("binding_df")
    path = save_csv(df, "binding")
    if not path:
        return {"error": "No data to download"}
    return Response(
        content=open(path, "rb").read(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=linkd_binding.csv"},
    )
