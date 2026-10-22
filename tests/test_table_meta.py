from __future__ import annotations

from spectrascholar.rag.table_meta import query_signals, table_boost, table_meta


def test_table_meta_detects_dataset_metric_ratio_and_patch():
    text = (
        "TABLE VI\n"
        "COMPARISON RESULTS ON INDIAN PINES DATASET\n"
        "OA(%) 99.19 98.93\n"
        "AA(%) 98.93 97.00\n"
        "20% training samples; patch 7x7\n"
    )
    meta = table_meta(text)
    assert meta.has_table is True
    assert "Indian Pines" in meta.datasets
    assert {"OA", "AA"} <= meta.metrics
    assert "20%" in meta.ratios
    assert "7x7" in meta.patches


def test_query_signals_and_table_boost_are_deterministic():
    query = "WFCG 在 Indian Pines、1% 训练比例下的 OA 是多少？"
    signals = query_signals(query)
    assert signals.has_table is True
    assert "Indian Pines" in signals.datasets
    assert "1%" in signals.ratios
    assert "OA" in signals.metrics

    matching_page = "TABLE VI\nINDIAN PINES DATASET\nOA(%) 90.86\n1% training"
    other_page = "This page discusses unrelated image classification figures."
    assert table_boost(query, matching_page) > 0.3
    assert table_boost(query, other_page) == 0.0


def test_non_table_query_has_no_boost():
    assert table_boost("what is the main contribution?", "TABLE I OA 99.0") == 0.0
