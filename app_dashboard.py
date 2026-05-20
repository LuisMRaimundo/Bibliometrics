# app_dashboard.py — v2.2 (import-safe Streamlit shell; logic in bibliometric_analysis.dashboard)
# Requisitos: streamlit, pandas, scikit-learn, openpyxl, xlsxwriter
# Run: streamlit run app_dashboard.py

from __future__ import annotations

import pandas as pd
import streamlit as st

from bibliometric_analysis.dashboard import (
    agg_mncs_pp,
    compute_dashboard_metrics,
    compute_goldset_qa,
    compute_sensitivity_table,
    ensure_min_metrics,
    get_sheet,
    load_excel_data,
    load_var_records_any,
    read_gold_csv,
    resolve_unit_col,
)
from metrics.percentiles import compute_ppx


def main() -> None:
    st.set_page_config(page_title="Bibliometrics Dashboard", layout="wide")

    st.sidebar.header("Configurações")
    uploaded = st.sidebar.file_uploader("Carregar Excel exportado pelo núcleo (.xlsx)", type=["xlsx"])
    st.sidebar.selectbox(
        "Política de percentis (ties)",
        ["≥ limiar (fechado)", "> limiar (aberto)"],
        help="Define como tratar empates na fronteira do percentil.",
    )
    target_err = st.sidebar.number_input(
        "Alvo de erro relativo do baseline (c₀/limiares), %",
        min_value=0.5, max_value=20.0, value=5.0, step=0.5,
    )
    graph_mode = st.sidebar.selectbox("Modo de grafo para comunidades", ["Não dirigido", "Dirigido"])
    st.sidebar.markdown("---")
    st.sidebar.subheader("Sensibilidade (comparar com baseline)")
    st.sidebar.multiselect("Janelas k", [3, 5, 7], default=[5])
    st.sidebar.multiselect("Nível de conceito (OpenAlex)", [1, 2], default=[1])
    st.sidebar.multiselect("Contagem", ["fractional", "full"], default=["fractional"])
    st.sidebar.markdown("---")
    st.sidebar.subheader("QA Deduplicação")
    gold_csv = st.sidebar.file_uploader("Gold set de pares (CSV)", type=["csv"])

    st.title("Bibliometrics Dashboard — v2.2")

    if not uploaded:
        st.info("Carrega o Excel exportado pelo núcleo para começar.")
        return

    sheets = load_excel_data(uploaded.getvalue())
    df_records = get_sheet(sheets, "Records+Metrics", "Records + Metrics", "Records & Metrics", "Records Metrics")
    df_global = get_sheet(sheets, "Global Dist/Thresholds", "Global Dist Thresholds", "Global Dist + Thresholds")
    df_meta = get_sheet(sheets, "Run Metadata", "Run-Metadata", "RunMeta")

    if df_records is None:
        st.error("Falta a folha 'Records+Metrics'. Reexporta no núcleo ou ajusta o nome aqui.")
        return

    tabs = st.tabs(["Visão geral", "Métricas & Percentis", "Rede (HTML)", "QA Deduplicação", "Sensibilidade"])

    with tabs[0]:
        st.subheader("Resumo da execução")
        metrics = compute_dashboard_metrics(df_records, df_global, err_target=float(target_err))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Publicações (corpus)", f"{metrics['n_docs']}")
        c2.metric("MNCS (média c_f)", "N/A" if pd.isna(metrics["mncs"]) else f"{metrics['mncs']:.3f}")
        c3.metric("PP(top10%)", "N/A" if pd.isna(metrics["pp10_share"]) else f"{metrics['pp10_share']:.1f}%")
        c4.metric("Execuções registadas", f"{len(df_meta) if df_meta is not None else 0}")

        st.markdown("#### Alvo de erro do baseline")
        err_target = metrics["err_target"]
        for label, key in [
            ("Erro relativo c₀", "err_c0_pct"),
            ("Erro relativo limiar top25%", "err_thr25_pct"),
            ("Erro relativo limiar top10%", "err_thr10_pct"),
            ("Erro relativo limiar top1%", "err_thr1_pct"),
        ]:
            value = metrics["err_vals"][key]
            if pd.isna(value):
                st.metric(label, "N/A")
            else:
                st.metric(label, f"{value:.2f}%")
                if value > err_target:
                    st.warning(f"{label} acima do alvo ({err_target:.1f}%).")

        if metrics["pp_realized"]:
            st.caption("Sem erros de baseline (baseline local). Mostramos %PP realizadas no corpus.")
            for col, share in metrics["pp_realized"].items():
                st.metric(f"% realizado {col.replace('PPg_', '')}", f"{share:.2f}%")

    with tabs[1]:
        st.subheader("PPx (compute_ppx) com baseline por grupos")
        score_candidates = [c for c in ("c_use_window", "c_use") if c in df_records.columns]
        if not score_candidates:
            st.warning("Não encontrei 'c_use' nem 'c_use_window' em Records+Metrics.")
        else:
            score_col = st.selectbox("Score a ranquear", options=score_candidates, index=0)
            key_pool = [c for c in df_records.columns if c in ("year", "domain_label", "domain_id", "field", "concept_label", "concept_id")]
            default_keys = [c for c in ("year", "domain_label") if c in key_pool] or [c for c in ("year", "domain_id") if c in key_pool]
            by_cols = st.multiselect("Agrupar por (baseline)", options=key_pool, default=default_keys)
            p = st.slider("Percentil p (PP top = 100*(1-p)%)", min_value=0.50, max_value=0.99, value=0.90, step=0.01)
            ties_gui = st.selectbox("Política de empates (ties)", ["≥ limiar (fechado)", "> limiar (aberto)"])
            tie_map = {"≥ limiar (fechado)": ">=threshold", "> limiar (aberto)": ">threshold"}
            df_ppx = compute_ppx(df_records, score_col=score_col, by=by_cols, p=float(p), ties=tie_map[ties_gui])
            pp_col = [c for c in df_ppx.columns if c.startswith("pp")][-1]
            show_cols = (by_cols + [score_col, "ppx_threshold", pp_col]) if by_cols else [score_col, "ppx_threshold", pp_col]
            st.dataframe(df_ppx[show_cols].head(20))
            unit_opts = [c for c in df_ppx.columns if c.lower() in {"author", "authors", "institution", "affiliation", "unit", "unit_id", "country"}]
            unit_col = st.selectbox("Agregação por unidade", options=unit_opts or [])
            if unit_col:
                if "c_f" not in df_ppx.columns and "c0_mean" in df_ppx.columns:
                    s_eff = pd.to_numeric(df_ppx[score_col], errors="coerce")
                    c0 = pd.to_numeric(df_ppx["c0_mean"], errors="coerce")
                    df_ppx["c_f"] = (s_eff / c0).where(c0 > 0)
                agg = agg_mncs_pp(df_ppx, unit_col, "c_f", [pp_col])
                st.dataframe(agg)

    with tabs[2]:
        st.subheader("Rede de citação (visualização HTML)")
        html_file = st.file_uploader("Carregar HTML da rede", type=["html"])
        expected = "dirigido" if graph_mode == "Dirigido" else "nao_dirigido"
        st.info(f"Modo selecionado: **{graph_mode}**. Sugere-se `network_{expected}.html`.")
        if html_file:
            st.components.v1.html(html_file.read().decode("utf-8", errors="replace"), height=800, scrolling=True)

    with tabs[3]:
        st.subheader("Qualidade da deduplicação (gold set)")
        if gold_csv:
            gd = read_gold_csv(gold_csv.getvalue())
            if gd.shape[1] < 2:
                st.error("CSV inválido: menos de 2 colunas.")
                return
            cols = gd.columns.tolist()
            y_true_col = st.selectbox("Coluna gold (0/1)", cols, index=cols.index("match") if "match" in cols else 0)
            y_pred_col = st.selectbox("Coluna previsão (0/1)", cols, index=cols.index("y_pred") if "y_pred" in cols else 0)
            qa = compute_goldset_qa(gd, y_true_col, y_pred_col)
            c1, c2, c3 = st.columns(3)
            c1.metric("Precisão", f"{qa['precision']:.3f}")
            c2.metric("Revocação", f"{qa['recall']:.3f}")
            c3.metric("F1", f"{qa['f1']:.3f}")
            if qa["coerced_true"] or qa["coerced_pred"]:
                st.info(f"Valores coeridos → gold: {qa['coerced_true']}, previsão: {qa['coerced_pred']}.")
            st.write(gd.head(20))
        else:
            st.info("Carrega um CSV de gold set para avaliar precisão/recall/F1.")

    with tabs[4]:
        st.subheader("Relatório de sensibilidade (Δ vs baseline)")
        var_files = st.file_uploader("Carregar 1..5 variantes de Excel", type=["xlsx"], accept_multiple_files=True)
        if not var_files:
            st.info("Carrega pelo menos um .xlsx de variante para comparar.")
            return
        first = var_files[0]
        var_records, has_metrics = load_var_records_any(pd.ExcelFile(first))
        if var_records is None:
            st.error(f"A variante '{first.name}' não tem folha reconhecida.")
            return
        if not has_metrics:
            var_records = ensure_min_metrics(var_records)
        canon_opts = ["institution", "author", "country"]
        avail = [c for c in canon_opts if resolve_unit_col(df_records, c) and resolve_unit_col(var_records, c)]
        unit_canon = st.selectbox("Unidade para comparação", options=avail or canon_opts)
        for f in var_files:
            xls = pd.ExcelFile(f)
            rec, has_m = load_var_records_any(xls)
            if rec is None:
                st.warning(f"Ignorado '{f.name}': sem folha reconhecida.")
                continue
            if not has_m:
                rec = ensure_min_metrics(rec)
            comp = compute_sensitivity_table(df_records, rec, unit_canon)
            if comp is None:
                st.warning(f"Ignorado '{f.name}': colunas de unidade incompatíveis.")
                continue
            st.markdown(f"**Comparação vs baseline — {f.name}**")
            show = [unit_canon, "n_docs_base", "n_docs_var", "mncs_base", "mncs_var", "Δ_MNCS"]
            if "pp10_base" in comp.columns:
                show += ["pp10_base", "pp10_var", "Δ_PP10 (pp)"]
            st.dataframe(comp[show].head(200))

    st.caption("© 2025 — Dashboard v2.2 (package-backed, import-safe).")


if __name__ == "__main__":
    main()
