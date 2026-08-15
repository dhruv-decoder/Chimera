"""Retrieval over the fraud-intelligence corpus.

The corpus is the taxonomy (each technique as a document) plus curated,
source-cited intel notes in ``corpus/*.md``. Retrieval is TF-IDF cosine by
default: fully offline, no model download, and more than adequate for a
few-dozen-document knowledge base - which keeps the deployed footprint inside
free-tier limits. The ``Retriever`` interface is deliberately small so it can be
swapped for sentence-transformer or hosted embeddings in production (noted in the
write-up as a quality upgrade).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..config import CORPUS_DIR
from .taxonomy import TECHNIQUES


@dataclass
class Document:
    id: str
    title: str
    text: str
    tags: List[str]
    sources: List[str]


def _parse_md(path: Path) -> Document:
    raw = path.read_text()
    title, tags, sources, body = path.stem, [], [], raw
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if m:
        front, body = m.group(1), m.group(2)
        for line in front.splitlines():
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip()
            elif line.strip().startswith("- http"):
                sources.append(line.strip()[2:])
            elif line.startswith("tags:"):
                tags = re.findall(r"[\w\-]+", line.split(":", 1)[1])
    return Document(id=path.stem, title=title, text=f"{title}\n{body}", tags=tags, sources=sources)


def build_corpus() -> List[Document]:
    docs: List[Document] = []
    # Taxonomy techniques as documents.
    for t in TECHNIQUES:
        text = (f"{t.name}. {t.summary} GenAI role: {t.genai_role} "
                f"Kill chain: {'; '.join(t.kill_chain)}. "
                f"Signatures: {'; '.join(t.signatures)}. Tactic: {t.tactic}. "
                f"Rails: {', '.join(t.rails)}.")
        docs.append(Document(id=t.id, title=t.name, text=text,
                             tags=[t.tactic] + t.rails + t.channels, sources=t.references))
    # Curated intel notes.
    if CORPUS_DIR.exists():
        for p in sorted(CORPUS_DIR.glob("*.md")):
            docs.append(_parse_md(p))
    return docs


class Retriever:
    def __init__(self) -> None:
        self.docs = build_corpus()
        self._vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        self._mat = self._vec.fit_transform([d.text for d in self.docs])

    def query(self, text: str, k: int = 4) -> List[dict]:
        q = self._vec.transform([text])
        sims = cosine_similarity(q, self._mat)[0]
        order = np.argsort(-sims)[:k]
        out = []
        for i in order:
            d = self.docs[i]
            out.append({"id": d.id, "title": d.title, "score": round(float(sims[i]), 4),
                        "snippet": d.text[:400], "sources": d.sources, "tags": d.tags})
        return out


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
