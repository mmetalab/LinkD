#!/bin/bash
# Prepare data archives for Figshare upload.
# Run from project root: bash scripts/prepare_figshare.sh
#
# Figshare free tier limit: 5 GB per file, 20 GB total per public dataset.
# DrugTargetMetrics (~13 GB) is split into 5 parts to stay under the limit.
#
# Total output: 9 zip files (~16 GB)

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
echo "[1/9] Database/ (~28 MB)..."
zip -r "$OUT/Database.zip" Database/ -x "*.DS_Store"
echo ""

# 2. EHR Results (~58 MB)
echo "[2/9] EHR_Results/ (~58 MB)..."
zip -r "$OUT/EHR_Results.zip" EHR_Results/ -x "*.DS_Store"
echo ""

# 3. Drug Response (~79 MB)
echo "[3/9] DrugResponse/ (~79 MB)..."
zip -r "$OUT/DrugResponse.zip" DrugResponse/ -x "*.DS_Store"
echo ""

# 4. Target Disease Association (~2.6 GB)
echo "[4/9] Target_Disease_Association/ (~2.6 GB)..."
zip -r "$OUT/Target_Disease_Association.zip" Target_Disease_Association/ -x "*.DS_Store"
echo ""

# 5. DrugTargetMetrics CSVs + index files (~80 MB)
echo "[5/9] DrugTargetMetrics CSVs + indexes (~80 MB)..."
zip "$OUT/DrugTargetMetrics_csvs.zip" \
  DrugTargetMetrics/drug_selectivity_metrics.csv \
  DrugTargetMetrics/drug_umap_clustering.csv \
  DrugTargetMetrics/target_binding_stats.csv \
  DrugTargetMetrics/drug_phase_mapping.csv \
  DrugTargetMetrics/target_centric_pan/drug_index.json \
  DrugTargetMetrics/target_centric_pan/target_index.json
echo ""

# 6. Parquet Part 1: chunks 000-024 (~3.3 GB)
echo "[6/9] DrugTargetMetrics parquet part 1 (chunks 000-024, ~3.3 GB)..."
FILES=""
for i in $(seq -w 0 24); do
  FILES="$FILES DrugTargetMetrics/target_centric_pan/target_centric_pan_uniprot_chunk_0${i}.parquet"
done
zip "$OUT/DrugTargetMetrics_parquet_part1.zip" $FILES
echo ""

# 7. Parquet Part 2: chunks 025-049 (~3.3 GB)
echo "[7/9] DrugTargetMetrics parquet part 2 (chunks 025-049, ~3.3 GB)..."
FILES=""
for i in $(seq -w 25 49); do
  FILES="$FILES DrugTargetMetrics/target_centric_pan/target_centric_pan_uniprot_chunk_0${i}.parquet"
done
zip "$OUT/DrugTargetMetrics_parquet_part2.zip" $FILES
echo ""

# 8. Parquet Part 3: chunks 050-074 (~3.3 GB)
echo "[8/9] DrugTargetMetrics parquet part 3 (chunks 050-074, ~3.3 GB)..."
FILES=""
for i in $(seq -w 50 74); do
  FILES="$FILES DrugTargetMetrics/target_centric_pan/target_centric_pan_uniprot_chunk_0${i}.parquet"
done
zip "$OUT/DrugTargetMetrics_parquet_part3.zip" $FILES
echo ""

# 9. Parquet Part 4: chunks 075-099 (~3.3 GB)
echo "[9/9] DrugTargetMetrics parquet part 4 (chunks 075-099, ~3.3 GB)..."
FILES=""
for i in $(seq -w 75 99); do
  FILES="$FILES DrugTargetMetrics/target_centric_pan/target_centric_pan_uniprot_chunk_0${i}.parquet"
done
zip "$OUT/DrugTargetMetrics_parquet_part4.zip" $FILES
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
echo "  5. Upload all 9 zip files from $OUT/"
echo "  6. Publish → copy DOI"
echo "  7. Update scripts/download_data.py with file URLs"
echo "  8. Update README.md with DOI"
echo "  9. Push updates to GitHub"
