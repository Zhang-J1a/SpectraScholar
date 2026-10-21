"""Dependency-free PDF fixtures used by tests and evaluation scripts.

This module has **no environment side effects**, so evaluation scripts can
import it without importing the FastAPI app or touching a workspace.
"""
from __future__ import annotations

DYNAMIC_GNN_PAGES = [
    [
        "Dynamic Graph Neural Networks for Hyperspectral Image Classification",
        "Alice Smith, Bob Lee",
        "IGARSS 2024",
        "Abstract",
        "We propose a dynamic graph method using GCN and KNN graph construction.",
    ],
    [
        "Experiments",
        "On Indian Pines with 10% training samples and patch size 9x9 under random split,",
        "the overall accuracy (OA) is 98.4% and Kappa is 0.977.",
        "The dynamic graph is updated during training.",
    ],
]

HYBRIDSN_PAGES = [
    [
        "HybridSN: Exploring 3D-2D CNN for Hyperspectral Image Classification",
        "Sam Wang, Li Chen",
        "IGARSS 2024",
        "Abstract",
        "We use HybridSN with 3D-CNN and 2D-CNN for spectral-spatial classification.",
    ],
    [
        "Experiments",
        "On Indian Pines with 10% training samples and patch size 9x9 under random split,",
        "HybridSN achieves OA = 97.1% and AA = 96.5%.",
        "We also compare with a static graph baseline using RBF graphs.",
    ],
]


def _escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(page_streams: list[bytes]) -> bytes:
    """Build a valid PDF from one content stream per page."""
    page_numbers = [4 + index * 2 for index in range(len(page_streams))]
    content_numbers = [5 + index * 2 for index in range(len(page_streams))]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Kids [{' '.join(f'{number} 0 R' for number in page_numbers)}]"
            f" /Count {len(page_numbers)} >>"
        ).encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for page_number, content_number, stream in zip(page_numbers, content_numbers, page_streams, strict=True):
        objects[page_number] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_number} 0 R >>"
        ).encode()
        objects[content_number] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )
    header = b"%PDF-1.4\n"
    body = bytearray()
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(header) + len(body)
        body.extend(f"{number} 0 obj\n".encode())
        body.extend(objects[number])
        body.extend(b"\nendobj\n")
    xref_offset = len(header) + len(body)
    size = max(objects) + 1
    xref = bytearray(f"xref\n0 {size}\n".encode())
    xref.extend(b"0000000000 65535 f \n")
    for number in range(1, size):
        xref.extend(f"{offsets.get(number, 0):010d} 00000 n \n".encode())
    trailer = f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    return header + bytes(body) + bytes(xref) + trailer


def _text_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 10 Tf", "72 750 Td"]
    for line in lines:
        commands.append(f"({_escape_pdf(line)}) Tj")
        commands.append("0 -14 Td")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", "replace")


def make_pdf_bytes(pages: list[list[str]]) -> bytes:
    """Create a valid multi-page PDF using only the standard library."""
    return _build_pdf([_text_stream(lines) for lines in pages])


def make_table_pdf_bytes() -> bytes:
    """Create a one-page PDF with a real ruled OA/AA/Kappa table.

    The lines are actual PDF graphics, so pdfplumber's structural table finder
    sees a table rather than just aligned text.
    """
    commands = [
        "0.8 w",
        "BT /F1 11 Tf 60 748 Td "
        "(Table 1: OA on Indian Pines with 10% training samples, patch size 9x9, random split.) Tj ET",
    ]
    for y in (720, 696, 672, 648):
        commands.append(f"50 {y} m 440 {y} l S")
    for x in (50, 230, 300, 370, 440):
        commands.append(f"{x} 648 m {x} 720 l S")
    cells = [
        ("Method", 56, 700),
        ("OA", 236, 700),
        ("AA", 306, 700),
        ("Kappa", 376, 700),
        ("HybridSN", 56, 676),
        ("98.4", 236, 676),
        ("97.8", 306, 676),
        ("0.976", 376, 676),
        ("GCN", 56, 652),
        ("97.1", 236, 652),
        ("96.5", 306, 652),
        ("0.965", 376, 652),
    ]
    for text, x, y in cells:
        commands.append(f"BT /F1 10 Tf {x} {y} Td ({_escape_pdf(text)}) Tj ET")
    return _build_pdf(["\n".join(commands).encode("latin-1", "replace")])
