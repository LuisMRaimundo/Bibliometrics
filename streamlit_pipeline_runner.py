# streamlit_pipeline_runner.py — import-safe Streamlit shell for package pipeline
# Run: streamlit run streamlit_pipeline_runner.py

from __future__ import annotations

from pathlib import Path

import streamlit as st

from bibliometric_analysis.dashboard.runner import build_pipeline_config, run_pipeline_from_upload


def main() -> None:
    st.set_page_config(page_title="Bibliometric Pipeline", layout="wide")
    st.title("Bibliometric Analysis — Pipeline Runner")
    st.caption("bibliometric/scientometric research software with OpenAlex-based normalization.")

    uploaded = st.file_uploader("Upload WoS / Scopus / OpenAlex / PoP input", type=["txt", "csv"])
    mailto = st.text_input("OpenAlex mailto (required for online mode)", value="")
    offline = st.checkbox("Offline mode (local baseline, no OpenAlex fetch)", value=True)
    source = st.selectbox("Input format", ["auto", "wos", "scopus", "openalex", "pop"])
    ties = st.selectbox("Ties policy", ["closed_ge", "open_gt", "hazen"])
    k_window = st.slider("Citation window k", 0, 10, 5)
    concept_level = st.slider("OpenAlex concept level", 0, 2, 1)

    if st.button("Run analysis", disabled=uploaded is None):
        cfg = build_pipeline_config(
            ties_policy=ties,
            use_local_baseline=True,
            k_window=k_window,
            concept_level=concept_level,
        )
        if not offline and not mailto.strip():
            st.error("Online mode requires a mailto address.")
            return
        with st.spinner("Running pipeline …"):
            result = run_pipeline_from_upload(
                uploaded.getvalue(),
                uploaded.name,
                Path(st.session_state.get("out_dir", ".")),
                offline=offline,
                source=source,
                mailto=mailto.strip(),
                config=cfg,
                log=st.write,
            )
        out = result.get("out_path")
        if out and Path(out).exists():
            st.success(f"Export complete: {out}")
            st.download_button("Download Excel", Path(out).read_bytes(), file_name=Path(out).name)
        else:
            st.info("Pipeline finished. Check output path in result.")


if __name__ == "__main__":
    main()
