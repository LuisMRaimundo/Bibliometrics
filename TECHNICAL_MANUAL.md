# Bibliometric Analysis System — Technical Manual
## Version 16 — Complete Reference

> **v16 update:** Core logic moved to installable package `bibliometric_analysis/`. Root scripts remain as compatibility entry points. See `docs/architecture.md`, `docs/export_schema.md`, `docs/dependencies.md`.

---

# Table of Contents
1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Installation and Dependencies](#3-installation-and-dependencies)
4. [Module Reference](#4-module-reference)
5. [Mathematical Algorithms and Formulas](#5-mathematical-algorithms-and-formulas)
6. [Tutorial](#6-tutorial)
7. [Bibliography](#7-bibliography)

---

# 1. Introduction

The **Bibliometric Analysis System** is a comprehensive Python application for bibliometric analysis using the OpenAlex API. It supports:

- **Data ingestion** from Web of Science (.txt), Scopus (.csv), OpenAlex CSV, and Publish or Perish/Google Scholar exports
- **Citation normalization** via MNCS (Mean Normalized Citation Score) with global or local baselines
- **Percentile-based metrics** (PP top 25%, 10%, 1%) with configurable ties policies
- **Citation network analysis** with community detection (Leiden, Louvain, Greedy Modularity)
- **Entity enrichment** (authors, institutions) via OpenAlex
- **Semantic topic modeling** with BERTopic
- **Intelligent text selection** for reading lists and corpus subsets

---

# 2. System Architecture

```
Bibliometric analysis_15/
├── software_gui_pro_4.py        # Main application (Tkinter GUI)
├── app_dashboard.py             # Streamlit dashboard (post-analysis)
├── openalex_converter.py        # OpenAlex CSV → Scopus-like CSV
├── enrich_entities.py          # Author/institution enrichment
├── viz_network_plus.py          # CLI network visualization
├── viz_network_interface_2.py    # Tkinter GUI for network viz
├── semantic_bertopic_preset.py   # BERTopic topic modeling
├── Query_OpenAlex/
│   └── openalex_query_7.py     # OpenAlex query tool (GUI)
├── TEXTS SELECT/
│   ├── select_texts_gui_v7_intelligent.py  # Text selection GUI
│   └── excel_analyzer.py        # Excel quality analyzer
├── metrics/
│   ├── __init__.py
│   └── percentiles.py           # PPx computation
└── tests/
    └── test_percentiles.py
```

**Data flow:**
1. **Input** → WoS/Scopus/OpenAlex parsers → Deduplicated corpus (DOI-based)
2. **OpenAlex enrichment** → Focal works + citers → Domain concepts, citations
3. **Baseline computation** → c₀ (mean), percentiles (q75, q90, q99) per domain×year
4. **Metrics** → MNCS (cf), PP flags, network metrics
5. **Export** → Excel (Records+Metrics, Edges, Network Metrics, Summaries, Run Metadata)

---

# 3. Installation and Dependencies

## 3.1 Core Requirements (`requirements.txt`)

```
pandas
requests
tqdm
XlsxWriter
```

## 3.2 Full Dependency Set

| Package | Purpose | Required For |
|---------|---------|--------------|
| pandas | Data handling | All modules |
| numpy | Numerical operations | Metrics, bootstrap |
| requests | HTTP/API | OpenAlex, enrich_entities |
| tqdm | Progress bars | software_gui_pro_4 (opt-in) |
| XlsxWriter | Excel export | software_gui_pro_4, select_texts |
| networkx | Graph analysis | software_gui_pro_4, viz_network |
| openpyxl | Excel read | viz_network, select_texts, excel_analyzer |
| pyvis | Interactive HTML graphs | viz_network |
| python-louvain | Louvain communities | software_gui_pro_4 (optional) |
| igraph + leidenalg | Leiden communities | software_gui_pro_4 (optional) |
| streamlit | Web dashboard | app_dashboard |
| scikit-learn | Precision/Recall/F1 | app_dashboard (QA) |
| rapidfuzz | Fuzzy deduplication | enrich_entities |
| sentence-transformers | Embeddings | semantic_bertopic |
| umap-learn | Dimensionality reduction | semantic_bertopic |
| hdbscan | Clustering | semantic_bertopic |
| bertopic | Topic modeling | semantic_bertopic |

## 3.3 Installation Commands

```bash
pip install pandas requests tqdm XlsxWriter networkx openpyxl pyvis
pip install python-louvain   # optional: Louvain
pip install igraph leidenalg # optional: Leiden
pip install streamlit scikit-learn  # for dashboard
pip install rapidfuzz  # for enrich_entities
pip install sentence-transformers umap-learn hdbscan bertopic  # for BERTopic
```

---

# 4. Module Reference

## 4.1 software_gui_pro_4.py — Main Bibliometric Engine

**Purpose:** Full bibliometric pipeline with OpenAlex integration, MNCS/PP metrics, citation network, and community detection.

**Key functions:**
- `parse_wos_txt`, `parse_scopus_csv`, `parse_openalex_csv`, `parse_pop_csv` — Parsers
- `build_corpus` — Focal works + citers, window k, self-citation exclusion
- `build_edges_by_doi` — Citation edges from referenced works
- `community_detection` — Leiden / Louvain / Greedy Modularity
- `global_distribution` — c₀ and percentiles from OpenAlex histogram/group_by
- `add_cf_and_pp_global` — MNCS (cf) and PP flags per record
- `explode_multifield_fractional` — Multi-field fractional counting
- `bootstrap_mncs_with_c0` — 95% CI for MNCS via bootstrap

## 4.2 app_dashboard.py — Streamlit Dashboard

**Purpose:** Post-analysis visualization, PPx recomputation, sensitivity analysis, QA deduplication.

**Features:**
- Overview metrics (corpus size, MNCS, PP10%)
- PPx with configurable baseline groups and ties policy
- Network HTML viewer
- Gold-set QA (Precision, Recall, F1)
- Sensitivity (Δ MNCS, Δ PP10 vs baseline)

## 4.3 metrics/percentiles.py — PPx Computation

**Purpose:** Percentile-based performance (PP top X%) with group-specific baselines.

**API:**
```python
compute_ppx(df, score_col, by=None, p=0.90, ties=">=threshold")
# Returns df with ppx_threshold and pp{top_pct} column
```

## 4.4 enrich_entities.py — Author/Institution Enrichment

**Purpose:** Harvest authors and institutions from OpenAlex for DOIs in Excel, with fuzzy name deduplication.

**Output:** `authors.csv`, `institutions.csv`, `authorships.csv`

## 4.5 viz_network_plus.py / viz_network_interface_2.py

**Purpose:** Build interactive citation network (PyVis) from Excel; node size/color by metrics.

## 4.6 semantic_bertopic_preset.py

**Purpose:** BERTopic topic modeling on title+abstract from Records+Metrics; exports topic assignments and HTML visualization.

## 4.7 select_texts_gui_v7_intelligent.py + excel_analyzer.py

**Purpose:** Intelligent selection of texts by area, with Excel quality analysis and automatic file/sheet recommendation.

## 4.8 Query_OpenAlex / openalex_query_7.py

**Purpose:** GUI for querying OpenAlex API (title/abstract filters, date range, type) with CSV/BibTeX/HTML export.

## 4.9 openalex_converter.py

**Purpose:** Convert OpenAlex Works CSV to Scopus-like CSV format.

---

# 5. Mathematical Algorithms and Formulas

## 5.1 DOI Normalization

**Regex pattern:**
```
\b10\.\d{4,9}/[^\s;()<>\"']+
```

DOIs are extracted, lowercased, and stripped of trailing punctuation. Deduplication is by DOI; records without DOI are preserved.

---

## 5.2 Title Similarity (Jaccard)

Used for matching works by title in OpenAlex search:

$$ \text{similarity}(A, B) = \frac{|A \cap B|}{|A \cup B|} $$

Where $A$, $B$ are sets of tokens from normalized titles (NFKD → ASCII, lowercase, alphanumeric only). Minimum acceptance threshold: **0.60** (configurable via `min_sim`).

---

## 5.3 Baseline Mean (c₀) from Histogram

Given a histogram of citation counts $\{(k_i, n_i)\}$ (value $k_i$, frequency $n_i$):

$$ c_0 = \bar{c} = \frac{\sum_i k_i \cdot n_i}{\sum_i n_i} = \frac{\sum_i k_i \cdot n_i}{N} $$

Implementation: `_mean_from_hist(values, counts)` in `software_gui_pro_4.py`.

---

## 5.4 Quantile from Discrete Histogram

Two methods supported:

**CDF-min (default):**
$$ \text{target} = p \cdot N, \quad \text{quantile} = \text{value at index } \arg\min_i \{\text{cumsum}_i \geq \text{target}\} $$

**Hazen:**
$$ \text{target} = p \cdot N + 0.5, \quad \text{same index search} $$

Where `cumsum` is the cumulative sum of frequencies. Implementation: `_quantile_from_hist()`.

---

## 5.5 MNCS (Mean Normalized Citation Score)

For each document:

$$ \text{cf} = \frac{c_{\text{use}}}{c_0} $$

- $c_{\text{use}}$: citation count used (either `cited_by_count` or `c_use_window` when k-window is active).
- $c_0$: baseline mean for the same (domain_id, year).

When baseline is incomplete, bootstrap resampling of the population distribution is used to estimate the denominator.

---

## 5.6 PP (Percentile Performance) Flags

Let $\tau_p$ be the $p$-quantile threshold for the baseline. For each document with score $c$:

**Ties policy `closed_ge` (≥):**
$$ \text{PPg\_top}X = \mathbf{1}[c \geq \tau_p] $$

**Ties policy `open_gt` (>):**
$$ \text{PPg\_top}X = \mathbf{1}[c > \tau_p] $$

Percentiles used: $p=0.75$ (top 25%), $p=0.90$ (top 10%), $p=0.99$ (top 1%).

---

## 5.7 PPx (compute_ppx) — Generic Percentile Rank

For score column $s$ and groups $g$:

1. Compute threshold: $\tau_g = Q_p(s_g)$ with linear interpolation.
2. Flag: $f_i = \mathbf{1}[s_i \geq \tau_{g(i)}]$ (or $>$, depending on `ties`).

Column naming: `pp{top_pct}` where `top_pct = (1-p)*100` (e.g. `p=0.90` → `pp10`).

---

## 5.8 Bootstrap for MNCS Confidence Interval

- Draw $B$ bootstrap samples (default $B=1000$) from document citations.
- For each sample: $\text{MNCS}_b = \bar{c}_{\text{sample}} / \tilde{c}_0$, where $\tilde{c}_0$ is either the known $c_0$ (if complete baseline) or a bootstrap draw from the population histogram.
- 95% CI: $[\tilde{Q}_{0.025}, \tilde{Q}_{0.975}]$ of $\{\text{MNCS}_b\}$.

---

## 5.9 Fractional Counting (Multi-field)

For multi-concept documents:

**Concept weights:** either uniform ($w_{\text{con}} = 1/K$) or score-proportional:
$$ w_{\text{con},k} = \frac{s_k}{\sum_j s_j} $$

**Author weight:** $w_{\text{auth}} = 1/n_{\text{authors}}$

**Affiliation weight:** $w_{\text{aff}} = 1/n_{\text{affiliations}}$

**Total fractional weight:**
$$ w_{\text{total}} = w_{\text{concept}} \times w_{\text{author}} \times w_{\text{affiliation}} $$

Weighted MNCS and PP aggregates use:
$$ \overline{x}_w = \frac{\sum_i w_i x_i}{\sum_i w_i} $$

---

## 5.10 Baseline Error Estimation (Bootstrap)

For histogram $\{(k_i, n_i)\}$ and $B$ bootstrap replicates:

- Draw multinomial $(n_1^*, \ldots, n_k^*)$ from $\mathbf{p} = (n_i/N)$.
- Compute $\hat{c}_0^*$, $\hat{\tau}_{75}^*$, $\hat{\tau}_{90}^*$, $\hat{\tau}_{99}^*$ from bootstrap histogram.
- Relative error (e.g. for $c_0$): $\text{err}_{c_0} = 100 \cdot \frac{\sigma(\hat{c}_0^*)}{|\hat{c}_0|}$ (in %).

---

## 5.11 PageRank

Standard PageRank on directed citation graph:
$$ \mathbf{PR} = (1-\alpha) \mathbf{1}/n + \alpha \, \mathbf{A}^T \mathbf{D}^{-1} \mathbf{PR} $$

With $\alpha = 0.85$, `max_iter=200`. Uses `networkx.pagerank`.

---

## 5.12 Betweenness Centrality

$$ C_B(v) = \sum_{s \neq v \neq t} \frac{\sigma_{st}(v)}{\sigma_{st}} $$

$\sigma_{st}$: number of shortest paths $s \to t$; $\sigma_{st}(v)$: those passing through $v$. Normalized by $(n-1)(n-2)$ for directed graphs. Uses `networkx.betweenness_centrality` with `normalized=True`.

---

## 5.13 Community Detection

**Leiden** (preferred): `leidenalg.RBConfigurationVertexPartition` with `resolution_parameter` $\gamma$. Stability measured by mean NMI across $n$ runs.

**Louvain:** `community.best_partition` with `resolution=γ`.

**Greedy Modularity:** `nx.algorithms.community.greedy_modularity_communities` on undirected projection.

**NMI (Normalized Mutual Information):** Used to compare partitions for stability. Implementation: `igraph.compare_communities(..., method="NMI")`.

---

## 5.14 Min-Max Scaling (Node Size)

$$ \text{size}_i = \text{lo} + \frac{s_i - s_{\min}}{s_{\max} - s_{\min}} \cdot (\text{hi} - \text{lo}) $$

Default: `lo=5`, `hi=30`. If $s_{\min} = s_{\max}$, returns midpoint.

---

## 5.15 Z-Score (Text Selection)

$$ z_i = \frac{x_i - \bar{x}}{\sigma} $$

With $\sigma$ computed using `ddof=0`. If $\sigma=0$, $z_i=0$.

---

## 5.16 Diversity Score (Reading Lists)

$$ \text{score\_div} = 0.5 \cdot z_{\text{cf}} + 0.3 \cdot z_{\text{use}} + 0.2 \cdot z_{\text{pr}} $$

Used to rank documents for diversity-based reading lists.

---

## 5.17 Quota Distribution (Modo B — Maiores Restos)

For $n$ documents and areas with counts $n_a$:

1. $q_a = \lfloor n \cdot n_a / N \rfloor$
2. Remainder: $r = n - \sum_a q_a$
3. Assign remaining slots to areas with largest fractional parts $(n \cdot n_a / N) - q_a$.

---

## 5.18 Excel Quality Score (excel_analyzer)

**Completeness:** $\frac{1}{5}\sum \mathbf{1}[\text{has\_title}, \text{has\_doi}, \text{has\_year}, \text{has\_author}, \text{has\_area}]$

**Data completeness:** weighted sum of non-null ratios (title 40%, DOI 30%, year 30%).

**Data quality score:**
$$ \text{score} = 0.6 \cdot \text{completeness} + 0.4 \cdot \text{data\_completeness} + 0.1 \cdot \mathbf{1}[\text{has\_metrics}] $$

Capped at 1.0.

---

## 5.19 Fuzzy Deduplication (rapidfuzz)

Uses `fuzz.token_sort_ratio` for name similarity. Names with ratio ≥ threshold (default 95–96) are clustered; canonical form is the first in cluster.

---

## 5.20 BERTopic Pipeline

1. **Embeddings:** `SentenceTransformer` (e.g. `paraphrase-multilingual-MiniLM-L12-v2`).
2. **UMAP:** $n\_components=5$, `n_neighbors=15`, `metric="cosine"`, `min_dist=0`.
3. **HDBSCAN:** `min_cluster_size=15`, `cluster_selection_method="eom"`, `metric="euclidean"`.
4. Topics assigned; probability from BERTopic's `calculate_probabilities=True`.

---

## 5.21 Abstract Inverted Index Reconstruction

OpenAlex stores abstracts as `{token: [positions]}`. Reconstruction:

1. Flatten to `(position, token)` pairs.
2. Sort by position.
3. Join tokens in order.

---

## 5.22 Precision, Recall, F1 (QA Deduplication)

$$ \text{Precision} = \frac{TP}{TP+FP}, \quad \text{Recall} = \frac{TP}{TP+FN}, \quad F_1 = \frac{2 \cdot P \cdot R}{P+R} $$

Binary classification: match (1) vs non-match (0).

---

# 6. Tutorial

## 6.1 Quick Start: Full Bibliometric Analysis

**Step 1 — Prepare input**
- Export from Web of Science (save as .txt) or Scopus (CSV), or use an OpenAlex Works CSV.
- Ensure DOIs are present when possible.

**Step 2 — Run main application**
```bash
python software_gui_pro_4.py
```

**Step 3 — Configure**
- Choose source (WoS or Scopus/OpenAlex).
- Select file.
- Set email (mailto) for OpenAlex API.
- Enable "Expandir citantes" for citation window and self-citation exclusion.
- Set Concept level (0–5), k-window (e.g. 5 years).
- Optional: Exclude self-citations, exclude retractions.
- Choose community algorithm (auto: Leiden → Louvain → Greedy).
- Click **Executar**.

**Step 4 — Output**
- Excel file: `{stem}_metrics_pro.xlsx` with sheets:
  - Records+Metrics
  - Edges
  - Network Metrics
  - Summary (integer)
  - Summary (fractional)
  - Global Dist/Thresholds
  - Run Metadata

---

## 6.2 Querying OpenAlex

```bash
cd Query_OpenAlex
python openalex_query_7.py
```

1. Enter email (mailto).
2. Add search terms (title/abstract; use `|` for OR).
3. Set year range, languages, type filters.
4. Click **Pesquisar**.
5. Export as CSV, BibTeX, or HTML.

---

## 6.3 Converting OpenAlex CSV to Scopus-like

**CLI:**
```bash
python openalex_converter.py "works.csv" "openalex_as_scopus.csv"
```

**GUI:** Run without arguments to open file dialogs.

---

## 6.4 Enriching Authors and Institutions

```bash
python enrich_entities.py ".\dataset_metrics_pro.xlsx" --mailto "you@institution.pt" --concurrency 6
```

Produces: `authors.csv`, `institutions.csv`, `authorships.csv`.

---

## 6.5 Network Visualization

**CLI (viz_network_plus.py):**
```bash
python viz_network_plus.py dataset_metrics_pro.xlsx --out network.html --size pagerank --min_degree 1 --color_by community
```

**GUI (viz_network_interface_2.py):**
```bash
python viz_network_interface_2.py
```
Select Excel, set size/color/min-degree, build, then open HTML.

---

## 6.6 BERTopic Topic Modeling

```bash
python semantic_bertopic_preset.py results.xlsx --model paraphrase-multilingual-MiniLM-L12-v2 --preset default --min_topic_size 15 --out_html sem_bertopic.html
```

Outputs: `bertopic_doc_topics.csv`, `bertopic_topics.csv`, `sem_bertopic.html`.

---

## 6.7 Intelligent Text Selection

```bash
cd "TEXTS SELECT"
python select_texts_gui_v7_intelligent.py
```

1. Choose folder (auto-selects best Excel) or specific file.
2. Optionally run "Analisar Pasta" for recommendations.
3. Select mode: A (1/area), B (quotas), C (global capped), D (N per area).
4. Set N and Max per Area (for C).
5. Execute. Output: Excel with Main_Selection, Top_Per_Area, reading lists (Core, Recent, Bridge, Diversity), download script sheet.

---

## 6.8 Dashboard (Streamlit)

```bash
streamlit run app_dashboard.py
```

1. Upload Excel from main pipeline.
2. Browse tabs: Overview, Metrics & Percentiles, Network HTML, QA Deduplication, Sensitivity.
3. For sensitivity, upload variant Excels and compare Δ MNCS, Δ PP10.

---

# 7. Bibliography

## 7.1 Bibliometrics and Citation Analysis

- **Waltman, L., & van Eck, N. J.** (2012). The field-normalized citation impact indicator (MNCS) and its application to biomedical research. *Scientometrics*, 92(1), 29–42. https://doi.org/10.1007/s11192-011-0576-6

- **Waltman, L., & van Eck, N. J.** (2019). Field-normalized citation impact indicators and the choice of an appropriate counting method. *Journal of Informetrics*, 13(2), 449–463. https://doi.org/10.1016/j.joi.2019.02.005

- **Bornmann, L., & Williams, R.** (2017). The state of h-index research. *EMBO Reports*, 18(2), 163–166. https://doi.org/10.15252/embr.201643483

- **Wouters, P.** (1999). *The citation culture*. Doctoral dissertation, University of Amsterdam. https://dare.uva.nl/search?identifier=a3484a7b-0e34-49b2-a93a-51e24f7c7dca

## 7.2 OpenAlex and Data Sources

- **Priem, J., Piwowar, H., & Orr, R.** (2022). OpenAlex: A fully-open index of scholarly works, authors, institutions, and more. *Research Intelligence*, 1. https://doi.org/10.5937/intell2201001P

- **OpenAlex API Documentation.** (2024). https://docs.openalex.org/

- **Piwowar, H., Priem, J., Larivière, V., Alperin, J. P., Matthias, L., Norlander, B., ... & Haustein, S.** (2018). The state of OA: A large-scale analysis of the prevalence and impact of Open Access articles. *PeerJ*, 6, e4375. https://doi.org/10.7717/peerj.4375

## 7.3 Percentile-Based Indicators

- **Waltman, L., & van Eck, N. J.** (2012). The inconsistency of the h-index. *Journal of the American Society for Information Science and Technology*, 63(2), 406–415. https://doi.org/10.1002/asi.21678

- **Bornmann, L., & Marx, W.** (2014). How to evaluate individual researchers working in the natural and life sciences meaningfully? A proposal of methods based on percentiles of citations. *Scientometrics*, 98(1), 487–509. https://doi.org/10.1007/s11192-013-1161-y

- **Leydesdorff, L., Bornmann, L., & Mingers, J.** (2019). The evaluation of the quality of research. *Journal of Informetrics*, 13(2), 487–488. https://doi.org/10.1016/j.joi.2019.02.016

## 7.4 Network Analysis and Community Detection

- **Page, L., Brin, S., Motwani, R., & Winograd, T.** (1999). The PageRank citation ranking: Bringing order to the web. *Stanford InfoLab*. http://ilpubs.stanford.edu:8090/422/

- **Freeman, L. C.** (1977). A set of measures of centrality based on betweenness. *Sociometry*, 40(1), 35–41. https://doi.org/10.2307/3033543

- **Blondel, V. D., Guillaume, J. L., Lambiotte, R., & Lefebvre, E.** (2008). Fast unfolding of communities in large networks. *Journal of Statistical Mechanics: Theory and Experiment*, 2008(10), P10008. https://doi.org/10.1088/1742-5468/2008/10/P10008

- **Traag, V. A., Waltman, L., & van Eck, N. J.** (2019). From Louvain to Leiden: Guaranteeing well-connected communities. *Scientific Reports*, 9(1), 5233. https://doi.org/10.1038/s41598-019-41695-z

- **Danon, L., Díaz-Guilera, A., Duch, J., & Arenas, A.** (2005). Comparing community structure identification. *Journal of Statistical Mechanics: Theory and Experiment*, 2005(09), P09008. https://doi.org/10.1088/1742-5468/2005/09/P09008

- **Newman, M. E. J.** (2004). Fast algorithm for detecting community structure in networks. *Physical Review E*, 69(6), 066133. https://doi.org/10.1103/PhysRevE.69.066133

## 7.5 Topic Modeling and Embeddings

- **Grootendorst, M.** (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure. *arXiv preprint* arXiv:2203.05794. https://arxiv.org/abs/2203.05794

- **McInnes, L., Healy, J., & Melville, J.** (2018). UMAP: Uniform Manifold Approximation and Projection for dimension reduction. *arXiv preprint* arXiv:1802.03426. https://arxiv.org/abs/1802.03426

- **Campello, R. J. G. B., Moulavi, D., & Sander, J.** (2013). Density-based clustering based on hierarchical density estimates. In *Pacific-Asia Conference on Knowledge Discovery and Data Mining* (pp. 160–172). Springer. https://doi.org/10.1007/978-3-642-37456-2_14

- **Reimers, N., & Gurevych, I.** (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. *Proceedings of EMNLP 2019*, 3982–3992. https://doi.org/10.18653/v1/D19-1410

## 7.6 Fuzzy Matching and Deduplication

- **Cohen, W. W., Ravikumar, P., & Fienberg, S. E.** (2003). A comparison of string distance metrics for name-matching tasks. In *IIWeb 2003* (pp. 73–78). https://www.cs.cmu.edu/~wcohen/postscript/ijcai-ws-2003.pdf

- **RapidFuzz.** (2024). *RapidFuzz: Rapid fuzzy string matching in Python.* https://github.com/maxbachmann/RapidFuzz

## 7.7 Python Libraries

- **Harris, C. R., et al.** (2020). Array programming with NumPy. *Nature*, 585(7825), 357–362. https://doi.org/10.1038/s41586-020-2649-2

- **McKinney, W.** (2010). Data structures for statistical computing in Python. *Proceedings of the 9th Python in Science Conference*, 56–61. https://doi.org/10.25080/Majora-92bf1922-00a

- **Hagberg, A., Swart, P., & S Chult, D.** (2008). Exploring network structure, dynamics, and function using NetworkX. *Los Alamos National Laboratory (LANL)*, LA-UR-08-5495. https://doi.org/10.25390/CORNELL.5246163

- **Reitz, K.** (2024). *Requests: HTTP for Humans.* https://requests.readthedocs.io/

## 7.8 Web of Science and Scopus

- **Clarivate.** (2024). *Web of Science.* https://clarivate.com/products/web-of-science/

- **Elsevier.** (2024). *Scopus.* https://www.scopus.com/

- **Harzing, A. W.** (2007). Publish or Perish. https://harzing.com/resources/publish-or-perish

---

**Document version:** 1.0  
**Last updated:** March 2025  
**Project:** Bibliometric analysis_15
