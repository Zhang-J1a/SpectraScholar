from spectrascholar.evidence import quote_on_page, verify_evidence, verify_metric, heuristic_extract
from spectrascholar.schemas import Evidence, MetricEvidence


def test_exact_quote_verified():
    p = ["We evaluated on Indian Pines dataset with an OA of 98.4%. "]
    good = Evidence(value="Indian Pines", quote="Indian Pines", page=1)
    assert verify_evidence(good, p).verified is True
    assert verify_evidence(Evidence(value="Indian Pines", quote="Indian Pines", page=2), p) is None


def test_hallucinated_value_is_rejected():
    pages = ["The OA score is 88.5% on this benchmark."]
    fake = MetricEvidence(dataset="Sample", metric="OA", value="99.9%", page=1, quote="The OA score is 88.5%")
    assert verify_metric(fake, pages) is None
    assert not quote_on_page(pages, 1, "The OA score is 99.9%")


def test_heuristic_only_reports_dataset_matches():
    x = heuristic_extract("id1", "paper.pdf", ["An Indian Pines experiment." , "OA=98.2%"])
    assert len(x.datasets) == 1
    assert x.datasets[0].verified
    assert x.metrics == []
