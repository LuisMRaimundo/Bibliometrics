# -*- coding: utf-8 -*-
"""
viz_network_tk.py — Visualizador de redes (PyVis) com GUI Tkinter.
- Escolhe um Excel exportado pelo núcleo (folhas: 'Records+Metrics' e 'Edges')
- Define parâmetros (tamanho, min_degree, cor)
- Gera HTML interativo e permite abrir no browser.

Requisitos:
  pip install pandas networkx pyvis openpyxl xlsxwriter
"""

from __future__ import annotations
import os, math, tempfile, threading, webbrowser, io
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd
import networkx as nx
from pyvis.network import Network

# ================== Utilitários base ==================

def _minmax_scale(series, lo=5, hi=30):
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    a, b = float(s.min()), float(s.max())
    if not math.isfinite(a) or not math.isfinite(b) or a == b:
        return pd.Series([(lo + hi) / 2.0] * len(s), index=s.index)
    return lo + (s - a) * (hi - lo) / (b - a)

def _get_sheet(xls: pd.ExcelFile, *candidates: str) -> pd.DataFrame | None:
    """Obter folha por nomes candidatos; tenta também normalização (lower/sem espaços)."""
    names = set(xls.sheet_names)
    for name in candidates:
        if name in names:
            return xls.parse(name)
    canon = {n.lower().replace(" ", ""): n for n in xls.sheet_names}
    for name in candidates:
        key = name.lower().replace(" ", "")
        if key in canon:
            return xls.parse(canon[key])
    return None

# ================== Métricas de rede ==================

def compute_network_metrics(records: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    """
    Métricas por nó a partir de Records+Metrics (nós) e Edges (arestas):
      deg_in, deg_out, deg, betweenness, pagerank, community (greedy modularity no grafo não dirigido).
    Aceita arestas: (citer_idx,cited_idx) OU (source,target) OU (from,to) OU (src,dst).
    Ignora self-loops e nós fora de 'records'.
    """
    cols = ["idx","deg_in","deg_out","deg","betweenness","pagerank","community"]
    if records is None or records.empty or "idx" not in records.columns:
        return pd.DataFrame(columns=cols)

    # mapear colunas de arestas
    src_dst_pairs = [("citer_idx","cited_idx"), ("source","target"), ("from","to"), ("src","dst")]
    src_col = dst_col = None
    if edges is not None and not edges.empty:
        for a, b in src_dst_pairs:
            if a in edges.columns and b in edges.columns:
                src_col, dst_col = a, b
                break

    nodes = pd.to_numeric(records["idx"], errors="coerce").dropna().astype(int).unique().tolist()
    G = nx.DiGraph()
    G.add_nodes_from(nodes)

    if edges is not None and not edges.empty and src_col and dst_col:
        e = edges[[src_col, dst_col]].copy()
        e[src_col] = pd.to_numeric(e[src_col], errors="coerce")
        e[dst_col] = pd.to_numeric(e[dst_col], errors="coerce")
        e = e.dropna().astype(int)
        node_set = set(nodes)
        e = e[(e[src_col].isin(node_set)) & (e[dst_col].isin(node_set)) & (e[src_col] != e[dst_col])]
        if not e.empty:
            G.add_edges_from(e.itertuples(index=False, name=None))

    has_edges = G.number_of_edges() > 0
    n_nodes = max(1, G.number_of_nodes())

    deg_in = dict(G.in_degree()); deg_out = dict(G.out_degree())
    deg_total = {n: deg_in.get(n, 0) + deg_out.get(n, 0) for n in G.nodes()}

    try:
        bet = nx.betweenness_centrality(G, normalized=True) if has_edges else {n: 0.0 for n in G.nodes()}
    except Exception:
        bet = {n: float("nan") for n in G.nodes()}

    try:
        pr = nx.pagerank(G, alpha=0.85, max_iter=200) if has_edges else {n: 1.0 / n_nodes for n in G.nodes()}
    except Exception:
        pr = {n: float("nan") for n in G.nodes()}

    # comunidades em grafo não dirigido
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

    out = pd.DataFrame({"idx": list(G.nodes())})
    out["deg_in"] = out["idx"].map(deg_in).fillna(0).astype(int)
    out["deg_out"] = out["idx"].map(deg_out).fillna(0).astype(int)
    out["deg"] = out["idx"].map(deg_total).fillna(0).astype(int)
    out["betweenness"] = out["idx"].map(bet).astype(float)
    out["pagerank"] = out["idx"].map(pr).astype(float)
    out["community"] = out["idx"].map(node2comm).fillna(0).astype(int)
    return out

# ================== Construção / export ==================

def build_network(xlsx_path: str, out_html: str,
                  size_metric: str = "pagerank",
                  min_degree: int = 1,
                  color_by: str = "community") -> str:
    xls = pd.ExcelFile(xlsx_path)
    rec = _get_sheet(xls, "Records+Metrics", "Records + Metrics", "Records & Metrics", "RecordsMetrics")
    if rec is None or rec.empty:
        raise RuntimeError("Folha 'Records+Metrics' não encontrada no Excel.")

    edges = _get_sheet(xls, "Edges")
    if edges is None:
        edges = pd.DataFrame(columns=["citer_idx", "cited_idx"])

    try:
        netm = _get_sheet(xls, "Network Metrics", "NetworkMetrics")
    except Exception:
        netm = pd.DataFrame()

    # coerções básicas
    for c in ("idx","year","cited_by_count","cf","CP","deg","pagerank","betweenness","community"):
        if c in rec.columns:
            rec[c] = pd.to_numeric(rec[c], errors="coerce")

    # métricas (se necessário)
    if netm is None or netm.empty or "idx" not in netm.columns:
        netm = compute_network_metrics(rec, edges)
        netm["community"] = netm["community"].fillna(0).astype(int)
        netm["community_label"] = None
        netm["algo"] = "NA"; netm["gamma"] = None; netm["stability_nmi"] = None

    rec = rec.merge(netm, on="idx", how="left")

    keep_ids = set(rec.loc[rec["deg"] >= int(min_degree), "idx"].dropna().astype(int).tolist())
    # nomes possíveis de arestas
    src_dst = ("citer_idx","cited_idx")
    if edges is not None and not edges.empty:
        for a,b in (("citer_idx","cited_idx"), ("source","target"), ("from","to"), ("src","dst")):
            if a in edges.columns and b in edges.columns:
                src_dst = (a,b); break
    e2 = edges[edges[src_dst[0]].isin(keep_ids) & edges[src_dst[1]].isin(keep_ids)].copy()
    rec2 = rec[rec["idx"].isin(keep_ids)].copy()

    if size_metric.lower() == "degree":
        size_metric = "deg"
    if size_metric not in rec2.columns:
        for cand in ("CP","cf","cited_by_count","deg","pagerank","betweenness"):
            if cand in rec2.columns:
                size_metric = cand; break
    sizes = _minmax_scale(rec2[size_metric], lo=5, hi=30)

    if color_by not in rec2.columns:
        color_by = "community"
    groups = pd.Categorical(rec2.get(color_by, pd.Series([None]*len(rec2))).fillna("NA"))
    palette = {d: f"hsl({int(360*i/max(1,len(groups.categories)))},70%,60%)" for i,d in enumerate(groups.categories)}

    def _mk_title(row):
        parts = []
        ttl = row.get("title")
        if isinstance(ttl, str) and ttl:
            parts.append(ttl)
        meta = " | ".join([p for p in (str(row.get("year")) if pd.notna(row.get("year")) else "", row.get("domain_label") or "") if p])
        if meta: parts.append(meta)
        if pd.notna(row.get("cf")): parts.append(f"cf={float(row['cf']):.2f}")
        if pd.notna(row.get("pagerank")): parts.append(f"PR={float(row['pagerank']):.4f}")
        if pd.notna(row.get("community")):
            cl = row.get("community_label")
            parts.append(f"comm={int(row['community'])}{(' ('+str(cl)+')') if cl else ''}")
        algo = row.get("algo")
        if isinstance(algo, str):
            parts.append(f"algo={algo}; γ={row.get('gamma')}; NMI={row.get('stability_nmi')}")
        return "<br/>".join(parts)

    net = Network(height="820px", width="100%", directed=True, bgcolor="#ffffff", notebook=False)
    net.barnes_hut()

    for i, (_, row) in enumerate(rec2.iterrows()):
        idx = int(row["idx"])
        label = (row["title"][:80] + "…") if isinstance(row.get("title"), str) and len(row["title"]) > 80 else (row.get("title") or str(idx))
        colkey = row.get(color_by, "NA")
        color = palette.get(colkey, "#97c2fc")
        net.add_node(n_id=idx, label=label, title=_mk_title(row), value=float(sizes.iloc[i]), color=color)

    for _, r in e2.iterrows():
        net.add_edge(int(r[src_dst[0]]), int(r[src_dst[1]]), arrows="to")

    net.set_options("""
{
  "nodes": { "shape": "dot" },
  "edges": { "arrows": { "to": { "enabled": true, "scaleFactor": 0.6 } }, "color": { "opacity": 0.35 } },
  "physics": { "stabilization": true, "barnesHut": { "gravitationalConstant": -20000 } },
  "interaction": { "tooltipDelay": 200, "hover": true, "navigationButtons": true }
}
    """)
    out = Path(out_html or "network_plus.html")
    net.write_html(out.as_posix(), notebook=False, open_browser=False)
    return out.as_posix()

# ================== GUI Tkinter ==================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Network Viz (Tkinter)")
        self.geometry("760x520")
        self.resizable(True, True)

        # Vars
        self.xlsx_path = tk.StringVar()
        self.out_path  = tk.StringVar(value=os.path.join(tempfile.gettempdir(), "network_plus.html"))
        self.size_var  = tk.StringVar(value="pagerank")
        self.min_deg   = tk.IntVar(value=1)
        self.color_var = tk.StringVar(value="community")

        # Layout
        pad = {"padx": 8, "pady": 6}

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True)

        # Excel
        ttk.Label(frm, text="Excel (Records+Metrics, Edges):").grid(row=0, column=0, sticky="w", **pad)
        ent_x = ttk.Entry(frm, textvariable=self.xlsx_path, width=70)
        ent_x.grid(row=0, column=1, sticky="we", **pad)
        ttk.Button(frm, text="Escolher…", command=self.browse_xlsx).grid(row=0, column=2, **pad)

        # Output
        ttk.Label(frm, text="HTML de saída:").grid(row=1, column=0, sticky="w", **pad)
        ent_o = ttk.Entry(frm, textvariable=self.out_path, width=70)
        ent_o.grid(row=1, column=1, sticky="we", **pad)
        ttk.Button(frm, text="Guardar como…", command=self.browse_out).grid(row=1, column=2, **pad)

        # Parâmetros
        ttk.Label(frm, text="Tamanho do nó:").grid(row=2, column=0, sticky="w", **pad)
        cb_size = ttk.Combobox(frm, textvariable=self.size_var, state="readonly",
                               values=["pagerank","degree","deg_in","deg_out","betweenness","CP","cited_by_count","cf"])
        cb_size.grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Grau mínimo:").grid(row=3, column=0, sticky="w", **pad)
        sp_deg = ttk.Spinbox(frm, from_=0, to=100, textvariable=self.min_deg, width=6)
        sp_deg.grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Colorir por:").grid(row=4, column=0, sticky="w", **pad)
        cb_col = ttk.Combobox(frm, textvariable=self.color_var, state="readonly",
                              values=["community","community_label","domain_label"])
        cb_col.grid(row=4, column=1, sticky="w", **pad)

        # Botões ação
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=5, column=0, columnspan=3, sticky="we", **pad)
        self.btn_build = ttk.Button(btn_frame, text="Construir rede", command=self.run_build)
        self.btn_build.pack(side="left", padx=4)
        self.btn_open = ttk.Button(btn_frame, text="Abrir HTML", command=self.open_html, state="disabled")
        self.btn_open.pack(side="left", padx=4)

        # Log
        ttk.Label(frm, text="Log:").grid(row=6, column=0, sticky="w", **pad)
        self.txt = tk.Text(frm, height=14, wrap="word")
        self.txt.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=8, pady=(0,8))
        yscroll = ttk.Scrollbar(frm, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=7, column=3, sticky="ns", pady=(0,8))

        frm.columnconfigure(1, weight=1)  # expandir o campo de caminho
        frm.rowconfigure(7, weight=1)

    def log(self, msg: str):
        self.txt.insert("end", msg.rstrip() + "\n")
        self.txt.see("end")
        self.update_idletasks()

    def browse_xlsx(self):
        path = filedialog.askopenfilename(title="Escolher Excel", filetypes=[("Excel", "*.xlsx")])
        if path:
            self.xlsx_path.set(path)
            # sugestão de out na mesma pasta
            out_guess = os.path.join(os.path.dirname(path), "network_plus.html")
            self.out_path.set(out_guess)

    def browse_out(self):
        path = filedialog.asksaveasfilename(title="Guardar HTML", defaultextension=".html",
                                            initialfile="network_plus.html",
                                            filetypes=[("HTML", "*.html")])
        if path:
            self.out_path.set(path)

    def run_build(self):
        xlsx = self.xlsx_path.get().strip()
        out  = self.out_path.get().strip()
        if not xlsx:
            messagebox.showerror("Erro", "Escolha um ficheiro Excel.")
            return
        if not os.path.exists(xlsx):
            messagebox.showerror("Erro", f"Ficheiro não encontrado:\n{xlsx}")
            return
        size = self.size_var.get().strip()
        color_by = self.color_var.get().strip()
        try:
            min_degree = int(self.min_deg.get())
        except Exception:
            messagebox.showerror("Erro", "Grau mínimo inválido.")
            return

        self.btn_build.config(state="disabled")
        self.btn_open.config(state="disabled")
        self.log(f"Iniciar construção: {os.path.basename(xlsx)}  →  {out}")
        self.log(f"Parâmetros: size={size}, min_degree={min_degree}, color_by={color_by}")

        def _worker():
            try:
                produced = build_network(xlsx, out, size_metric=size, min_degree=min_degree, color_by=color_by)
                self.log(f"✔ Rede gravada em: {produced}")
                self.btn_open.config(state="normal")
                messagebox.showinfo("Concluído", f"Rede gravada em:\n{produced}")
            except Exception as e:
                self.log(f"[ERRO] {e}")
                messagebox.showerror("Falhou", str(e))
            finally:
                self.btn_build.config(state="normal")

        threading.Thread(target=_worker, daemon=True).start()

    def open_html(self):
        out = self.out_path.get().strip()
        if not out or not os.path.exists(out):
            messagebox.showwarning("Aviso", "O ficheiro HTML ainda não existe.")
            return
        webbrowser.open_new_tab(Path(out).as_uri())

# ================== Entry-point ==================

if __name__ == "__main__":
    app = App()
    app.mainloop()
