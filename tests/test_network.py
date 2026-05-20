import pandas as pd

from bibliometric_analysis.network.build import build_edges_by_doi
from bibliometric_analysis.network.metrics import community_detection, compute_basic_metrics


def test_build_edges():
    records = pd.DataFrame(
        {
            "idx": [0, 1],
            "doi": ["10.1000/a", "10.1000/b"],
            "ref_dois": [["10.1000/b"], []],
        }
    )
    edges = build_edges_by_doi(records)
    assert len(edges) == 1
    assert edges.iloc[0]["citer_idx"] == 0
    assert edges.iloc[0]["cited_idx"] == 1


def test_pagerank_finite():
    records = pd.DataFrame({"idx": [0, 1], "doi": ["a", "b"], "ref_dois": [["b"], []], "domain_label": ["X", "Y"]})
    edges = build_edges_by_doi(records)
    net = community_detection(records, edges, "greedy", 1.0, 42)
    assert net["pagerank"].notna().all()


def test_disconnected_graph():
    records = pd.DataFrame({"idx": [0, 1], "doi": ["a", "b"], "ref_dois": [[], []], "domain_label": ["X", "Y"]})
    edges = build_edges_by_doi(records)
    assert edges.empty
    net = compute_basic_metrics(records, edges)
    assert len(net) == 2


def test_self_loop_ignored():
    records = pd.DataFrame({"idx": [0], "doi": ["10.1000/a"], "ref_dois": [["10.1000/a"]]})
    edges = build_edges_by_doi(records)
    assert edges.empty
