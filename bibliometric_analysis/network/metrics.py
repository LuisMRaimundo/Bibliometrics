"""Per-node network metrics (degree, PageRank, betweenness, communities)."""

from __future__ import annotations

import math

import networkx as nx
import numpy as np
import pandas as pd

try:
    import community as community_louvain
except Exception:
    community_louvain = None

try:
    import igraph as ig
    import leidenalg
except Exception:
    ig = None
    leidenalg = None


def compute_basic_metrics(records: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    """Compute deg_in, deg_out, deg, betweenness, pagerank, community."""
    cols = ["idx", "deg_in", "deg_out", "deg", "betweenness", "pagerank", "community"]

    if records is None or records.empty or "idx" not in records.columns:
        return pd.DataFrame(columns=cols)

    src_dst_pairs = [
        ("citer_idx", "cited_idx"),
        ("source", "target"),
        ("from", "to"),
        ("src", "dst"),
    ]
    src_col = dst_col = None
    if edges is not None and not edges.empty:
        for a, b in src_dst_pairs:
            if a in edges.columns and b in edges.columns:
                src_col, dst_col = a, b
                break

    nodes = pd.to_numeric(records["idx"], errors="coerce").dropna().astype(int).unique().tolist()
    g = nx.DiGraph()
    g.add_nodes_from(nodes)

    if edges is not None and not edges.empty and src_col and dst_col:
        e = edges[[src_col, dst_col]].copy()
        e[src_col] = pd.to_numeric(e[src_col], errors="coerce")
        e[dst_col] = pd.to_numeric(e[dst_col], errors="coerce")
        e = e.dropna().astype(int)
        node_set = set(nodes)
        e = e[(e[src_col].isin(node_set)) & (e[dst_col].isin(node_set)) & (e[src_col] != e[dst_col])]
        if not e.empty:
            g.add_edges_from(e.itertuples(index=False, name=None))

    has_edges = g.number_of_edges() > 0
    n_nodes = max(1, g.number_of_nodes())

    deg_in = dict(g.in_degree())
    deg_out = dict(g.out_degree())
    deg_total = {n: deg_in.get(n, 0) + deg_out.get(n, 0) for n in g.nodes()}

    try:
        bet = nx.betweenness_centrality(g, normalized=True) if has_edges else {n: 0.0 for n in g.nodes()}
    except Exception:
        bet = {n: float("nan") for n in g.nodes()}

    try:
        if has_edges:
            pr = nx.pagerank(g, alpha=0.85, max_iter=200)
        else:
            pr = {n: 1.0 / n_nodes for n in g.nodes()}
    except Exception:
        pr = {n: float("nan") for n in g.nodes()}

    try:
        if has_edges:
            from networkx.algorithms.community import greedy_modularity_communities

            ug = g.to_undirected()
            comms = list(greedy_modularity_communities(ug))
            node2comm = {}
            for cid, comm in enumerate(comms, start=1):
                for u in comm:
                    node2comm[u] = cid
            for n in g.nodes():
                node2comm.setdefault(n, 0)
        else:
            node2comm = {n: 0 for n in g.nodes()}
    except Exception:
        node2comm = {n: 0 for n in g.nodes()}

    out = pd.DataFrame({"idx": list(g.nodes())})
    out["deg_in"] = out["idx"].map(deg_in).fillna(0).astype(int)
    out["deg_out"] = out["idx"].map(deg_out).fillna(0).astype(int)
    out["deg"] = out["idx"].map(deg_total).fillna(0).astype(int)
    out["betweenness"] = out["idx"].map(bet).astype(float)
    out["pagerank"] = out["idx"].map(pr).astype(float)
    out["community"] = out["idx"].map(node2comm).fillna(0).astype(int)
    return out


def community_detection(
    records: pd.DataFrame,
    edges: pd.DataFrame,
    algo: str,
    gamma: float,
    seed: int,
    n_runs_stability: int = 5,
) -> pd.DataFrame:
    """Full community detection with Leiden/Louvain/Greedy fallback (matches legacy GUI)."""
    if edges.empty:
        return pd.DataFrame(
            columns=[
                "idx",
                "deg_in",
                "deg_out",
                "deg",
                "pagerank",
                "betweenness",
                "community",
                "community_label",
                "algo",
                "gamma",
                "stability_nmi",
            ]
        )
    g = nx.DiGraph()
    nodes = records["idx"].astype(int).tolist()
    g.add_nodes_from(nodes)
    for _, r in edges.iterrows():
        g.add_edge(int(r["citer_idx"]), int(r["cited_idx"]))
    deg_in = dict(g.in_degree())
    deg_out = dict(g.out_degree())
    deg_total = {n: deg_in.get(n, 0) + deg_out.get(n, 0) for n in g.nodes()}
    try:
        pr = nx.pagerank(g, alpha=0.85, max_iter=200)
    except Exception:
        pr = {n: np.nan for n in g.nodes()}
    try:
        bet = nx.betweenness_centrality(g, normalized=True)
    except Exception:
        bet = {n: np.nan for n in g.nodes()}
    ug = g.to_undirected()

    def majority_label(community_nodes):
        sub = records.set_index("idx").loc[list(community_nodes)]
        lab = sub["domain_label"].dropna()
        return lab.value_counts().idxmax() if not lab.empty else None

    algo_used = "greedy"
    comm_map: dict = {}
    stability = np.nan
    if algo == "leiden" and ig is not None and leidenalg is not None:
        idx_to_pos = {idx: i for i, idx in enumerate(nodes)}
        edges_ig = [(idx_to_pos[int(u)], idx_to_pos[int(v)]) for u, v in g.edges()]
        graph = ig.Graph(n=len(nodes), edges=edges_ig, directed=False)
        parts = []
        rng = np.random.default_rng(seed)
        for _ in range(n_runs_stability):
            part = leidenalg.find_partition(
                graph,
                leidenalg.RBConfigurationVertexPartition,
                resolution_parameter=float(gamma),
                seed=int(rng.integers(0, 1_000_000_000)),
            )
            parts.append(part.membership)
        memb = parts[0]
        algo_used = "leiden"
        try:
            nmis = [ig.compare_communities(memb, p, method="NMI") for p in parts[1:]]
            stability = float(np.mean(nmis)) if nmis else np.nan
        except Exception:
            stability = np.nan
        comm_map = {nodes[i]: int(memb[i]) for i in range(len(nodes))}
    elif algo == "louvain" and community_louvain is not None:
        part = community_louvain.best_partition(ug, resolution=float(gamma), random_state=int(seed))
        comm_map = {int(n): int(c) for n, c in part.items()}
        algo_used = "louvain"
    else:
        comms = list(nx.algorithms.community.greedy_modularity_communities(ug))
        for cid, comm in enumerate(comms):
            for n in comm:
                comm_map[int(n)] = int(cid)
        algo_used = "greedy"

    rev: dict = {}
    for n, c in comm_map.items():
        rev.setdefault(c, set()).add(n)
    comm_label = {c: majority_label(members) for c, members in rev.items()}

    return pd.DataFrame(
        {
            "idx": list(g.nodes()),
            "deg_in": [deg_in.get(n, 0) for n in g.nodes()],
            "deg_out": [deg_out.get(n, 0) for n in g.nodes()],
            "deg": [deg_total.get(n, 0) for n in g.nodes()],
            "pagerank": [pr.get(n, np.nan) for n in g.nodes()],
            "betweenness": [bet.get(n, np.nan) for n in g.nodes()],
            "community": [comm_map.get(n, -1) for n in g.nodes()],
            "community_label": [comm_label.get(comm_map.get(n, -1)) for n in g.nodes()],
            "algo": algo_used,
            "gamma": float(gamma),
            "stability_nmi": stability,
        }
    )


def minmax_scale(series, lo=5, hi=30):
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    a, b = float(s.min()), float(s.max())
    if not math.isfinite(a) or not math.isfinite(b) or a == b:
        return pd.Series([(lo + hi) / 2.0] * len(s), index=s.index)
    return lo + (s - a) * (hi - lo) / (b - a)
