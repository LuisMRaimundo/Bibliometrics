# -*- coding: utf-8 -*-
"""
semantic_bertopic_preset.py — BERTopic com presets reprodutíveis

Saída:
  - sem_bertopic.html
  - bertopic_doc_topics.csv  (doc_id, topic, probability?)
  - bertopic_topics.csv      (Topic, Name, Count, ...)

Uso típico:
  python semantic_bertopic_preset.py results.xlsx \
    --model paraphrase-multilingual-MiniLM-L12-v2 \
    --language multilingual \
    --preset default \
    --min_topic_size 15 \
    --out_html sem_bertopic.html
"""

import argparse, random, sys
from pathlib import Path

import numpy as np
import pandas as pd

# --- guardas de dependências, com mensagens claras ---
try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    raise SystemExit("Falta 'sentence-transformers' (pip install sentence-transformers).") from e

try:
    import umap
except Exception as e:
    raise SystemExit("Falta 'umap-learn' (pip install umap-learn).") from e

try:
    import hdbscan
except Exception as e:
    raise SystemExit("Falta 'hdbscan' (pip install hdbscan).") from e

try:
    from bertopic import BERTopic
except Exception as e:
    raise SystemExit("Falta 'bertopic' (pip install bertopic).") from e


# --------------------- presets de hiperparâmetros ---------------------
def get_preset(name: str):
    name = (name or "default").lower()
    presets = {
        "default": {
            "umap": dict(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42),
            "hdb": dict(min_cluster_size=15, metric="euclidean", cluster_selection_method="eom", prediction_data=True)
        },
        "coarse": {
            "umap": dict(n_neighbors=10, n_components=5, min_dist=0.05, metric="cosine", random_state=42),
            "hdb": dict(min_cluster_size=30, metric="euclidean", cluster_selection_method="eom", prediction_data=True)
        },
        "fine": {
            "umap": dict(n_neighbors=25, n_components=5, min_dist=0.0, metric="cosine", random_state=42),
            "hdb": dict(min_cluster_size=8, metric="euclidean", cluster_selection_method="eom", prediction_data=True)
        },
    }
    return presets.get(name, presets["default"])


# --------------------- leitura/limpeza de documentos ---------------------
def load_docs(xlsx_path: str):
    """Extrai docs textuais a partir de Records+Metrics: concatena title + abstract (quando existirem)."""
    rec = pd.read_excel(xlsx_path, sheet_name="Records+Metrics")
    # Colunas que podem existir nas exportações do núcleo
    has_title = "title" in rec.columns
    has_abs = "abstract" in rec.columns

    # construir texto
    def mk_text(row):
        parts = []
        if has_title and isinstance(row.get("title"), str):
            parts.append(row["title"])
        if has_abs and isinstance(row.get("abstract"), str):
            parts.append(row["abstract"])
        return " ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())

    texts = rec.apply(mk_text, axis=1).astype(str)
    doc_ids = rec["idx"] if "idx" in rec.columns else pd.Series(range(len(texts)), name="idx")
    # filtrar vazios
    mask = texts.str.strip().astype(bool)
    return rec, texts[mask].tolist(), doc_ids[mask].tolist(), (~mask).sum()


# --------------------- main ---------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", help="Excel exportado pelo núcleo (Records+Metrics)")
    ap.add_argument("--model", default="paraphrase-multilingual-MiniLM-L12-v2",
                    help="Modelo Sentence-Transformers")
    ap.add_argument("--language", default="multilingual",
                    help="Idioma para BERTopic (e.g., 'multilingual', 'english', 'portuguese')")
    ap.add_argument("--preset", default="default", choices=["default", "coarse", "fine"])
    ap.add_argument("--min_topic_size", type=int, default=None, help="Override para min_cluster_size do HDBSCAN")
    ap.add_argument("--out_html", default="sem_bertopic.html", help="HTML de saída (dashboard procura este nome)")
    args = ap.parse_args()

    # Reprodutibilidade global
    random.seed(42)
    np.random.seed(42)

    # Carregar corpus
    try:
        rec, docs, doc_ids, n_empty = load_docs(args.xlsx)
    except Exception as e:
        raise SystemExit(f"Falha a ler '{args.xlsx}' (sheet 'Records+Metrics'): {e}")

    if len(docs) < 5:
        raise SystemExit(f"Corpus demasiado pequeno para BERTopic (docs úteis={len(docs)}, vazios/sem texto={n_empty}).")

    if n_empty > 0:
        print(f"[info] {n_empty} registos sem texto útil (title/abstract ausentes). Continuando com {len(docs)} docs.", file=sys.stderr)

    # Embeddings
    model = SentenceTransformer(args.model)
    emb = model.encode(docs, show_progress_bar=True)

    # Preset + overrides
    p = get_preset(args.preset)
    um = umap.UMAP(**p["umap"])
    hs = hdbscan.HDBSCAN(**p["hdb"])
    if args.min_topic_size:
        hs.min_cluster_size = int(args.min_topic_size)

    # BERTopic
    topic_model = BERTopic(
        umap_model=um,
        hdbscan_model=hs,
        language=args.language,
        calculate_probabilities=True,
        verbose=True
    )
    topics, probs = topic_model.fit_transform(docs, embeddings=emb)

    # CSV de atribuições
    df_doc = pd.DataFrame({"doc_id": doc_ids, "topic": topics})
    if probs is not None:
        try:
            # probs pode ser array (n_docs, n_topics) ou lista; extrair prob. máx. por doc
            max_prob = np.max(probs, axis=1) if hasattr(probs, "shape") else [float(p) for p in probs]
            df_doc["probability"] = max_prob
        except Exception:
            pass
    df_doc.to_csv("bertopic_doc_topics.csv", index=False)

    # CSV de tópicos
    info = topic_model.get_topic_info()
    info.to_csv("bertopic_topics.csv", index=False)

    # HTML (robusto; não falha o run)
    try:
        fig = topic_model.visualize_topics()
        fig.write_html(args.out_html, include_plotlyjs="cdn")
    except Exception as e:
        print("[aviso] Falha ao gerar HTML:", e, file=sys.stderr)

    # Log final
    try:
        n_topics = int(info[info["Topic"] != -1].shape[0]) if "Topic" in info.columns else int(info[info["topic"] != -1].shape[0])
    except Exception:
        n_topics = int(info.shape[0])
    print("✔ BERTopic concluído:", {"n_docs": len(docs), "n_topics": n_topics})


if __name__ == "__main__":
    main()
