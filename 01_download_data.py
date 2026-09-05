"""Step 1: Data Acquisition — one-time download of the real Zomato restaurant dataset.

Requires Kaggle API credentials: place kaggle.json at ~/.kaggle/kaggle.json,
or set KAGGLE_USERNAME and KAGGLE_KEY environment variables.
"""
import shutil
from pathlib import Path

import kagglehub

DATA_DIR = Path(__file__).parent / "data"
TARGET_FILE = DATA_DIR / "raw_restaurants.csv"


def main():
    if TARGET_FILE.exists():
        print(f"Already downloaded: {TARGET_FILE}")
        return

    DATA_DIR.mkdir(exist_ok=True)
    dataset_path = Path(kagglehub.dataset_download("rajeshrampure/zomato-dataset"))
    print(f"Downloaded to kagglehub cache: {dataset_path}")

    csv_files = list(dataset_path.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV file found in {dataset_path}")

    shutil.copy(csv_files[0], TARGET_FILE)
    print(f"Copied to {TARGET_FILE}")


if __name__ == "__main__":
    main()
