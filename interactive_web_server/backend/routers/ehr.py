from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional
from services import db, df_to_records, save_csv, _last_results

router = APIRouter()


ICD_CATEGORIES = {
    "C": "Cancer", "I": "Cardiovascular", "E": "Endocrine & Metabolic",
    "F": "Mental & Behavioral", "J": "Respiratory", "K": "Digestive",
    "L": "Skin", "M": "Musculoskeletal", "N": "Genitourinary",
    "G": "Nervous System", "D": "Blood & Immune", "O": "Pregnancy",
}


@router.get("/ehr/preload")
def ehr_preload(
    page: int = 1, page_size: int = 50, source: str = "Both",
    drug_filter: str = "", disease_filter: str = "",
    icd_prefix: str = "C", atc_category: str = "",
):
    """Return deduplicated, filtered EHR data with category panels."""
    import pandas as _pd

    # --- Build combined DataFrame ---
    print(f"EHR preload: db has {len(db.dfs)} datasets, keys: {list(db.dfs.keys())}")
    frames = []
    if source in ("Both", "Mount Sinai"):
        ms = db.dfs.get("ehr_mount_sinai")
        print(f"  ehr_mount_sinai: {'found, ' + str(len(ms)) + ' rows' if ms is not None else 'NOT FOUND'}")
        if ms is not None and not ms.empty:
            msc = ms.copy()
            msc["Source"] = "Mount Sinai"
            msc["Odds Ratio"] = msc["logit_or"] if "logit_or" in msc.columns else None
            msc["P-Value"] = msc["logit_p"] if "logit_p" in msc.columns else None
            msc["Hazard Ratio"] = msc["cox_hr"] if "cox_hr" in msc.columns else None
            msc["Exposed+Disease"] = msc["exposed_occurred(a)"] if "exposed_occurred(a)" in msc.columns else None
            msc["Unexposed+Disease"] = msc["no_exposed_occurred(c)"] if "no_exposed_occurred(c)" in msc.columns else None
            msc["Drug Category"] = msc["ATC Level_1_name"] if "ATC Level_1_name" in msc.columns else ""
            frames.append(msc)
    if source in ("Both", "UK Biobank"):
        uk = db.dfs.get("ehr_uk_biobank")
        if uk is not None and not uk.empty:
            ukc = uk.copy()
            ukc["Source"] = "UK Biobank"
            ukc["Odds Ratio"] = ukc["odds_ratio"] if "odds_ratio" in ukc.columns else None
            ukc["P-Value"] = None
            ukc["Hazard Ratio"] = None
            ukc["Exposed+Disease"] = ukc["drug_cancer"] if "drug_cancer" in ukc.columns else None
            ukc["Unexposed+Disease"] = ukc["no_drug_cancer"] if "no_drug_cancer" in ukc.columns else None
            ukc["Drug Category"] = ukc["ATC Level_1_name"] if "ATC Level_1_name" in ukc.columns else ""
            frames.append(ukc)

    empty = {"associations": [], "columns": [], "total": 0, "page": page, "page_size": page_size,
             "forest": [], "disease_categories": [], "drug_categories": [], "total_raw": 0}
    if not frames:
        return empty

    combined = _pd.concat(frames, ignore_index=True)
    total_raw = len(combined)

    # --- Deduplicate: keep row with lowest P-Value per (Drug Chembl ID, ICD10) ---
    if "P-Value" in combined.columns and "Drug Chembl ID" in combined.columns and "ICD10" in combined.columns:
        combined = combined.sort_values("P-Value", na_position="last")
        combined = combined.drop_duplicates(subset=["Drug Chembl ID", "ICD10"], keep="first")

    # --- Build category counts (before filtering, after dedup) ---
    disease_cats = []
    if "ICD10" in combined.columns:
        prefixes = combined["ICD10"].astype(str).str[0]
        for prefix, label in sorted(ICD_CATEGORIES.items()):
            cnt = int((prefixes == prefix).sum())
            if cnt > 0:
                disease_cats.append({"prefix": prefix, "label": label, "count": cnt})

    drug_cats = []
    if "Drug Category" in combined.columns:
        for cat, cnt in combined["Drug Category"].value_counts().head(15).items():
            if cat and str(cat) != "nan":
                drug_cats.append({"category": str(cat).capitalize(), "count": int(cnt)})

    # --- Apply filters ---
    if icd_prefix and "ICD10" in combined.columns:
        combined = combined[combined["ICD10"].astype(str).str.startswith(icd_prefix)]
    if atc_category and "Drug Category" in combined.columns:
        combined = combined[combined["Drug Category"].astype(str).str.contains(atc_category, case=False, na=False)]
    if drug_filter:
        mask = _pd.Series(False, index=combined.index)
        for col in ["Drug Chembl ID", "Drug Name"]:
            if col in combined.columns:
                mask = mask | combined[col].astype(str).str.contains(drug_filter, case=False, na=False)
        combined = combined[mask]
    if disease_filter:
        mask = _pd.Series(False, index=combined.index)
        for col in ["ICD10", "Disease Description"]:
            if col in combined.columns:
                mask = mask | combined[col].astype(str).str.contains(disease_filter, case=False, na=False)
        combined = combined[mask]

    # --- Sort ---
    if "P-Value" in combined.columns:
        combined = combined.sort_values("P-Value", na_position="last")

    total = len(combined)
    start = (page - 1) * page_size
    page_df = combined.iloc[start:start + page_size]

    # --- Display columns ---
    DISPLAY = ["Drug Name", "ICD10", "Disease Description", "Odds Ratio", "P-Value",
               "Hazard Ratio", "Exposed+Disease", "Unexposed+Disease", "Drug Category", "Source"]
    disp_cols = [c for c in DISPLAY if c in page_df.columns]
    display = page_df[disp_cols].rename(columns={"ICD10": "ICD-10", "Disease Description": "Disease"})

    # --- Volcano-style plot: OR vs -log10(P-Value) ---
    import math
    forest = []
    if "Odds Ratio" in combined.columns and "P-Value" in combined.columns:
        fdf = combined.dropna(subset=["Odds Ratio", "P-Value"]).head(200)
        for _, row in fdf.iterrows():
            pval = row["P-Value"]
            or_val = row["Odds Ratio"]
            if not isinstance(or_val, (int, float)) or math.isnan(or_val) or math.isinf(or_val):
                continue
            neg_log_p = -math.log10(pval) if isinstance(pval, (int, float)) and pval > 0 and not math.isnan(pval) else 0
            forest.append({
                "or_value": round(float(or_val), 4),
                "neg_log_p": round(neg_log_p, 2),
                "drug_name": str(row.get("Drug Name", "")),
                "disease": str(row.get("Disease Description", ""))[:40],
                "icd10": str(row.get("ICD10", "")),
                "source": str(row.get("Source", "unknown")).lower().replace(" ", "_"),
            })
    elif "Odds Ratio" in combined.columns:
        # Fallback if no P-Value (UK Biobank)
        fdf = combined.dropna(subset=["Odds Ratio"]).head(50)
        for _, row in fdf.iterrows():
            or_val = row["Odds Ratio"]
            if not isinstance(or_val, (int, float)) or math.isnan(or_val) or math.isinf(or_val):
                continue
            forest.append({
                "or_value": round(float(or_val), 4),
                "neg_log_p": 0,
                "drug_name": str(row.get("Drug Name", "")),
                "disease": str(row.get("Disease Description", ""))[:40],
                "icd10": str(row.get("ICD10", "")),
                "source": str(row.get("Source", "unknown")).lower().replace(" ", "_"),
            })

    return {
        "associations": df_to_records(display, max_rows=page_size),
        "columns": list(display.columns),
        "total": total,
        "total_raw": total_raw,
        "page": page,
        "page_size": page_size,
        "forest": forest,
        "disease_categories": disease_cats,
        "drug_categories": drug_cats,
    }


class EHRRequest(BaseModel):
    drug_id: str = ""
    drug_name: str = ""
    icd_code: str = ""
    disease_name: str = ""
    source: str = "Both"


@router.post("/ehr/search")
def ehr_search(req: EHRRequest):
    drug_id = req.drug_id.strip() or None
    drug_name = req.drug_name.strip() or None
    icd_code = req.icd_code.strip() or None
    disease_name = req.disease_name.strip() or None
    source_val = None if req.source == "Both" else req.source.lower().replace(" ", "_")

    if not any([drug_id, drug_name, icd_code, disease_name]):
        return {"error": "Enter at least one search parameter."}

    result = {"risk": None, "forest": [], "comparison": None, "table": [], "table_columns": []}

    # EHR associations
    ehr_df = db.get_ehr_drug_disease_associations(
        drug_id=drug_id, drug_name=drug_name, icd_code=icd_code,
        disease_name=disease_name, source=source_val
    )

    # Risk assessment
    risk = db.assess_prevention_risk(
        drug_id=drug_id, drug_name=drug_name, icd_code=icd_code, disease_name=disease_name
    )

    if risk and risk.get("found"):
        risk_out = {"total": risk["total_associations"], "sources": []}
        for src_key, src_label in [("mount_sinai", "Mount Sinai"), ("uk_biobank", "UK Biobank")]:
            if src_key in risk and risk[src_key].get("total", 0) > 0:
                s = risk[src_key]
                risk_out["sources"].append({
                    "name": src_label,
                    "total": s["total"],
                    "protective": s.get("protective", 0),
                    "risk_increasing": s.get("risk_increasing", 0),
                    "avg_or": s.get("avg_or"),
                })
        result["risk"] = risk_out

        # Comparison chart data
        result["comparison"] = {
            "sources": [s["name"] for s in risk_out["sources"]],
            "protective": [s["protective"] for s in risk_out["sources"]],
            "risk_increasing": [s["risk_increasing"] for s in risk_out["sources"]],
        }

    # Forest plot data
    if ehr_df is not None and not ehr_df.empty:
        or_col = None
        for col_candidate in ["logit_or", "odds_ratio", "OR"]:
            if col_candidate in ehr_df.columns:
                or_col = col_candidate
                break
        if or_col:
            plot_df = ehr_df.dropna(subset=[or_col]).head(30)
            if "ICD10" in plot_df.columns:
                labels = plot_df["ICD10"].astype(str).tolist()
            elif "Disease" in plot_df.columns:
                labels = plot_df["Disease"].astype(str).str[:30].tolist()
            else:
                labels = [f"Assoc {i+1}" for i in range(len(plot_df))]

            sources_list = plot_df["ehr_source"].tolist() if "ehr_source" in plot_df.columns else ["unknown"] * len(plot_df)
            result["forest"] = [
                {"label": lab, "or_value": float(row[or_col]), "source": src}
                for lab, (_, row), src in zip(labels, plot_df.iterrows(), sources_list)
            ]

        # Table
        result["table"] = df_to_records(ehr_df)
        result["table_columns"] = list(ehr_df.columns)
        _last_results["ehr_df"] = ehr_df

    return result


@router.get("/ehr/download/csv")
def ehr_download_csv():
    df = _last_results.get("ehr_df")
    path = save_csv(df, "ehr")
    if not path:
        return {"error": "No data to download"}
    return Response(
        content=open(path, "rb").read(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=linkd_ehr.csv"},
    )
