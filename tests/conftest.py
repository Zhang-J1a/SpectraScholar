"""Shared test fixtures.

Important: the environment is configured *before* importing the application so
that tests never touch the developer's real workspace or database.
"""
from __future__ import annotations

import os
import shutil
import sys
import time
import types
from pathlib import Path

import pytest

_TEST_WORKSPACE = Path(__file__).resolve().parent.parent / ".test-workspace"
shutil.rmtree(_TEST_WORKSPACE, ignore_errors=True)
_TEST_WORKSPACE.mkdir(parents=True, exist_ok=True)
os.environ["WORKSPACE_DIR"] = str(_TEST_WORKSPACE)
os.environ.update(
    {
        "RESEARCH_BACKEND": "demo",
        "EXTRACTOR_BACKEND": "heuristic",
        "EMBEDDING_BACKEND": "hash",
        "ANSWER_BACKEND": "extractive",
        "RATE_LIMIT_PER_MINUTE": "0",
        "API_KEY": "",
        "MAX_UPLOAD_MB": "2",
        "MAX_PDF_PAGES": "20",
        "MAX_EXTRACT_CHARS": "60000",
        "RESEARCH_TIMEOUT_SECONDS": "10",
        "RESEARCH_PHASE_TIMEOUT_SECONDS": "5",
        "RESEARCH_MAX_ATTEMPTS": "2",
        "RETRY_BACKOFF_SECONDS": "0",
        "WORKFLOW_STEP_TIMEOUT_SECONDS": "30",
        "WORKFLOW_MAX_RETRIES": "1",
        "LOG_LEVEL": "WARNING",
    }
)
for key in ("OPENAI_API_KEY", "TAVILY_API_KEY", "OPENAI_BASE_URL"):
    os.environ.pop(key, None)

from fastapi.testclient import TestClient

from spectrascholar.main import app
from spectrascholar.rag.service import reset_index
from spectrascholar.settings import settings
from spectrascholar.store import init_store


def _rmtree_with_retry(path: Path) -> None:
    if not path.exists():
        return
    for _ in range(10):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            time.sleep(0.1)
    shutil.rmtree(path, ignore_errors=True)


def _clean_workspace() -> None:
    for path in (settings.paper_dir, settings.report_dir, settings.kb_dir, settings.config_dir):
        _rmtree_with_retry(path)
        path.mkdir(parents=True, exist_ok=True)
    for path in (settings.db_path, Path(str(settings.db_path) + "-wal"), Path(str(settings.db_path) + "-shm")):
        for _ in range(10):
            try:
                path.unlink(missing_ok=True)
                break
            except PermissionError:
                time.sleep(0.1)
    init_store()
    reset_index()


@pytest.fixture(autouse=True)
def clean_state():
    _clean_workspace()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(clean_state):
    return clean_state


# ---------------------------------------------------------------------------
# Minimal, valid PDF generator (ASCII text only)
# ---------------------------------------------------------------------------
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


def make_pdf(path: Path, pages: list[list[str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(make_pdf_bytes(pages))
    return path


def upload_pdf(client: TestClient, filename: str, pages: list[list[str]]) -> dict:
    payload = make_pdf_bytes(pages)
    response = client.post(
        "/api/v1/documents",
        files={"file": (filename, payload, "application/pdf")},
    )
    assert response.status_code in {200, 201}, response.text
    return response.json()


def upload_table_pdf(client: TestClient, filename: str = "table_paper.pdf") -> dict:
    response = client.post(
        "/api/v1/documents",
        files={"file": (filename, make_table_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code in {200, 201}, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Fixture documents used by extraction / comparison / workflow tests
# ---------------------------------------------------------------------------
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


@pytest.fixture
def two_papers(client):
    first = upload_pdf(client, "dynamic_gnn.pdf", DYNAMIC_GNN_PAGES)
    second = upload_pdf(client, "hybridsn.pdf", HYBRIDSN_PAGES)
    return first, second


# ---------------------------------------------------------------------------
# Fake GPT Researcher module
# ---------------------------------------------------------------------------
class FakeGPTResearcher:
    instances: list[FakeGPTResearcher] = []

    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)
        config_path = kwargs.get("config_path")
        self.config_data = None
        if config_path and Path(config_path).is_file():
            import json

            self.config_data = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.context = kwargs.pop("_context", "A fake research context about hyperspectral GNNs.")
        self.report = kwargs.pop("_report", "# Fake report\n\nA verifiable fake report for tests.")
        self.delay = 0.0
        self.fail_on = None
        FakeGPTResearcher.instances.append(self)

    async def conduct_research(self):
        if self.fail_on == "conduct":
            raise RuntimeError("fake search failure")
        if self.delay:
            import asyncio

            await asyncio.sleep(self.delay)
        return self.context

    async def write_report(self):
        if self.fail_on == "write":
            raise RuntimeError("fake report failure")
        return self.report

    def get_costs(self):
        return 0.01


def install_fake_gptr(
    monkeypatch,
    *,
    report: str | None = None,
    context: str | None = None,
    delay: float = 0.0,
    fail_on: str | None = None,
):
    module = types.ModuleType("gpt_researcher")

    class Researcher(FakeGPTResearcher):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if report is not None:
                self.report = report
            if context is not None:
                self.context = context
            self.delay = delay
            self.fail_on = fail_on

    module.GPTResearcher = Researcher
    monkeypatch.setitem(sys.modules, "gpt_researcher", module)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    FakeGPTResearcher.instances = []
    return module
