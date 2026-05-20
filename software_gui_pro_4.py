# -*- coding: utf-8 -*-
"""Bibliometria PRO — Tkinter GUI shell (v16.2). Core logic: bibliometric_analysis.core.pipeline."""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from bibliometric_analysis.core.config import PipelineConfig
from bibliometric_analysis.core.pipeline import run_online_pipeline
from bibliometric_analysis.export.excel import export_excel as _export_excel_pkg
from bibliometric_analysis.gui.launchers import (
    launch_network_viz,
    launch_openalex_converter,
    launch_openalex_query,
    launch_streamlit_app,
    run_enrichment,
)
from bibliometric_analysis.metrics.mncs import add_cf_and_pp_global as _add_cf_and_pp_global_pkg
from bibliometric_analysis.openalex.client import get_default_client, http_get
from bibliometric_analysis.openalex.client import set_max_concurrent as _client_set_max_concurrent
from bibliometric_analysis.parsers.common import doi_pat  # noqa: F401 — legacy re-export
from metrics.percentiles import compute_ppx  # noqa: F401 — legacy re-export

# --- optional deps (import tests check these) ---
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

try:
    from pyvis.network import Network
    HAS_PYVIS = True
except Exception:
    Network = None
    HAS_PYVIS = False

# --- legacy module-level constants (compatibility) ---
SLEEP = 0.2
BASE = "https://api.openalex.org"
TIES_POLICY = "closed_ge"
USE_LOCAL_BASELINE = True
BASELINE_BOOTSTRAP_B = 800
BASELINE_ERROR_TARGET_PCT = 5.0
SHOW_PROGRESS = False

_oa_client = get_default_client()
HTTP_CACHE = _oa_client.cache
MAX_CONCURRENT = 6


def _tqdm(iterable=None, **kwargs):
    try:
        from tqdm.auto import tqdm as _tqdm_auto
    except Exception:
        _tqdm_auto = None
    if (not SHOW_PROGRESS) or (_tqdm_auto is None):
        class _NullIter:
            def __init__(self, it):
                self.it = it
            def __iter__(self):
                return iter(self.it) if self.it is not None else iter(())
        return _NullIter(iterable)
    return _tqdm_auto(iterable, **kwargs) if iterable is not None else _tqdm_auto(**kwargs)


def set_max_concurrent(n: int):
    global MAX_CONCURRENT
    MAX_CONCURRENT = max(1, int(n))
    _client_set_max_concurrent(n)


# --- thin compatibility wrappers ---
def add_cf_and_pp_global(df: pd.DataFrame, globals_df: pd.DataFrame) -> pd.DataFrame:
    return _add_cf_and_pp_global_pkg(df, globals_df, ties_policy=TIES_POLICY)


def export_excel(records, edges, net_metrics, s_int, s_frac, globals_df, runmeta, out_path):
    return _export_excel_pkg(records, edges, net_metrics, s_int, s_frac, globals_df, runmeta, out_path)


def export_network_html(G, out_html: str, directed: bool = True, notebook: bool = False):
    if not HAS_PYVIS:
        return
    net = Network(height="850px", width="100%", directed=directed, notebook=notebook, bgcolor="#ffffff")
    for n, attrs in G.nodes(data=True):
        net.add_node(str(n), label=attrs.get("label") or str(n), size=attrs.get("size") or 8,
                     color=attrs.get("color"), title=attrs.get("title") or "")
    for u, v, attrs in G.edges(data=True):
        net.add_edge(str(u), str(v), value=attrs.get("weight") or 1)
    net.toggle_physics(True)
    net.show(out_html)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bibliometria PRO — c₀/PP globais, autocitações, retratações, Leiden")
        self.geometry("1180x760")
        self.resizable(True, True)
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Fonte:").grid(row=0, column=0, sticky="w")
        self.fonte_var = tk.StringVar(value="wos")
        ttk.Radiobutton(frm, text="WoS (.txt)", variable=self.fonte_var, value="wos").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(frm, text="Scopus/OpenAlex (.csv)", variable=self.fonte_var, value="scopus").grid(row=0, column=2, sticky="w")

        ttk.Label(frm, text="Ficheiro:").grid(row=1, column=0, sticky="w")
        self.path_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.path_var, width=70).grid(row=1, column=1, columnspan=2, sticky="we", padx=6)
        ttk.Button(frm, text="Escolher…", command=self.choose_file).grid(row=1, column=3, sticky="w")

        self.expand_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Expandir citantes (janela k/autocitações)", variable=self.expand_var).grid(row=2, column=1, sticky="w", pady=2)

        ttk.Label(frm, text="Email (OpenAlex mailto):").grid(row=3, column=0, sticky="w")
        self.mailto_var = tk.StringVar(value="nome@instituicao.pt")
        ttk.Entry(frm, textvariable=self.mailto_var, width=40).grid(row=3, column=1, sticky="w")

        ttk.Label(frm, text="Concept level:").grid(row=4, column=0, sticky="w")
        self.level_var = tk.IntVar(value=1)
        ttk.Spinbox(frm, from_=0, to=5, textvariable=self.level_var, width=6).grid(row=4, column=1, sticky="w")
        ttk.Label(frm, text="Peso multi-campo:").grid(row=4, column=2, sticky="e")
        self.level_weight_var = tk.StringVar(value="equal")
        ttk.Combobox(frm, textvariable=self.level_weight_var, values=["equal", "score"], width=10, state="readonly").grid(row=4, column=3, sticky="w")

        ttk.Label(frm, text="Janela k (anos):").grid(row=5, column=0, sticky="w")
        self.k_var = tk.IntVar(value=5)
        ttk.Spinbox(frm, from_=0, to=10, textvariable=self.k_var, width=6).grid(row=5, column=1, sticky="w")
        ttk.Label(frm, text="Tipos (OpenAlex):").grid(row=5, column=2, sticky="e")
        self.types_var = tk.StringVar(value="journal-article,review-article")
        ttk.Entry(frm, textvariable=self.types_var, width=36).grid(row=5, column=3, sticky="w")

        self.selfcit_off = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Excluir autocitações", variable=self.selfcit_off).grid(row=6, column=1, sticky="w")
        self.retract_off = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Excluir retratações", variable=self.retract_off).grid(row=6, column=2, sticky="w")

        self.prefer_hist = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Usar histograma/group_by OpenAlex", variable=self.prefer_hist).grid(row=7, column=1, sticky="w")
        ttk.Label(frm, text="Limite páginas fallback:").grid(row=7, column=2, sticky="e")
        self.max_pages_full = tk.IntVar(value=9999)
        ttk.Spinbox(frm, from_=100, to=99999, textvariable=self.max_pages_full, width=10).grid(row=7, column=3, sticky="w")

        ttk.Label(frm, text="Comunidades:").grid(row=8, column=0, sticky="w")
        self.comm_algo_var = tk.StringVar(value="auto")
        ttk.Combobox(frm, textvariable=self.comm_algo_var, values=["auto", "leiden", "louvain", "greedy"], width=10, state="readonly").grid(row=8, column=1, sticky="w")
        ttk.Label(frm, text="γ:").grid(row=8, column=2, sticky="e")
        self.gamma_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(frm, from_=0.2, to=3.0, increment=0.1, textvariable=self.gamma_var, width=8).grid(row=8, column=3, sticky="w")
        ttk.Label(frm, text="Seed:").grid(row=8, column=4, sticky="e")
        self.seed_var = tk.IntVar(value=42)
        ttk.Spinbox(frm, from_=0, to=9999, textvariable=self.seed_var, width=8).grid(row=8, column=5, sticky="w")
        ttk.Label(frm, text="n_runs (Leiden):").grid(row=9, column=2, sticky="e")
        self.nruns_var = tk.IntVar(value=5)
        ttk.Spinbox(frm, from_=3, to=20, textvariable=self.nruns_var, width=8).grid(row=9, column=3, sticky="w")

        ttk.Label(frm, text="B (bootstrap MNCS):").grid(row=9, column=0, sticky="w")
        self.boot_B_var = tk.IntVar(value=1000)
        ttk.Spinbox(frm, from_=200, to=20000, increment=200, textvariable=self.boot_B_var, width=10).grid(row=9, column=1, sticky="w")

        ttk.Label(frm, text="Concorrência:").grid(row=10, column=0, sticky="w")
        self.conc_var = tk.IntVar(value=6)
        ttk.Spinbox(frm, from_=1, to=16, textvariable=self.conc_var, width=10).grid(row=10, column=1, sticky="w")
        ttk.Label(frm, text="Perfil OpenAlex:").grid(row=10, column=2, sticky="e")
        self.mode_var = tk.StringVar(value="equilibrio (5/1000)")
        ttk.Combobox(frm, textvariable=self.mode_var, values=["rapido (3/500)", "equilibrio (5/1000)", "rigor (10/2000)"], width=18, state="readonly").grid(row=10, column=3, sticky="w")

        self.var_show_progress = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Mostrar progresso", variable=self.var_show_progress).grid(row=11, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.btn_exec = ttk.Button(frm, text="Executar", command=self.run)
        self.btn_exec.grid(row=11, column=2, sticky="e", pady=10)
        ttk.Button(frm, text="Sair", command=self.destroy).grid(row=11, column=3, sticky="e", pady=10)

        tools = ttk.LabelFrame(frm, text="Ferramentas (abrir noutra janela)", padding=6)
        tools.grid(row=13, column=0, columnspan=6, sticky="ew", pady=(0, 6))
        ttk.Button(tools, text="Dashboard Streamlit", command=self.open_dashboard).pack(side="left", padx=4)
        ttk.Button(tools, text="Pipeline Streamlit", command=self.open_streamlit_pipeline).pack(side="left", padx=4)
        ttk.Button(tools, text="Consulta OpenAlex", command=self.open_openalex_query).pack(side="left", padx=4)
        ttk.Button(tools, text="Visualizar rede", command=self.open_network_viz).pack(side="left", padx=4)
        ttk.Button(tools, text="Converter OpenAlex→Scopus", command=self.open_converter).pack(side="left", padx=4)
        ttk.Button(tools, text="Enriquecer autores…", command=self.run_enrichment_tool).pack(side="left", padx=4)

        self.log = tk.Text(frm, height=18, width=150)
        self.log.grid(row=12, column=0, columnspan=6, pady=6, sticky="nsew")
        self.log.config(state="disabled")
        for i in range(6):
            frm.grid_columnconfigure(i, weight=1)
        frm.grid_rowconfigure(12, weight=1)

    def choose_file(self):
        types = [("Web of Science TXT", "*.txt"), ("Todos", "*.*")] if self.fonte_var.get() == "wos" else [("CSV", "*.csv"), ("Todos", "*.*")]
        p = filedialog.askopenfilename(title="Escolha o ficheiro", filetypes=types)
        if p:
            self.path_var.set(p)

    def append_log(self, msg: str):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")
        self.update_idletasks()

    def ui_call(self, func, *args, **kwargs):
        self.after(0, lambda: func(*args, **kwargs))

    def append_log_threadsafe(self, msg: str):
        self.ui_call(self.append_log, msg)

    def _launch_tool(self, label: str, launcher):
        try:
            launcher()
            self.append_log(f"[{label}] Janela iniciada.")
        except FileNotFoundError as e:
            messagebox.showerror("Erro", str(e))
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir {label}:\n{e}")

    def open_dashboard(self):
        self._launch_tool("Dashboard", lambda: launch_streamlit_app("app_dashboard.py"))

    def open_streamlit_pipeline(self):
        self._launch_tool("Pipeline Streamlit", lambda: launch_streamlit_app("streamlit_pipeline_runner.py"))

    def open_openalex_query(self):
        self._launch_tool("Consulta OpenAlex", launch_openalex_query)

    def open_network_viz(self):
        self._launch_tool("Visualizar rede", launch_network_viz)

    def open_converter(self):
        self._launch_tool("Converter OpenAlex", launch_openalex_converter)

    def run_enrichment_tool(self):
        mailto = self.mailto_var.get().strip()
        if not mailto or "@" not in mailto:
            messagebox.showerror("Erro", "Indique um email OpenAlex válido (campo mailto).")
            return
        xlsx = filedialog.askopenfilename(
            title="Excel exportado pelo núcleo (Records+Metrics)",
            filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
        )
        if not xlsx:
            return

        def _worker():
            try:
                run_enrichment(xlsx, mailto, int(self.conc_var.get()), log=self.append_log_threadsafe)
                self.ui_call(messagebox.showinfo, "Concluído", "Enrichment guardado:\nauthors.csv\ninstitutions.csv\nauthorships.csv")
            except Exception as e:
                self.ui_call(messagebox.showerror, "Erro", str(e))
                self.append_log_threadsafe(f"[enrichment ERRO] {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _pipeline_config(self) -> PipelineConfig:
        types = {t.strip() for t in (self.types_var.get() or "").split(",") if t.strip()}
        return PipelineConfig(
            ties_policy=TIES_POLICY,
            use_local_baseline=USE_LOCAL_BASELINE,
            k_window=int(self.k_var.get()),
            drop_self_citations=self.selfcit_off.get(),
            drop_retracted=self.retract_off.get(),
            concept_level=int(self.level_var.get()),
            prefer_histogram=self.prefer_hist.get(),
            max_pages=int(self.max_pages_full.get()),
            types_filter=types or None,
            baseline_bootstrap_b=int(self.boot_B_var.get()),
        )

    def run(self):
        global SHOW_PROGRESS
        SHOW_PROGRESS = bool(self.var_show_progress.get())
        if getattr(self, "_is_running", False):
            self.append_log_threadsafe("AVISO: execução em curso.")
            return
        self._is_running = True
        try:
            self.btn_exec.config(state="disabled")
            path = self.path_var.get().strip()
            if not path or not Path(path).exists():
                messagebox.showerror("Erro", "Selecione um ficheiro válido.")
                self._is_running = False
                self.btn_exec.config(state="normal")
                return

            mailto = self.mailto_var.get().strip()
            set_max_concurrent(int(self.conc_var.get()))
            mode = self.mode_var.get()
            if "rigor" in mode:
                workers = max(2, MAX_CONCURRENT // 3)
            elif "rapido" in mode:
                workers = max(2, MAX_CONCURRENT // 2)
            else:
                workers = max(2, MAX_CONCURRENT // 2)

            cfg = self._pipeline_config()
            source = "wos" if self.fonte_var.get() == "wos" else "auto"

            def _worker():
                try:
                    run_online_pipeline(
                        path,
                        config=cfg,
                        source=source,
                        mailto=mailto,
                        expand=self.expand_var.get(),
                        http_get_fn=http_get,
                        max_concurrent=MAX_CONCURRENT,
                        sleep=SLEEP,
                        base_url=BASE,
                        progress_iter=_tqdm if SHOW_PROGRESS else None,
                        comm_algo=self.comm_algo_var.get(),
                        comm_gamma=float(self.gamma_var.get()),
                        comm_seed=int(self.seed_var.get()),
                        comm_n_runs=int(self.nruns_var.get()),
                        level_weight=self.level_weight_var.get(),
                        global_workers=workers,
                        log=self.append_log_threadsafe,
                    )
                    out = Path(path).with_name(f"{Path(path).stem}_metrics_pro.xlsx")
                    self.ui_call(messagebox.showinfo, "Concluído", f"Ficheiro gerado:\n{out}")
                except Exception as e:
                    self.ui_call(messagebox.showerror, "Erro", str(e))
                    self.append_log_threadsafe(f"[ERRO] {e}")
                finally:
                    def _release():
                        self._is_running = False
                        try:
                            self.btn_exec.config(state="normal")
                        except Exception:
                            pass
                    self.ui_call(_release)

            threading.Thread(target=_worker, daemon=True).start()
        except Exception:
            self._is_running = False
            self.btn_exec.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
