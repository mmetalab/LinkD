#!/bin/bash
# Prepare data archives for Figshare upload.
# Run from project root: bash scripts/prepare_figshare.sh
#
# Creates zip files in figshare_upload/ directory.
# Total size: ~16 GB
# Figshare free tier: 20 GB per public dataset

set -e
cd "$(dirname "$0")/.."

OUT="figshare_upload"
mkdir -p "$OUT"

echo "============================================"
echo "  LinkD: Preparing Figshare Data Archives"
echo "============================================"
echo ""

# 1. Database (small)
echo "[1/5] Database/ (~28 MB)..."
zip -r "$OUT/Database.zip" Database/ -x "*.DS_Store"
echo ""

# 2. EHR Results
echo "[2/5] EHR_Results/ (~58 MB)..."
zip -r "$OUT/EHR_Results.zip" EHR_Results/ -x "*.DS_Store"
echo ""

# 3. Drug Response
echo "[3/5] DrugResponse/ (~79 MB)..."
zip -r "$OUT/DrugResponse.zip" DrugResponse/ -x "*.DS_Store"
echo ""

# 4. Target Disease Association (large)
echo "[4/5] Target_Disease_Association/ (~2.6 GB)..."
zip -r "$OUT/Target_Disease_Association.zip" Target_Disease_Association/ -x "*.DS_Store"
echo ""

# 5. DrugTargetMetrics (largest — exclude .pt files)
echo "[5/5] DrugTargetMetrics/ (~13 GB, excluding .pt files)..."
zip -r "$OUT/DrugTargetMetrics.zip" DrugTargetMetrics/ -x "*.pt" "*.DS_Store"
echo ""

# Summary
echo "============================================"
echo "  Archives ready in $OUT/"
echo "============================================"
ls -lh "$OUT/"
echo ""
echo "Total size:"
du -sh "$OUT/"
echo ""
echo "Next steps:"
echo "  1. Go to https://figshare.com → 'Create a new item'"
echo "  2. Title: 'LinkD: Drug-Target-Disease Database'"
echo "  3. Category: Bioinformatics"
echo "  4. License: CC BY 4.0"
echo "  5. Upload all 5 zip files from $OUT/"
echo "  6. Publish → copy DOI"
echo "  7. Update scripts/download_data.py with file URLs"
echo "  8. Update README.md with DOI"
