#!/bin/bash
# Prepare data archives for Figshare upload.
# Run from project root: bash scripts/prepare_figshare.sh
#
# Figshare free tier limit: 5 GB per file, 20 GB total per public dataset.
# DrugTargetMetrics (~13 GB) is split into 4 parts to stay under the limit.
#
# Total output: 7 zip files (~16 GB)

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
echo "[1/7] Database/ (~28 MB)..."
zip -r "$OUT/Database.zip" Database/ -x "*.DS_Store"
echo ""

# 2. EHR Results (~58 MB)
echo "[2/7] EHR_Results/ (~58 MB)..."
zip -r "$OUT/EHR_Results.zip" EHR_Results/ -x "*.DS_Store"
echo ""

# 3. Drug Response (~79 MB)
echo "[3/7] DrugResponse/ (~79 MB)..."
zip -r "$OUT/DrugResponse.zip" DrugResponse/ -x "*.DS_Store"
echo ""

# 4. Target Disease Association (~2.6 GB)
echo "[4/7] Target_Disease_Association/ (~2.6 GB)..."
zip -r "$OUT/Target_Disease_Association.zip" Target_Disease_Association/ -x "*.DS_Store"
echo ""

# 5. DrugTargetMetrics CSVs + index files (~80 MB)
echo "[5/7] DrugTargetMetrics CSVs + indexes (~80 MB)..."
zip "$OUT/DrugTargetMetrics_csvs.zip" \
  DrugTargetMetrics/drug_selectivity_metrics.csv \
  DrugTargetMetrics/drug_umap_clustering.csv \
  DrugTargetMetrics/target_binding_stats.csv \
  DrugTargetMetrics/drug_phase_mapping.csv \
  DrugTargetMetrics/target_centric_pan/drug_index.json \
  DrugTargetMetrics/target_centric_pan/target_index.json
echo ""

# 6. DrugTargetMetrics Parquet Part 1: chunks 000-049 (~4.5 GB)
echo "[6/7] DrugTargetMetrics parquet part 1 (chunks 000-049, ~4.5 GB)..."
PART1_FILES=""
for i in $(seq -w 0 49); do
  PART1_FILES="$PART1_FILES DrugTargetMetrics/target_centric_pan/target_centric_pan_uniprot_chunk_0${i}.parquet"
done
zip "$OUT/DrugTargetMetrics_parquet_part1.zip" $PART1_FILES
echo ""

# 7. DrugTargetMetrics Parquet Part 2: chunks 050-099 (~4.5 GB)
echo "[7/7] DrugTargetMetrics parquet part 2 (chunks 050-099, ~4.5 GB)..."
PART2_FILES=""
for i in $(seq -w 50 99); do
  PART2_FILES="$PART2_FILES DrugTargetMetrics/target_centric_pan/target_centric_pan_uniprot_chunk_0${i}.parquet"
done
zip "$OUT/DrugTargetMetrics_parquet_part2.zip" $PART2_FILES
echo ""

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
echo "  5. Upload all 7 zip files from $OUT/"
echo "  6. Publish → copy DOI"
echo "  7. Update scripts/download_data.py with file URLs"
echo "  8. Update README.md with DOI"
echo "  9. Push updates to GitHub"
