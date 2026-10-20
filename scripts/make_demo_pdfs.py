"""Generate the two synthetic demo PDFs used by the fixture evaluation.

They are intentionally tiny (two pages each) and contain no real paper content.
Use them to exercise upload → compare → workflow → RAG without external data.

Usage:
    python scripts/make_demo_pdfs.py --out demo_assets
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import DYNAMIC_GNN_PAGES, HYBRIDSN_PAGES, make_pdf_bytes  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "demo_assets")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, pages in (("dynamic_gnn.pdf", DYNAMIC_GNN_PAGES), ("hybridsn.pdf", HYBRIDSN_PAGES)):
        path = args.out / name
        path.write_bytes(make_pdf_bytes(pages))
        print(f"wrote {path}")
    print("这些是合成夹具 PDF，不是真实论文；上传后可用于功能演示。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
