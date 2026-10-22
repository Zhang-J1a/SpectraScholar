from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def test_research_eval_has_50_valid_labeled_questions():
    payload = json.loads(Path("eval/research_eval.json").read_text(encoding="utf-8"))
    items = payload["items"]
    assert len(items) == 50
    assert len({item["id"] for item in items}) == 50
    assert {item["document_id"] for item in items} == {
        "hybridsn",
        "ssrn",
        "cnn_gat",
    }
    counts = Counter(item["category"] for item in items)
    assert counts["metadata"] >= 10
    assert counts["metric"] >= 20
    assert counts["condition"] >= 8
    for item in items:
        assert item["gold_page"] >= 1
        assert item["gold_answer"]
        assert item["gold_quote"]
