# -*- coding: utf-8 -*-
"""
openalex_converter.py
Converte CSV do OpenAlex (Works) para CSV "estilo Scopus" que a tua GUI já aceita.
- Se executares SEM argumentos -> abre GUI (Tkinter).
- Se executares COM argumentos -> modo CLI:
    python openalex_converter.py "works.csv" "openalex_as_scopus.csv"

Saída (colunas): Authors, Title, Year, Source title, Cited by, DOI,
                 Abstract, Author Keywords, Document Type, EID, Link
"""

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

# ----------------- Helpers de extração -----------------

def norm_doi(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r'^(https?://(dx\.)?doi\.org/|doi:)', '', s, flags=re.I)
    return s.lower()

def parse_abstract_inv_index(x) -> str:
    """Reconstrói o abstract a partir de abstract_inverted_index (JSON: token -> [pos])."""
    if not isinstance(x, str) or not x.strip():
        return ""
    try:
        obj = json.loads(x)
        items = []
        for token, poss in obj.items():
            for p in poss:
                items.append((int(p), token))
        if not items:
            return ""
        items.sort(key=lambda z: z[0])
        text = " ".join(t for _, t in items)
        return re.sub(r"\s+", " ", text).strip()
    except Exception:
        return ""

def extract_authors(row: pd.Series) -> str:
    """Extrai autores de 'authorships' (JSON) -> 'Nome; Nome; ...'"""
    val = row.get("authorships")
    if isinstance(val, str) and val.strip().startswith("["):
        try:
            arr = json.loads(val)
            names = []
            for a in arr:
                nm = None
                if isinstance(a, dict):
                    if "author" in a and isinstance(a["author"], dict):
                        nm = a["author"].get("display_name")
                    if not nm:
                        nm = a.get("author_display_name") or a.get("author_name")
                if nm:
                    names.append(str(nm))
            return "; ".join(names)
        except Exception:
            return ""
    return ""

def extract_source_title(row: pd.Series) -> str:
    for c in [
        "host_venue.display_name",
        "primary_location.source.display_name",
        "journal.display_name",
        "venue.display_name",
    ]:
        v = row.get(c)
        if isinstance(v, str) and v.strip():
            return v
    return ""

def extract_document_type(row: pd.Series) -> str:
    for c in ["type", "type_crossref", "type_assertion"]:
        v = row.get(c)
        if isinstance(v, str) and v.strip():
            return v
    return ""

def extract_title(row: pd.Series) -> str:
    for c in ["display_name", "title"]:
        v = row.get(c)
        if isinstance(v, str) and v.strip():
            return v
    return ""

def extract_year(row: pd.Series):
    v = row.get("publication_year")
    try:
        return int(v)
    except Exception:
        return ""

def extract_abstract(row: pd.Series) -> str:
    v = row.get("abstract")
    if isinstance(v, str) and v.strip():
        return v
    return parse_abstract_inv_index(row.get("abstract_inverted_index", ""))

def extract_keywords(row: pd.Series) -> str:
    """‘topics’ (JSON) -> 'kw; kw; ...'; fallback para ‘concepts’ se existir."""
    tv = row.get("topics")
    if isinstance(tv, str) and tv.strip().startswith("["):
        try:
            arr = json.loads(tv)
            names = []
            for t in arr:
                if isinstance(t, dict):
                    nm = t.get("display_name")
                    if nm:
                        names.append(str(nm))
            if names:
                return "; ".join(sorted(set(names)))
        except Exception:
            pass
    cv = row.get("concepts")
    if isinstance(cv, str) and cv.strip().startswith("["):
        try:
            arr = json.loads(cv)
            names = []
            for c in arr:
                if isinstance(c, dict):
                    nm = c.get("display_name")
                    if nm:
                        names.append(str(nm))
            if names:
                return "; ".join(sorted(set(names)))
        except Exception:
            pass
    return ""

def extract_doi(row: pd.Series) -> str:
    for c in ["doi", "ids.doi"]:
        v = row.get(c)
        if isinstance(v, str) and v.strip():
            return norm_doi(v)
    return ""

def extract_eid_and_link(row: pd.Series):
    v = row.get("id")
    if isinstance(v, str) and v.strip():
        return v, v
    return "", ""

# ----------------- Conversão principal -----------------

def convert_openalex_to_scopus_like(in_csv: Path, out_csv: Path, encoding: str = "utf-8-sig") -> int:
    df = pd.read_csv(in_csv, low_memory=False)
    rows = []
    for _, row in df.iterrows():
        authors   = extract_authors(row)
        title     = extract_title(row)
        year      = extract_year(row)
        source    = extract_source_title(row)
        cited_by  = row.get("cited_by_count")
        try:
            cited_by = int(cited_by) if pd.notna(cited_by) else 0
        except Exception:
            cited_by = 0
        doi       = extract_doi(row)
        abstract  = extract_abstract(row)
        keywords  = extract_keywords(row)
        doc_type  = extract_document_type(row)
        eid, link = extract_eid_and_link(row)

        rows.append({
            "Authors": authors,
            "Title": title,
            "Year": year,
            "Source title": source,
            "Cited by": cited_by,
            "DOI": doi,
            "Abstract": abstract,
            "Author Keywords": keywords,
            "Document Type": doc_type,
            "EID": eid,
            "Link": link,
        })

    out_df = pd.DataFrame(rows, columns=[
        "Authors","Title","Year","Source title","Cited by","DOI",
        "Abstract","Author Keywords","Document Type","EID","Link"
    ])
    out_df.to_csv(out_csv, index=False, encoding=encoding)
    return len(out_df)

# ----------------- CLI + GUI -----------------

def run_cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("openalex_csv", help="CSV do OpenAlex (Works)")
    ap.add_argument("out_csv", help="CSV de saída 'estilo Scopus'")
    ap.add_argument("--encoding", default="utf-8-sig",
                    help="encoding do CSV de saída (default: utf-8-sig)")
    args = ap.parse_args()

    in_path = Path(args.openalex_csv)
    out_path = Path(args.out_csv)
    if not in_path.exists():
        raise SystemExit(f"Ficheiro não encontrado: {in_path}")

    n = convert_openalex_to_scopus_like(in_path, out_path, args.encoding)
    print(f"OK: {n} registos → {out_path.as_posix()}")

def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("OpenAlex → CSV estilo Scopus")
    root.geometry("720x220")

    in_var  = tk.StringVar()
    out_var = tk.StringVar(value=str(Path.cwd() / "openalex_as_scopus.csv"))
    enc_var = tk.StringVar(value="utf-8-sig")

    frm = ttk.Frame(root, padding=10)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="CSV do OpenAlex (Works):").grid(row=0, column=0, sticky="w")
    e1 = ttk.Entry(frm, textvariable=in_var, width=80); e1.grid(row=1, column=0, columnspan=2, sticky="we", pady=2)
    ttk.Button(frm, text="Procurar…", command=lambda: pick_in()).grid(row=1, column=2, padx=6)

    ttk.Label(frm, text="CSV de saída (estilo Scopus):").grid(row=2, column=0, sticky="w", pady=(8,0))
    e2 = ttk.Entry(frm, textvariable=out_var, width=80); e2.grid(row=3, column=0, columnspan=2, sticky="we", pady=2)
    ttk.Button(frm, text="Guardar como…", command=lambda: pick_out()).grid(row=3, column=2, padx=6)

    ttk.Label(frm, text="Encoding:").grid(row=4, column=0, sticky="w", pady=(8,0))
    ttk.Combobox(frm, textvariable=enc_var, values=["utf-8-sig","utf-8","cp1252"], width=12, state="readonly").grid(row=4, column=1, sticky="w")

    status = ttk.Label(frm, text="Pronto.", foreground="#555"); status.grid(row=5, column=0, columnspan=3, sticky="w", pady=(12,0))
    btn = ttk.Button(frm, text="Converter", command=lambda: do_convert()); btn.grid(row=6, column=0, pady=10)

    frm.columnconfigure(0, weight=1)

    def pick_in():
        p = filedialog.askopenfilename(title="Escolher CSV do OpenAlex", filetypes=[("CSV","*.csv")])
        if p:
            in_var.set(p)
            # sugerir nome de saída
            out_var.set(str(Path(p).with_suffix("").as_posix() + "_as_scopus.csv"))

    def pick_out():
        p = filedialog.asksaveasfilename(title="Guardar CSV (estilo Scopus)", defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if p:
            out_var.set(p)

    def do_convert():
        try:
            inp = Path(in_var.get())
            outp = Path(out_var.get())
            if not inp.exists():
                messagebox.showerror("Erro", "CSV de entrada não encontrado.")
                return
            status.config(text="A converter…"); root.update_idletasks()
            n = convert_openalex_to_scopus_like(inp, outp, enc_var.get())
            status.config(text=f"OK: {n} registos → {outp.name}")
            messagebox.showinfo("Concluído", f"Convertidos {n} registos.\n\nFicheiro: {outp}")
        except Exception as e:
            status.config(text="Erro.")
            messagebox.showerror("Erro na conversão", str(e))

    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # Modo CLI se foram passados os 2 argumentos obrigatórios
        run_cli()
    else:
        # Sem argumentos -> abre GUI
        run_gui()
