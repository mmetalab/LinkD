"""
Download LinkD data from Zenodo.

Usage:
    python scripts/download_data.py

Respects DATABASE_DIR environment variable for target directory.
Skips download if data already exists.
"""

import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# Configuration — update after Zenodo publication
ZENODO_RECORD_ID = "XXXXXXX"  # TODO: Replace with actual Zenodo record ID

# Individual file downloads (update with actual URLs after upload)
# Format: "filename.zip": "https://zenodo.org/records/RECORD_ID/files/filename.zip?download=1"
ZENODO_FILES = {
    # Uncomment and fill after Zenodo upload:
    # "Database.zip": "https://zenodo.org/records/XXXXXXX/files/Database.zip?download=1",
    # "EHR_Results.zip": "https://zenodo.org/records/XXXXXXX/files/EHR_Results.zip?download=1",
    # "DrugResponse.zip": "https://zenodo.org/records/XXXXXXX/files/DrugResponse.zip?download=1",
    # "Target_Disease_Association.zip": "https://zenodo.org/records/XXXXXXX/files/Target_Disease_Association.zip?download=1",
    # "DrugTargetMetrics_csvs.zip": "https://zenodo.org/records/XXXXXXX/files/DrugTargetMetrics_csvs.zip?download=1",
    # "DrugTargetMetrics_parquet_part1.zip": "https://zenodo.org/records/XXXXXXX/files/DrugTargetMetrics_parquet_part1.zip?download=1",
    # "DrugTargetMetrics_parquet_part2.zip": "https://zenodo.org/records/XXXXXXX/files/DrugTargetMetrics_parquet_part2.zip?download=1",
    # ... (parts 3-10)
}


def download_file(url: str, dest: str):
    """Download a file with progress."""
    print(f"  Downloading {dest}...")

    def report(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\r  {mb:.1f}/{total_mb:.1f} MB ({pct}%)")
            sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, reporthook=report)
    print()


def main():
    data_dir = Path(os.getenv("DATABASE_DIR", "data"))

    # Check if data already exists
    required_dirs = ["Database", "EHR_Results", "DrugResponse", "DrugTargetMetrics", "Target_Disease_Association"]
    existing = [d for d in required_dirs if (data_dir / d).exists()]

    if len(existing) == len(required_dirs):
        print(f"All data directories found in {data_dir}. Skipping download.")
        return

    if existing:
        print(f"Found {len(existing)}/{len(required_dirs)} directories. Downloading missing data...")
    else:
        print(f"No data found in {data_dir}. Downloading from Zenodo...")

    os.makedirs(data_dir, exist_ok=True)

    if ZENODO_RECORD_ID == "XXXXXXX":
        print("\n" + "=" * 60)
        print("  Zenodo record ID not configured yet!")
        print("  To set up:")
        print("  1. Upload data to Zenodo")
        print("  2. Update ZENODO_RECORD_ID in this script")
        print("  3. Uncomment ZENODO_FILES with download URLs")
        print("")
        print("  For local development, place data directories in:")
        print(f"  {data_dir.resolve()}/")
        print("=" * 60)
        return

    if not ZENODO_FILES:
        print("No Zenodo file URLs configured. Update ZENODO_FILES dict.")
        return

    # Download and extract each file
    for filename, url in ZENODO_FILES.items():
        zip_path = str(data_dir / filename)
        if not Path(zip_path).exists():
            download_file(url, zip_path)
        print(f"  Extracting {filename}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(str(data_dir))
        os.remove(zip_path)

    print(f"\nData download complete. Contents of {data_dir}:")
    for item in sorted(data_dir.iterdir()):
        if item.is_dir():
            size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
            print(f"  {item.name}/ ({size / (1024*1024):.1f} MB)")


if __name__ == "__main__":
    main()
