from __future__ import annotations

from tests.conftest import upload_pdf


def test_compare_two_papers_generates_comparable_metrics_and_markdown(client, two_papers):
    first, second = two_papers
    response = client.post(
        "/api/v1/compare",
        json={"document_ids": [first["document_id"], second["document_id"]], "mode": "heuristic"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["papers"]) == 2
    assert result["comparison_id"]
    assert result["extraction_mode"] == "heuristic"
    assert "可比性声明" in result["markdown"]
    assert "证据附录" in result["markdown"]

    oa_rows = [row for row in result["metric_rows"] if row["metric"] == "OA"]
    assert len(oa_rows) == 2
    assert all(row["dataset"] == "Indian Pines" for row in oa_rows)
    assert all(row["train_ratio"] == "10%" for row in oa_rows)
    assert all(row["patch_size"] == "9x9" for row in oa_rows)
    assert all(row["comparable"] for row in oa_rows)
    assert {row["rank_in_group"] for row in oa_rows} == {1, 2}

    # Kappa only exists in one paper, so it must not be ranked.
    kappa = next(row for row in result["metric_rows"] if row["metric"] == "Kappa")
    assert kappa["comparable"] is False
    assert kappa["rank_in_group"] is None

    comparison_id = result["comparison_id"]
    detail = client.get(f"/api/v1/compare/{comparison_id}")
    assert detail.status_code == 200
    assert detail.json()["comparison_id"] == comparison_id

    markdown = client.get(f"/api/v1/compare/{comparison_id}.md")
    assert markdown.status_code == 200
    assert "多论文结构化对比报告" in markdown.text
    assert "不可比项与风险提示" in markdown.text

    history = client.get("/api/v1/compare").json()
    assert any(item["comparison_id"] == comparison_id for item in history)


def test_compare_marks_missing_conditions_as_not_comparable(client):
    first = upload_pdf(
        client,
        "a.pdf",
        [["Paper A", "On Indian Pines, the overall accuracy (OA) is 91.2%."]],
    )
    second = upload_pdf(
        client,
        "b.pdf",
        [["Paper B", "On Indian Pines, the overall accuracy (OA) is 92.3%."]],
    )
    result = client.post(
        "/api/v1/compare",
        json={"document_ids": [first["document_id"], second["document_id"]]},
    ).json()
    oa_rows = [row for row in result["metric_rows"] if row["metric"] == "OA"]
    assert oa_rows
    assert all(row["comparable"] is False for row in oa_rows)
    assert all("训练样本比例" in (row["reason"] or "") for row in oa_rows)
    issues = {issue["code"] for issue in result["comparability_issues"]}
    assert "train_ratio_missing" in issues


def test_compare_validation_and_errors(client, two_papers):
    first, _ = two_papers
    one = client.post("/api/v1/compare", json={"document_ids": [first["document_id"]]})
    assert one.status_code == 422

    duplicate = client.post(
        "/api/v1/compare",
        json={"document_ids": [first["document_id"], first["document_id"]]},
    )
    assert duplicate.status_code == 422

    missing = client.post(
        "/api/v1/compare",
        json={"document_ids": [first["document_id"], "does-not-exist"]},
    )
    assert missing.status_code == 404

    assert client.get("/api/v1/compare/does-not-exist").status_code == 404
    assert client.get("/api/v1/compare/does-not-exist.md").status_code == 404


def test_llm_compare_without_key_returns_503(client, two_papers, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    first, second = two_papers
    response = client.post(
        "/api/v1/compare",
        json={
            "document_ids": [first["document_id"], second["document_id"]],
            "mode": "llm",
        },
    )
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
