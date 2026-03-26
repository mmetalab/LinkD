"""
Download LinkD Agent data from Figshare.

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

# Configuration — update after Figshare publication
FIGSHARE_ARTICLE_ID = "XXXXXXX"  # TODO: Replace with actual Figshare article ID
FIGSHARE_VERSION = 1

# Individual file downloads (update with actual file IDs after upload)
FIGSHARE_FILES = {
    # "filename.zip": "https://figshare.com/ndownloader/files/FILE_ID"
    # Uncomment and fill after Figshare upload:
    # "Database.zip": "https://figshare.com/ndownloader/files/XXXXXX",
    # "EHR_Results.zip": "https://figshare.com/ndownloader/files/XXXXXX",
    # "DrugResponse.zip": "https://figshare.com/ndownloader/files/XXXXXX",
    # "DrugTargetMetrics.zip": "https://figshare.com/ndownloader/files/XXXXXX",
    # "Target_Disease_Association.zip": "https://figshare.com/ndownloader/files/XXXXXX",
}

# Alternative: download entire article as zip
FIGSHARE_ARTICLE_URL = f"https://figshare.com/ndownloader/articles/{FIGSHARE_ARTICLE_ID}/versions/{FIGSHARE_VERSION}"


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
        print(f"No data found in {data_dir}. Downloading from Figshare...")

    os.makedirs(data_dir, exist_ok=True)

    if FIGSHARE_ARTICLE_ID == "XXXXXXX":
        print("\n" + "=" * 60)
        print("  Figshare article ID not configured yet!")
        print("  To set up:")
        print("  1. Upload data to Figshare")
        print("  2. Update FIGSHARE_ARTICLE_ID in this script")
        print("  3. Or set FIGSHARE_FILES with individual file URLs")
        print("")
        print("  For local development, place data directories in:")
        print(f"  {data_dir.resolve()}/")
        print("=" * 60)
        return

    # Download individual files if configured
    if FIGSHARE_FILES:
        for filename, url in FIGSHARE_FILES.items():
            zip_path = str(data_dir / filename)
            if not Path(zip_path).exists():
                download_file(url, zip_path)
                print(f"  Extracting {filename}...")
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(str(data_dir))
                os.remove(zip_path)
    else:
        # Download entire article
        zip_path = str(data_dir / "linkd_data.zip")
        download_file(FIGSHARE_ARTICLE_URL, zip_path)
        print("  Extracting archive...")
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
