# -*- coding: utf-8 -*-
import argparse, math
from pathlib import Path
import pandas as pd
from pyvis.network import Network
import networkx as nx

def _minmax_scale(series, lo=5, hi=30):
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    a, b = float(s.min()), float(s.max())
    if not math.isfinite(a) or not math.isfinite(b) or a == b:
        return pd.Series([ (lo+hi)/2.0 ] * len(s), index=s.index)
    return lo + (s - a) * (hi - lo) / (b - a)

def compute_network_metrics(records: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas básicas por nó a partir de Records+Metrics (nodes) e Edges:
      - deg_in, deg_out, deg, betweenness, pagerank, community (greedy modularity em grafo não dirigido).
    Aceita colunas de arestas: (citer_idx,cited_idx) OU (source,target) OU (from,to) OU (src,dst).
    Ignora self-loops e arestas para nós inexistentes em 'records'.
    """
    cols = ["idx","deg_in","deg_out","deg","betweenness","pagerank","community"]

    # Sem nós → devolve vazio estruturado
    if records is None or records.empty or "idx" not in records.columns:
        return pd.DataFrame(columns=cols)

    # Mapear colunas de arestas
    src_dst_pairs = [("citer_idx","cited_idx"), ("source","target"), ("from","to"), ("src","dst")]
    src_col = dst_col = None
    if edges is not None and not edges.empty:
        for a,b in src_dst_pairs:
            if a in edges.columns and b in edges.columns:
                src_col, dst_col = a, b
                break

    # Nós
    nodes = pd.to_numeric(records["idx"], errors="coerce").dropna().astype(int).unique().tolist()
    G = nx.DiGraph()
    G.add_nodes_from(nodes)

    # Arestas (se houver)
    if edges is not None and not edges.empty and src_col and dst_col:
        e = edges[[src_col, dst_col]].copy()
        e[src_col] = pd.to_numeric(e[src_col], errors="coerce")
        e[dst_col] = pd.to_numeric(e[dst_col], errors="coerce")
        e = e.dropna().astype(int)
        node_set = set(nodes)
        e = e[(e[src_col].isin(node_set)) & (e[dst_col].isin(node_set)) & (e[src_col] != e[dst_col])]
        if not e.empty:
            G.add_edges_from(e.itertuples(index=False, name=None))

    # Grafo sem arestas? Tratar métricas de forma estável
    has_edges = G.number_of_edges() > 0
    n_nodes = max(1, G.number_of_nodes())

    # Graus
    deg_in = dict(G.in_degree())
    deg_out = dict(G.out_degree())
    deg_total = {n: deg_in.get(n,0) + deg_out.get(n,0) for n in G.nodes()}

    # Betweenness
    try:
        bet = nx.betweenness_centrality(G, normalized=True) if has_edges else {n: 0.0 for n in G.nodes()}
    except Exception:
        bet = {n: float("nan") for n in G.nodes()}

    # PageRank
    try:
        if has_edges:
            pr = nx.pagerank(G, alpha=0.85, max_iter=200)
        else:
            pr = {n: 1.0 / n_nodes for n in G.nodes()}
    except Exception:
        pr = {n: float("nan") for n in G.nodes()}

    # Comunidades (projeção não dirigida + greedy modularity)
    try:
        if has_edges:
            from networkx.algorithms.community import greedy_modularity_communities
            UG = G.to_undirected()
            comms = list(greedy_modularity_communities(UG))
            node2comm = {}
            for cid, comm in enumerate(comms, start=1):
                for u in comm:
                    node2comm[u] = cid
            for n in G.nodes():
                node2comm.setdefault(n, 0)
        else:
            node2comm = {n: 0 for n in G.nodes()}
    except Exception:
        node2comm = {n: 0 for n in G.nodes()}

    # Saída
    out = pd.DataFrame({"idx": list(G.nodes())})
    out["deg_in"] = out["idx"].map(deg_in).fillna(0).astype(int)
    out["deg_out"] = out["idx"].map(deg_out).fillna(0).astype(int)
    out["deg"] = out["idx"].map(deg_total).fillna(0).astype(int)
    out["betweenness"] = out["idx"].map(bet).astype(float)
    out["pagerank"] = out["idx"].map(pr).astype(float)
    out["community"] = out["idx"].map(node2comm).fillna(0).astype(int)
    return out


def build_network(xlsx_path: str, out_html: str, size_metric: str = "pagerank", min_degree: int = 1, color_by: str = "community"):
    rec = pd.read_excel(xlsx_path, sheet_name="Records+Metrics")
    edges = pd.read_excel(xlsx_path, sheet_name="Edges")
    try: netm = pd.read_excel(xlsx_path, sheet_name="Network Metrics")
    except Exception: netm = pd.DataFrame()

    for c in ("idx","year","cited_by_count","cf","CP","deg","pagerank","betweenness","community"):
        if c in rec.columns:
            rec[c] = pd.to_numeric(rec[c], errors="coerce")

    if netm is None or netm.empty:
        netm = compute_network_metrics(rec, edges)
        netm["community"] = -1
        netm["community_label"] = None
        netm["algo"] = "NA"; netm["gamma"] = None; netm["stability_nmi"] = None

    rec = rec.merge(netm, on="idx", how="left")

    keep_ids = set(rec.loc[rec["deg"] >= int(min_degree), "idx"].tolist())
    e2 = edges[edges["citer_idx"].isin(keep_ids) & edges["cited_idx"].isin(keep_ids)].copy()
    rec2 = rec[rec["idx"].isin(keep_ids)].copy()

    if size_metric.lower() == "degree": size_metric = "deg"
    if size_metric not in rec2.columns:
        for cand in ("CP","cf","cited_by_count","deg","pagerank","betweenness"):
            if cand in rec2.columns: size_metric = cand; break
    sizes = _minmax_scale(rec2[size_metric], lo=5, hi=30)

    if color_by not in rec2.columns:
        color_by = "community"
    groups = pd.Categorical(rec2.get(color_by, pd.Series([None]*len(rec2))).fillna("NA"))
    palette = {d: f"hsl({int(360*i/max(1,len(groups.categories)))},70%,60%)" for i,d in enumerate(groups.categories)}

    # ---------------------------------------------------------
    # SUBSTITUA O BLOCO ANTIGO POR ESTE NO viz_network_plus.py
    # ---------------------------------------------------------

    def _mk_title(row):
        """
        Constrói o texto 'tooltip' (título hover) de forma segura,
        tratando valores vazios ou NaN para evitar erros.
        """
        parts = []

        # 1. Título (com proteção contra não-strings)
        title = row.get("title")
        if pd.notna(title) and title:
            parts.append(str(title))

        # 2. Metadados (Ano | Domínio) - A PARTE CRÍTICA
        meta_parts = []

        # Ano seguro
        year = row.get("year")
        if pd.notna(year):
            meta_parts.append(str(year).replace(".0", "")) # Remove decimal

        # Domínio seguro (Correção do erro 'float found')
        domain = row.get("domain_label")
        if pd.notna(domain) and domain:
            meta_parts.append(str(domain))

        if meta_parts:
            parts.append(" | ".join(meta_parts))

        # 3. Métricas (CF, PageRank) - com try/except por segurança
        if pd.notna(row.get("cf")):
            try:
                parts.append(f"cf={float(row['cf']):.2f}")
            except: pass

        if pd.notna(row.get("pagerank")):
            try:
                parts.append(f"PR={float(row['pagerank']):.4f}")
            except: pass

        # 4. Comunidade e Algoritmos
        if pd.notna(row.get("community")):
            try:
                cl = row.get("community_label")
                cl_str = f" ({cl})" if pd.notna(cl) and cl else ""
                parts.append(f"comm={int(row['community'])}{cl_str}")
            except: pass

        # Retorna HTML seguro
        return "<br/>".join(parts)

    # --- FIM DA FUNÇÃO, AGORA O LOOP DE CONSTRUÇÃO DA REDE ---

    # Inicialização da rede
    net = Network(height="820px", width="100%", directed=True, bgcolor="#ffffff", notebook=False)
    net.barnes_hut()

    # Loop Robusto para criar Nós
    for i, (_, row) in enumerate(rec2.iterrows()):
        idx = int(row["idx"])

        # Tratamento seguro do Label (evita erro se título for vazio)
        raw_title = row.get("title")
        if pd.notna(raw_title) and isinstance(raw_title, str):
            # Corta o título se for muito longo
            label = (raw_title[:80] + "…") if len(raw_title) > 80 else raw_title
        else:
            label = str(idx) # Usa o ID numérico se não houver título

        # Cor do nó
        colkey = row.get(color_by)
        if pd.isna(colkey): colkey = "NA"
        color = palette.get(colkey, "#97c2fc")

        # Tamanho seguro
        try:
            node_size = float(sizes.iloc[i])
        except:
            node_size = 5.0

        # Adiciona o nó usando a função segura _mk_title
        net.add_node(n_id=idx, label=label, title=_mk_title(row), value=node_size, color=color)

    # Loop para criar Arestas (Edges)
    for _, r in e2.iterrows():
        try:
            net.add_edge(int(r["citer_idx"]), int(r["cited_idx"]), arrows="to")
        except: 
            pass # Ignora arestas quebradas se houver dados corrompidos

    # Opções visuais do PyVis
    net.set_options("""
    {
      "nodes": { "shape": "dot" },
      "edges": { "arrows": { "to": { "enabled": true, "scaleFactor": 0.6 } }, "color": { "opacity": 0.35 } },
      "physics": { "stabilization": true, "barnesHut": { "gravitationalConstant": -20000 } },
      "interaction": { "tooltipDelay": 200, "hover": true, "navigationButtons": true }
    }
    """)

    # Gravar o ficheiro HTML final
    out = Path(out_html or "network_plus.html")
    net.write_html(out.as_posix(), notebook=False, open_browser=False)
    print(f"✔ Rede gravada em: {out}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", help="Excel gerado (Records+Metrics, Edges)")
    ap.add_argument("--out", default="network_plus.html", help="HTML de saída")
    ap.add_argument("--size", default="pagerank", help="Tamanho: CP|cited_by_count|cf|degree|pagerank|betweenness")
    ap.add_argument("--min_degree", type=int, default=1, help="Filtro: grau mínimo do nó")
    ap.add_argument("--color_by", default="community", help="Cor: community|community_label|domain_label")
    args = ap.parse_args()
    build_network(args.xlsx, args.out, args.size, args.min_degree, args.color_by)

if __name__ == "__main__":
    main()
