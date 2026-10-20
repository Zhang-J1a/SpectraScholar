from __future__ import annotations

from tests.conftest import make_pdf_bytes, upload_pdf


def test_upload_list_read_and_delete(client):
    info = upload_pdf(
        client,
        "paper.pdf",
        [["A First Page Title", "Authors: A B", "Some text about Indian Pines."], ["Second page"]],
    )
    assert info["filename"] == "paper.pdf"
    assert info["page_count"] == 2
    assert info["sha256"]

    documents = client.get("/api/v1/documents").json()
    assert len(documents) == 1
    assert documents[0]["document_id"] == info["document_id"]

    pages = client.get(f"/api/v1/documents/{info['document_id']}/pages").json()
    assert pages["page_count"] == 2
    assert "Indian Pines" in pages["pages"][0]["text"]

    page = client.get(f"/api/v1/documents/{info['document_id']}/pages/1")
    assert page.status_code == 200
    assert page.json()["page"] == 1
    assert client.get(f"/api/v1/documents/{info['document_id']}/pages/99").status_code == 404

    deleted = client.delete(f"/api/v1/documents/{info['document_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == info["document_id"]
    assert client.get("/api/v1/documents").json() == []


def test_duplicate_upload_is_deduplicated(client):
    first = upload_pdf(client, "same.pdf", [["Same content"]])
    second = client.post(
        "/api/v1/documents",
        files={"file": ("other-name.pdf", make_pdf_bytes([["Same content"]]), "application/pdf")},
    )
    assert second.status_code == 200
    assert second.json()["document_id"] == first["document_id"]
    assert len(client.get("/api/v1/documents").json()) == 1


def test_invalid_upload_cases(client):
    not_pdf = client.post(
        "/api/v1/documents",
        files={"file": ("evil.pdf", b"definitely not a pdf", "application/pdf")},
    )
    assert not_pdf.status_code == 415

    wrong_extension = client.post(
        "/api/v1/documents",
        files={"file": ("paper.txt", make_pdf_bytes([["text"]]), "text/plain")},
    )
    assert wrong_extension.status_code == 415

    empty = client.post("/api/v1/documents", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert empty.status_code == 400

    oversized = client.post(
        "/api/v1/documents",
        files={"file": ("big.pdf", b"%PDF-" + b"x" * (2 * 1024 * 1024 + 10), "application/pdf")},
    )
    assert oversized.status_code == 413


def test_filename_is_sanitized(client):
    info = upload_pdf(client, "..\\..\\evil.pdf", [["Path traversal test"]])
    assert info["filename"] == "evil.pdf"
    assert "/" not in info["filename"]
    assert "\\" not in info["filename"]


def test_missing_document_endpoints(client):
    assert client.get("/api/v1/documents/nope").status_code == 404
    assert client.get("/api/v1/documents/nope/pages").status_code == 404
    assert client.delete("/api/v1/documents/nope").status_code == 404
