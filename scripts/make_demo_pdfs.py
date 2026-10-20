"""Generate the synthetic demo PDFs used by the fixture evaluation.

They are intentionally tiny and contain no real paper content. Two are prose
papers; the third is a ruled OA/AA/Kappa table used to demo table extraction.

Usage:
    python scripts/make_demo_pdfs.py --out demo_assets
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import (  # noqa: E402
    DYNAMIC_GNN_PAGES,
    HYBRIDSN_PAGES,
    make_pdf_bytes,
    make_table_pdf_bytes,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "demo_assets")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, pages in (("dynamic_gnn.pdf", DYNAMIC_GNN_PAGES), ("hybridsn.pdf", HYBRIDSN_PAGES)):
        path = args.out / name
        path.write_bytes(make_pdf_bytes(pages))
        print(f"wrote {path}")
    table_path = args.out / "table_paper.pdf"
    table_path.write_bytes(make_table_pdf_bytes())
    print(f"wrote {table_path}")
    print("这些是合成夹具 PDF，不是真实论文；上传后可用于功能演示。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
