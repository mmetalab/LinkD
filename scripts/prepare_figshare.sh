#!/bin/bash
# Prepare data archives for Figshare upload.
# Run from project root: bash scripts/prepare_figshare.sh
#
# Figshare free tier limit: 5 GB per file, 20 GB total per public dataset.
# DrugTargetMetrics parquets (~13 GB) split into 10 parts of 10 files each (~1.3 GB per zip).
#
# Total output: 15 zip files (~16 GB)

set -e
cd "$(dirname "$0")/.."

OUT="figshare_upload"
mkdir -p "$OUT"

echo "============================================"
echo "  LinkD: Preparing Figshare Data Archives"
echo "  Figshare limit: 5 GB per file"
echo "============================================"
echo ""

# 1. Database (~28 MB)
echo "[1/15] Database/ (~28 MB)..."
zip -r "$OUT/Database.zip" Database/ -x "*.DS_Store"
echo ""

# 2. EHR Results (~58 MB)
echo "[2/15] EHR_Results/ (~58 MB)..."
zip -r "$OUT/EHR_Results.zip" EHR_Results/ -x "*.DS_Store"
echo ""

# 3. Drug Response (~79 MB)
echo "[3/15] DrugResponse/ (~79 MB)..."
zip -r "$OUT/DrugResponse.zip" DrugResponse/ -x "*.DS_Store"
echo ""

# 4. Target Disease Association (~2.6 GB)
echo "[4/15] Target_Disease_Association/ (~2.6 GB)..."
zip -r "$OUT/Target_Disease_Association.zip" Target_Disease_Association/ -x "*.DS_Store"
echo ""

# 5. DrugTargetMetrics CSVs + index files (~80 MB)
echo "[5/15] DrugTargetMetrics CSVs + indexes (~80 MB)..."
zip "$OUT/DrugTargetMetrics_csvs.zip" \
  DrugTargetMetrics/drug_selectivity_metrics.csv \
  DrugTargetMetrics/drug_umap_clustering.csv \
  DrugTargetMetrics/target_binding_stats.csv \
  DrugTargetMetrics/drug_phase_mapping.csv \
  DrugTargetMetrics/target_centric_pan/drug_index.json \
  DrugTargetMetrics/target_centric_pan/target_index.json
echo ""

# 6-15. Parquet Parts 1-10: 10 files each (~1.3 GB per zip)
for PART in $(seq 1 10); do
  START=$(( (PART - 1) * 10 ))
  END=$(( START + 9 ))
  NUM=$(( PART + 5 ))
  echo "[$NUM/15] DrugTargetMetrics parquet part $PART (chunks $(printf '%03d' $START)-$(printf '%03d' $END), ~1.3 GB)..."
  FILES=""
  for i in $(seq $START $END); do
    CHUNK=$(printf '%03d' $i)
    FILES="$FILES DrugTargetMetrics/target_centric_pan/target_centric_pan_uniprot_chunk_${CHUNK}.parquet"
  done
  zip "$OUT/DrugTargetMetrics_parquet_part${PART}.zip" $FILES
  echo ""
done

# Summary
echo "============================================"
echo "  Archives ready in $OUT/"
echo "============================================"
echo ""
ls -lh "$OUT/"
echo ""
echo "Total:"
du -sh "$OUT/"
echo ""
echo "============================================"
echo "  Next steps:"
echo "============================================"
echo "  1. Go to https://figshare.com → 'Create a new item'"
echo "  2. Title: 'LinkD: Drug-Target-Disease Multi-Evidence Database'"
echo "  3. Category: Bioinformatics"
echo "  4. License: CC BY 4.0"
echo "  5. Upload all 15 zip files from $OUT/"
echo "  6. Publish → copy DOI"
echo "  7. Update scripts/download_data.py with file URLs"
echo "  8. Update README.md with DOI"
echo "  9. Push updates to GitHub"
