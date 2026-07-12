"""Download and safely extract the public Olist Brazilian E-Commerce dataset."""

from __future__ import annotations

import argparse
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "external" / "olist"
DATASET_URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
EXPECTED_FILES = {
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--archive", type=Path, help="Use an existing downloaded zip file")
    return parser.parse_args()


def safe_extract(archive: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        available = {Path(name).name for name in source.namelist() if not name.endswith("/")}
        missing = EXPECTED_FILES - available
        if missing:
            raise ValueError(f"Olist archive is missing files: {sorted(missing)}")
        for member in source.infolist():
            filename = Path(member.filename).name
            if filename not in EXPECTED_FILES:
                continue
            target = output_dir / filename
            with source.open(member) as input_file, target.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
            content = target.read_bytes()
            if content.startswith(b"\xef\xbb\xbf"):
                target.write_bytes(content[3:])


def main() -> None:
    args = parse_args()
    if args.archive:
        archive = args.archive
        if not archive.exists():
            raise FileNotFoundError(archive)
        safe_extract(archive, args.output_dir)
    else:
        with tempfile.NamedTemporaryFile(suffix=".zip") as temporary:
            with urllib.request.urlopen(DATASET_URL, timeout=120) as response:
                shutil.copyfileobj(response, temporary)
            temporary.flush()
            safe_extract(Path(temporary.name), args.output_dir)
    print(f"Extracted {len(EXPECTED_FILES)} Olist CSV files to {args.output_dir}")


if __name__ == "__main__":
    main()
