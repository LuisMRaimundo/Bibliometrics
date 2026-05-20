#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
select_texts_gui_v7_intelligent.py

Version 7: Intelligent Excel File and Sheet Selection

Novidades v7:
- Análise automática de ficheiros Excel na pasta
- Seleção inteligente do melhor ficheiro e sheet baseada em métricas de qualidade
- Validação automática de dados antes do processamento
- Recomendações baseadas em múltiplos critérios (completude, qualidade, métricas)
- Integração com excel_analyzer.py para análise de qualidade
"""

import math
import os
import re
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Import intelligent analyzer
from excel_analyzer import ExcelAnalyzer, analyze_excel_folder

# --- CONFIGURAÇÃO DE COLUNAS (mantido do v6) ---
AREA_CANDIDATES = ["domain_label", "domain_id", "community_label", "area", "field", "ASJC", "WC"]
TITLE_CANDIDATES = ["title", "document title", "ti", "titulo"]
DOI_CANDIDATES = ["doi", "doi number", "pr_doi"]
YEAR_CANDIDATES = ["year", "py", "publication year", "date", "ano"]
AUTHOR_CANDIDATES = ["authors", "author_names", "authors_list", "creator", "autores"]

METRIC_COLS = {
    "cf": ["cf", "mncs", "c_f", "field_weighted_citation_impact"],
    "c_use_window": ["c_use_window", "use_window", "usage_window"],
    "c_use": ["c_use", "usage", "cited_by_count"],
    "pagerank": ["pagerank", "pr", "page_rank"],
    "betweenness": ["betweenness", "btw", "centrality"],
}

# --- UTILITÁRIOS (mantido do v6) ---
def pick_col(df: pd.DataFrame, candidates: list) -> str | None:
    cols_lower = {str(c).lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower: return cols_lower[cand.lower()]
    for c in df.columns:
        for cand in candidates:
            if cand.lower() in str(c).lower(): return c
    return None

def normalize_doi(x):
    if pd.isna(x): return ""
    s = str(x).strip().replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
    return s.strip()

def extract_year(x):
    if pd.isna(x): return ""
    m = re.search(r"(19|20|21)\d{2}", str(x))
    return int(m.group(0)) if m else ""

def safe_z_score(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    if s.std(ddof=0) == 0: return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / s.std(ddof=0)

def simplify_area_name(area_name):
    """Simplifica nomes de áreas em macro-áreas."""
    s = str(area_name).lower()
    
    if "physic" in s or "astro" in s: return "Physics & Astronomy"
    if "math" in s or "algebra" in s or "geometry" in s: return "Mathematics"
    if "computer" in s or "computat" in s or "intelligence" in s or "software" in s: return "Computer Science"
    if "bio" in s or "medic" in s or "genet" in s or "clini" in s: return "Biology & Medicine"
    if "chem" in s or "material" in s or "polymer" in s: return "Chemistry & Materials"
    if "engin" in s or "mechan" in s or "electr" in s: return "Engineering"
    if "geo" in s or "earth" in s or "envir" in s: return "Earth & Environmental"
    if "social" in s or "econ" in s or "psych" in s or "educ" in s: return "Social Sciences"
    
    return area_name

# --- LOAD COM SELEÇÃO INTELIGENTE ---
def load_data_intelligent(
    folder_path: str = None,
    xlsx_path: str = None,
    use_network: bool = False,
    simplify_areas: bool = True,
    auto_select: bool = True
) -> pd.DataFrame:
    """
    Carrega dados com seleção inteligente de ficheiro e sheet.
    
    Args:
        folder_path: Pasta para analisar (se auto_select=True)
        xlsx_path: Caminho específico do ficheiro (se fornecido)
        use_network: Usar métricas de rede
        simplify_areas: Simplificar áreas
        auto_select: Selecionar automaticamente o melhor ficheiro
    
    Returns:
        DataFrame com dados carregados
    """
    # Se xlsx_path fornecido, usar diretamente
    if xlsx_path and os.path.exists(xlsx_path):
        return _load_from_file(xlsx_path, use_network, simplify_areas)
    
    # Se folder_path fornecido e auto_select=True, analisar e escolher
    if folder_path and auto_select:
        analyzer = ExcelAnalyzer(folder_path)
        recommendation = analyzer.get_recommendation()
        
        if recommendation['status'] == 'success':
            recommended_file = recommendation['recommended_file']
            recommended_sheet = recommendation['recommended_sheet']
            
            # Carregar do ficheiro recomendado
            return _load_from_file(
                recommended_file,
                use_network,
                simplify_areas,
                sheet_name=recommended_sheet
            )
        else:
            raise ValueError(f"Nenhum ficheiro adequado encontrado: {recommendation['message']}")
    
    raise ValueError("Forneça folder_path ou xlsx_path")

def _load_from_file(
    xlsx_path: str,
    use_network: bool = False,
    simplify_areas: bool = True,
    sheet_name: str = None
) -> pd.DataFrame:
    """Carrega dados de um ficheiro específico."""
    try:
        xls = pd.ExcelFile(xlsx_path)
    except Exception as e:
        raise ValueError(f"Erro ao ler Excel: {e}")

    # Seleção inteligente de sheet
    if sheet_name and sheet_name in xls.sheet_names:
        selected_sheet = sheet_name
    elif "Records+Metrics" in xls.sheet_names:
        selected_sheet = "Records+Metrics"
    elif "Records" in xls.sheet_names:
        selected_sheet = "Records"
    else:
        # Analisar todos os sheets e escolher o melhor
        analyzer = ExcelAnalyzer(os.path.dirname(xlsx_path))
        file_quality = analyzer.analyze_file(xlsx_path)
        if file_quality.best_sheet:
            selected_sheet = file_quality.best_sheet
        else:
            selected_sheet = xls.sheet_names[0]
    
    df = xls.parse(selected_sheet)

    # Merge com Network Metrics se solicitado
    if use_network and "Network Metrics" in xls.sheet_names:
        df_net = xls.parse("Network Metrics")
        idx_col = pick_col(df, ["idx", "id", "eid"])
        idx_net = pick_col(df_net, ["idx", "id", "eid"])
        if idx_col and idx_net:
            net_cols = [c for c in df_net.columns if c not in df.columns and c != idx_net]
            df = df.merge(df_net[[idx_net] + net_cols], left_on=idx_col, right_on=idx_net, how="left")

    # Normalizar métricas
    for std_name, candidates in METRIC_COLS.items():
        found = pick_col(df, candidates)
        df[std_name] = pd.to_numeric(df[found], errors='coerce').fillna(0) if found else 0.0

    # Metadados
    df["_title"] = df[pick_col(df, TITLE_CANDIDATES) or df.columns[0]].fillna("No Title")
    df["_year"] = df[pick_col(df, YEAR_CANDIDATES)].apply(extract_year) if pick_col(df, YEAR_CANDIDATES) else ""
    df["_doi_clean"] = df[pick_col(df, DOI_CANDIDATES)].apply(normalize_doi) if pick_col(df, DOI_CANDIDATES) else ""
    
    auth_col = pick_col(df, AUTHOR_CANDIDATES)
    df["_authors"] = df[auth_col].fillna("Unknown Author") if auth_col else "Unknown Author"

    # ÁREA
    area_col = pick_col(df, AREA_CANDIDATES)
    raw_area = df[area_col].fillna("Unknown") if area_col else pd.Series(["Unknown"]*len(df))
    
    if simplify_areas:
        df["_area"] = raw_area.apply(simplify_area_name)
    else:
        df["_area"] = raw_area

    return df

# --- SELEÇÃO (mantido do v6) ---
def sort_best_texts(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(
        by=["cf", "c_use_window", "c_use", "pagerank", "betweenness"],
        ascending=[False, False, False, False, False]
    )

def select_mode_A(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return sort_best_texts(df).drop_duplicates(subset=["_area"]).head(n)

def select_mode_B(df: pd.DataFrame, n: int) -> pd.DataFrame:
    df_s = sort_best_texts(df)
    counts = df_s["_area"].value_counts()
    if counts.sum() == 0: return df_s.head(n)
    quotas = (counts / counts.sum() * n).apply(math.floor).astype(int)
    remainder = n - quotas.sum()
    if remainder > 0:
        remainders = (counts / counts.sum() * n) - quotas
        for area in remainders.sort_values(ascending=False).index[:remainder]:
            quotas[area] += 1
    parts = [df_s[df_s["_area"] == area].head(q) for area, q in quotas.items() if q > 0]
    return pd.concat(parts).sort_values("cf", ascending=False) if parts else df_s.head(n)

def select_mode_C(df: pd.DataFrame, n: int, max_per_area: int) -> pd.DataFrame:
    df_s = sort_best_texts(df)
    selected = []
    area_counts = {}
    for _, row in df_s.iterrows():
        if len(selected) >= n: break
        if area_counts.get(row["_area"], 0) < max_per_area:
            selected.append(row)
            area_counts[row["_area"]] = area_counts.get(row["_area"], 0) + 1
    return pd.DataFrame(selected)

def select_mode_D(df: pd.DataFrame, n_per_area: int) -> pd.DataFrame:
    df_s = sort_best_texts(df)
    return df_s.groupby("_area", group_keys=False).head(n_per_area)

def generate_reading_lists(df: pd.DataFrame, limit_per_list=15):
    df = df.copy()
    df["z_cf"] = safe_z_score(df["cf"])
    df["z_use"] = safe_z_score(df["c_use_window"])
    df["z_pr"] = safe_z_score(df["pagerank"])
    
    core = df.sort_values(["z_cf", "z_pr"], ascending=[False, False]).groupby("_area").head(2).head(limit_per_list)
    recent = df.sort_values(["c_use_window", "_year"], ascending=[False, False]).groupby("_area").head(2).head(limit_per_list)
    bridge = df.sort_values("betweenness", ascending=False).groupby("_area").head(1).head(limit_per_list)
    
    df["score_div"] = 0.5*df["z_cf"] + 0.3*df["z_use"] + 0.2*df["z_pr"]
    diversity = df.sort_values("score_div", ascending=False).drop_duplicates(subset=["_area"]).head(limit_per_list)
    return core, recent, bridge, diversity

# --- EXPORT (mantido do v6) ---
def create_hyperlink_col(df: pd.DataFrame):
    formulas = []
    for _, row in df.iterrows():
        doi = row.get("_doi_clean")
        title = str(row.get("_title", "")).replace('"', "'")
        year = str(row.get("_year", ""))
        display = f"{year}; {title}"
        if doi:
            formulas.append(f'=HYPERLINK("https://doi.org/{doi}", "{display}")')
        else:
            formulas.append(display)
    return formulas

def format_for_download_script(df: pd.DataFrame) -> pd.DataFrame:
    lines = []
    for _, row in df.iterrows():
        auth_raw = str(row.get("_authors", "Unknown"))
        auth_clean = re.sub(r'(?:^|[\s;])\d+[\.\)\s]?\s*', ' ', auth_raw).strip()
        auth = auth_clean.replace(";", ",") 
        
        title = str(row.get("_title", "No Title")).replace(";", ",")
        year = str(row.get("_year", ""))
        doi = str(row.get("_doi_clean", ""))
        
        full_line = f"{auth}; {title}; {year}; {doi}"
        clean_line = full_line.lstrip("; ")
        lines.append(clean_line)
    
    return pd.DataFrame({"Download_String": lines})

def save_bundle(xlsx_input, df_full, mode, n, max_area, output_path, include_reading_lists=True):
    if "is_retracted" in df_full.columns: df_full = df_full[df_full["is_retracted"] != 1]
    if "is_focal" in df_full.columns: df_full = df_full[df_full["is_focal"] == 1]

    topA = select_mode_A(df_full, n)
    topB = select_mode_B(df_full, n)
    topC = select_mode_C(df_full, n, max_area)
    topD = select_mode_D(df_full, n)

    if mode == "A": main_sel = topA
    elif mode == "B": main_sel = topB
    elif mode == "C": main_sel = topC
    else: main_sel = topD

    main_sel = main_sel.copy()
    main_sel["Link_Excel"] = create_hyperlink_col(main_sel)

    df_all_downloads = main_sel.copy()
    lists_dfs = []
    
    if include_reading_lists:
        core, recent, bridge, div = generate_reading_lists(df_full)
        lists_dfs = [core, recent, bridge, div]
        df_all_downloads = pd.concat([df_all_downloads] + lists_dfs)

    df_all_downloads = df_all_downloads.drop_duplicates(subset=["_doi_clean", "_title"])
    download_sheet = format_for_download_script(df_all_downloads)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame({"Referência": main_sel["Link_Excel"]}).to_excel(writer, sheet_name="Lista_Links", index=False)
        main_sel.to_excel(writer, sheet_name=f"Main_Selection_Mode{mode}", index=False)
        topD.to_excel(writer, sheet_name=f"Top{n}_Per_Area", index=False)
        
        if mode != "C": topC.to_excel(writer, sheet_name="Top_Global_Capped", index=False)
        
        if include_reading_lists:
            core.to_excel(writer, sheet_name="L_CORE", index=False)
            recent.to_excel(writer, sheet_name="L_RECENT", index=False)
            bridge.to_excel(writer, sheet_name="L_BRIDGE", index=False)
            div.to_excel(writer, sheet_name="L_DIVERSITY", index=False)
            
        download_sheet.to_excel(writer, sheet_name="For_Download_Script", index=False, header=False)

    return output_path

# --- GUI COM SELEÇÃO INTELIGENTE ---
def launch_gui():
    root = tk.Tk()
    root.title("Seletor v7 (Seleção Inteligente de Excel)")
    root.geometry("900x800")
    
    folder_path = tk.StringVar()
    file_path = tk.StringVar()
    out_path = tk.StringVar()
    mode_var = tk.StringVar(value="D")
    n_var = tk.IntVar(value=3)
    max_cap_var = tk.IntVar(value=3)
    use_net_var = tk.BooleanVar(value=True)
    reading_list_var = tk.BooleanVar(value=False)
    simplify_var = tk.BooleanVar(value=True)
    auto_select_var = tk.BooleanVar(value=True)  # NOVO: seleção automática
    
    recommendation_text = tk.StringVar(value="Nenhuma análise realizada ainda.")

    def analyze_folder():
        """Analisa a pasta e mostra recomendações."""
        folder = folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Erro", "Selecione uma pasta válida.")
            return
        
        try:
            recommendation = analyze_excel_folder(folder)
            
            if recommendation['status'] == 'success':
                msg = f"Ficheiro Recomendado: {recommendation['file_name']}\n"
                msg += f"Sheet Recomendado: {recommendation['recommended_sheet']}\n"
                msg += f"Qualidade: {recommendation['overall_score']:.1%}\n"
                msg += f"Registos: {recommendation['sheet_quality']['row_count']:,}\n\n"
                msg += "Características:\n"
                sq = recommendation['sheet_quality']
                if sq['has_title']: msg += "- Tem título\n"
                if sq['has_doi']: msg += "- Tem DOI\n"
                if sq['has_year']: msg += "- Tem ano\n"
                if sq['has_author']: msg += "- Tem autor\n"
                if sq['has_area']: msg += "- Tem área\n"
                if sq['has_metrics']: msg += "- Tem métricas\n"
                
                recommendation_text.set(msg)
                file_path.set(recommendation['recommended_file'])
                out_path.set(f"{os.path.splitext(recommendation['recommended_file'])[0]}_Selected.xlsx")
            else:
                recommendation_text.set(f"Erro: {recommendation['message']}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro na análise: {e}")

    def browse_folder():
        p = filedialog.askdirectory(title="Selecionar pasta com ficheiros Excel")
        if p:
            folder_path.set(p)
            if auto_select_var.get():
                analyze_folder()

    def browse_file():
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if p:
            file_path.set(p)
            out_path.set(f"{os.path.splitext(p)[0]}_Selected.xlsx")

    def run():
        if not file_path.get() and not folder_path.get():
            return messagebox.showerror("Erro", "Selecione ficheiro ou pasta.")
        
        try:
            # Usar seleção inteligente se auto_select ativado
            if auto_select_var.get() and folder_path.get():
                df = load_data_intelligent(
                    folder_path=folder_path.get(),
                    use_network=use_net_var.get(),
                    simplify_areas=simplify_var.get(),
                    auto_select=True
                )
                input_file = folder_path.get()
            else:
                df = load_data_intelligent(
                    xlsx_path=file_path.get(),
                    use_network=use_net_var.get(),
                    simplify_areas=simplify_var.get(),
                    auto_select=False
                )
                input_file = file_path.get()
            
            out = save_bundle(
                input_file, df, mode_var.get(), n_var.get(),
                max_cap_var.get(), out_path.get(), reading_list_var.get()
            )
            
            count_download = len(pd.read_excel(out, sheet_name="For_Download_Script"))
            msg = f"Sucesso!\nArquivo: {out}\n\n"
            msg += f"Total para download: {count_download} documentos.\n"
            msg += f"Registos processados: {len(df):,}"
            
            messagebox.showinfo("Concluído", msg)
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    pad = {"padx": 10, "pady": 5, "sticky": "w"}
    frm = ttk.Frame(root); frm.pack(fill="both", expand=True, padx=20)
    
    # Pasta ou ficheiro com descrições
    folder_label_frame = ttk.Frame(frm)
    folder_label_frame.grid(row=0, column=0, **pad)
    ttk.Label(folder_label_frame, text="Pasta (análise automática):").pack(side="left")
    ttk.Label(folder_label_frame, text="  → Analisa todos os Excel na pasta e escolhe o melhor", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    ttk.Entry(frm, textvariable=folder_path, width=50).grid(row=0, column=1, **pad)
    ttk.Button(frm, text="Buscar Pasta", command=browse_folder).grid(row=0, column=2, **pad)
    
    file_label_frame = ttk.Frame(frm)
    file_label_frame.grid(row=1, column=0, **pad)
    ttk.Label(file_label_frame, text="OU Ficheiro específico:").pack(side="left")
    ttk.Label(file_label_frame, text="  → Seleciona um ficheiro Excel específico manualmente", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    ttk.Entry(frm, textvariable=file_path, width=50).grid(row=1, column=1, **pad)
    ttk.Button(frm, text="Buscar Ficheiro", command=browse_file).grid(row=1, column=2, **pad)
    
    analyze_frame = ttk.Frame(frm)
    analyze_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=10, pady=5)
    ttk.Button(analyze_frame, text="Analisar Pasta", command=analyze_folder).pack(side="left")
    ttk.Label(analyze_frame, text="  → Analisa qualidade dos ficheiros e mostra recomendações", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    
    # Área de recomendações com descrição
    rec_label_frame = ttk.Frame(frm)
    rec_label_frame.grid(row=3, column=0, **pad)
    ttk.Label(rec_label_frame, text="Recomendação:", font=("Arial", 9, "bold")).pack(side="left")
    ttk.Label(rec_label_frame, text="  → Análise de qualidade e recomendações do sistema", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    rec_text = tk.Text(frm, height=8, width=60, wrap="word")
    rec_text.grid(row=3, column=1, columnspan=2, **pad)
    rec_text.insert("1.0", recommendation_text.get())
    recommendation_text.trace_add("write", lambda *args: rec_text.delete("1.0", "end") or rec_text.insert("1.0", recommendation_text.get()))
    
    output_label_frame = ttk.Frame(frm)
    output_label_frame.grid(row=4, column=0, **pad)
    ttk.Label(output_label_frame, text="Output:").pack(side="left")
    ttk.Label(output_label_frame, text="  → Ficheiro Excel de saída com resultados", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    ttk.Entry(frm, textvariable=out_path, width=50).grid(row=4, column=1, **pad)
    
    ttk.Separator(frm, orient="horizontal").grid(row=5, column=0, columnspan=3, sticky="ew", pady=10)
    
    # Opções com descrições
    lbl_mode = ttk.Label(frm, text="Modo de Seleção:", font=("Arial", 10, "bold"))
    lbl_mode.grid(row=6, column=0, **pad)
    m_frm = ttk.Frame(frm); m_frm.grid(row=6, column=1, columnspan=2, sticky="w")
    
    # Modos com descrições
    mode_descriptions = {
        "A": "1/Área - Um melhor documento por área (diversidade máxima)",
        "B": "Quotas - Distribui N documentos proporcionalmente por área",
        "C": "Global Capped - Top N global com limite por área",
        "D": "Top N Fixo/Área - N documentos por área (recomendado)"
    }
    
    for m, t in [("A","A: 1/Área"), ("B","B: Quotas"), ("C","C: Global Capped"), ("D","D: Top N Fixo/Área")]:
        rb_frame = ttk.Frame(m_frm)
        rb_frame.pack(anchor="w", fill="x")
        ttk.Radiobutton(rb_frame, text=t, variable=mode_var, value=m).pack(side="left")
        desc_label = ttk.Label(rb_frame, text=f"  → {mode_descriptions[m]}", foreground="gray", font=("Arial", 8))
        desc_label.pack(side="left")
        
    ttk.Label(frm, text="N (Total ou por Área):").grid(row=7, column=0, **pad)
    n_frame = ttk.Frame(frm)
    n_frame.grid(row=7, column=1, columnspan=2, sticky="w")
    ttk.Spinbox(n_frame, from_=1, to=1000, textvariable=n_var, width=10).pack(side="left")
    ttk.Label(n_frame, text="  → Número de documentos a selecionar (total ou por área conforme modo)", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    
    # Max Cap (para modo C)
    max_cap_label_frame = ttk.Frame(frm)
    max_cap_label_frame.grid(row=8, column=0, **pad)
    ttk.Label(max_cap_label_frame, text="Max por Área (Modo C):").pack(side="left")
    ttk.Label(max_cap_label_frame, text="  → Limite máximo de documentos por área no Modo C", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    max_cap_frame = ttk.Frame(frm)
    max_cap_frame.grid(row=8, column=1, columnspan=2, sticky="w")
    ttk.Spinbox(max_cap_frame, from_=1, to=100, textvariable=max_cap_var, width=10).pack(side="left")
    ttk.Label(max_cap_frame, text="  → Usado apenas no Modo C (Global Capped)", 
              foreground="gray", font=("Arial", 8)).pack(side="left")

    # Checkboxes com descrições
    auto_frame = ttk.Frame(frm)
    auto_frame.grid(row=9, column=0, columnspan=3, **pad)
    ttk.Checkbutton(auto_frame, text="Seleção Automática", variable=auto_select_var).pack(side="left")
    ttk.Label(auto_frame, text="  → Analisa pasta e escolhe automaticamente o melhor ficheiro e sheet", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    
    simplify_frame = ttk.Frame(frm)
    simplify_frame.grid(row=10, column=0, columnspan=3, **pad)
    ttk.Checkbutton(simplify_frame, text="Agrupar sub-áreas em Macro-Áreas", variable=simplify_var).pack(side="left")
    ttk.Label(simplify_frame, text="  → Simplifica áreas específicas (ex: 'Marine Biology' → 'Biology & Medicine')", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    
    net_frame = ttk.Frame(frm)
    net_frame.grid(row=11, column=0, columnspan=3, **pad)
    ttk.Checkbutton(net_frame, text="Usar Métricas de Rede", variable=use_net_var).pack(side="left")
    ttk.Label(net_frame, text="  → Inclui métricas de rede (PageRank, Betweenness) do sheet 'Network Metrics'", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    
    reading_frame = ttk.Frame(frm)
    reading_frame.grid(row=12, column=0, columnspan=3, **pad)
    ttk.Checkbutton(reading_frame, text="Gerar Listas de Leitura e Download", variable=reading_list_var).pack(side="left")
    ttk.Label(reading_frame, text="  → Cria listas adicionais: Core (importantes), Recent (recentes), Bridge (pontes), Diversity (diversos)", 
              foreground="gray", font=("Arial", 8)).pack(side="left")
    
    ttk.Button(root, text="EXECUTAR", command=run).pack(pady=20, fill="x", padx=40)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()

