from fastapi import APIRouter, Response
from pydantic import BaseModel
from services import db, df_to_records, save_csv, _last_results

router = APIRouter()


@router.get("/selectivity/preload")
def selectivity_preload(page: int = 1, page_size: int = 50, type_filter: str = "All", drug_filter: str = ""):
    """Return UMAP landscape + paginated drug table + type distribution."""
    result = {"umap": None, "type_distribution": {}, "drugs": [], "total": 0, "page": page, "page_size": page_size}

    if "drug_umap" in db.dfs:
        umap_df = db.dfs["drug_umap"]
        if "x" in umap_df.columns and "y" in umap_df.columns:
            # Type values in CSV have prefix: "Type I: Highly Selective" etc.
            type_colors = {"Highly Selective": "#238B45", "Moderate poly-target": "#FE9929", "Broad-spectrum": "#CB181D"}
            traces = []
            for t, color in type_colors.items():
                mask = umap_df["Type"].str.contains(t, case=False, na=False)
                sub = umap_df[mask]
                if len(sub) > 2000:
                    sub = sub.sample(2000, random_state=42)
                traces.append({
                    "type": t, "color": color,
                    "x": sub["x"].tolist(), "y": sub["y"].tolist(),
                    "drugs": sub["Drug"].tolist() if "Drug" in sub.columns else [],
                })
            result["umap"] = {"traces": traces, "highlight": None}

        if "Type" in umap_df.columns:
            # Clean type names: "Type I: Highly Selective" -> "Highly Selective"
            raw_dist = umap_df["Type"].value_counts().to_dict()
            clean_dist = {}
            for k, v in raw_dist.items():
                clean_key = k.split(": ", 1)[-1] if ": " in str(k) else str(k)
                clean_dist[clean_key] = v
            result["type_distribution"] = clean_dist

    # Paginated drug table from drug_selectivity
    sel_df = db.dfs.get("drug_selectivity")
    if sel_df is not None and not sel_df.empty:
        df = sel_df.copy()

        # Join type from drug_umap if available
        if "drug_umap" in db.dfs:
            umap_types = db.dfs["drug_umap"][["Drug", "Type"]].drop_duplicates()
            if "Type" not in df.columns:
                df = df.merge(umap_types, on="Drug", how="left")

        # Filters
        if type_filter and type_filter != "All" and "Type" in df.columns:
            df = df[df["Type"].str.contains(type_filter, case=False, na=False)]
        if drug_filter:
            mask = df["Drug"].str.contains(drug_filter, case=False, na=False)
            if "Drug Name" in df.columns:
                mask = mask | df["Drug Name"].str.contains(drug_filter, case=False, na=False)
            df = df[mask]

        total = len(df)
        start = (page - 1) * page_size
        page_df = df.iloc[start:start + page_size]

        cols = [c for c in ["Drug", "Drug Name", "Selectivity_Score", "Type", "n_targets_measured"] if c in page_df.columns]
        col_rename = {"Drug": "Drug ChEMBL ID", "Selectivity_Score": "Selectivity Score", "n_targets_measured": "Targets Measured"}
        display_df = page_df[cols].rename(columns=col_rename)
        result["drugs"] = df_to_records(display_df, max_rows=page_size)
        result["drug_columns"] = list(display_df.columns)
        result["total"] = total

    return result


class SelectivityRequest(BaseModel):
    drug_id: str = ""
    selectivity_type: str = "All"


@router.post("/selectivity/search")
def selectivity_search(req: SelectivityRequest):
    drug_id = req.drug_id.strip() if req.drug_id else ""
    result = {"info": None, "bars": [], "umap": None, "table": [], "table_columns": []}

    if drug_id:
        info = db.get_drug_selectivity_info(drug_id=drug_id)
        if info:
            result["info"] = {
                "drug": info.get("Drug", drug_id),
                "selectivity_score": info.get("Selectivity_Score"),
                "drug_type": info.get("drug_type"),
                "n_targets": info.get("N_target_measured"),
            }

        # Target affinities bar data
        targets_df = db.get_targets_for_drug_with_affinity(drug_id, limit=20)
        if not targets_df.empty and "aff_local" in targets_df.columns:
            bars_df = targets_df.sort_values("aff_local", ascending=False).head(20)
            result["bars"] = [
                {"target": row.get("Target", "")[:25], "affinity": row.get("aff_local", 0)}
                for _, row in bars_df.iterrows()
            ]

        # UMAP data
        if "drug_umap" in db.dfs:
            umap_df = db.dfs["drug_umap"]
            if "x" in umap_df.columns and "y" in umap_df.columns:
                # Sample for performance (send max 2000 points per type)
                type_colors = {"Highly Selective": "#238B45", "Moderate poly-target": "#FE9929", "Broad-spectrum": "#CB181D"}
                traces = []
                for t, color in type_colors.items():
                    mask = umap_df["Type"] == t
                    sub = umap_df[mask]
                    if len(sub) > 2000:
                        sub = sub.sample(2000, random_state=42)
                    traces.append({
                        "type": t, "color": color,
                        "x": sub["x"].tolist(), "y": sub["y"].tolist(),
                        "drugs": sub["Drug"].tolist() if "Drug" in sub.columns else [],
                    })
                # Highlight searched drug
                drug_mask = umap_df["Drug"].str.contains(drug_id, case=False, na=False)
                highlight = None
                if drug_mask.any():
                    hit = umap_df[drug_mask].iloc[0]
                    highlight = {"x": float(hit["x"]), "y": float(hit["y"]), "drug": drug_id}
                result["umap"] = {"traces": traces, "highlight": highlight}

    if req.selectivity_type and req.selectivity_type != "All":
        type_df = db.get_drugs_by_selectivity_type(req.selectivity_type)
        if not type_df.empty:
            cols = [c for c in ["Drug", "Type", "x", "y", "cluster"] if c in type_df.columns]
            table_df = type_df[cols] if cols else type_df
            result["table"] = df_to_records(table_df)
            result["table_columns"] = list(table_df.columns)
            _last_results["sel_df"] = table_df

    if not drug_id and (not req.selectivity_type or req.selectivity_type == "All"):
        return {"error": "Enter a drug ID or select a selectivity type."}

    return result


@router.get("/selectivity/download/csv")
def selectivity_download_csv():
    df = _last_results.get("sel_df")
    path = save_csv(df, "selectivity")
    if not path:
        return {"error": "No data to download"}
    return Response(
        content=open(path, "rb").read(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=linkd_selectivity.csv"},
    )
