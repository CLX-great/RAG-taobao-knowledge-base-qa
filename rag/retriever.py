"""Small dependency-free TF-IDF retriever for the project's local knowledge base."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    source: str
    chunk_id: int


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source: str
    chunk_id: int
    score: float


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def load_chunks(directory: Path, chunk_size: int = 500, overlap: int = 80) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        start = 0
        chunk_id = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(DocumentChunk(chunk_text, str(path), chunk_id))
                chunk_id += 1
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks


class TfidfRetriever:
    def __init__(self, chunks: Iterable[DocumentChunk]) -> None:
        self.chunks = list(chunks)
        self._document_frequency: dict[str, int] = {}
        self._vectors: list[dict[str, float]] = []
        for chunk in self.chunks:
            counts: dict[str, int] = {}
            for token in set(tokenize(chunk.text)):
                counts[token] = counts.get(token, 0) + 1
            for token in counts:
                self._document_frequency[token] = self._document_frequency.get(token, 0) + 1
            self._vectors.append(counts)

    def search(self, query: str, limit: int = 4) -> list[RetrievedChunk]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        query_counts = {token: query_tokens.count(token) for token in set(query_tokens)}
        document_count = max(len(self.chunks), 1)
        query_vector = {
            token: count * math.log((document_count + 1) / (self._document_frequency.get(token, 0) + 1))
            for token, count in query_counts.items()
        }
        query_norm = math.sqrt(sum(value * value for value in query_vector.values())) or 1.0

        scored: list[RetrievedChunk] = []
        for chunk, counts in zip(self.chunks, self._vectors):
            vector = {
                token: count * math.log((document_count + 1) / (self._document_frequency.get(token, 0) + 1))
                for token, count in counts.items()
            }
            vector_norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
            score = sum(query_vector.get(token, 0.0) * value for token, value in vector.items())
            score /= query_norm * vector_norm
            # Keep rare-term matches useful even when a query term is common
            # across the small local corpus and therefore has zero IDF.
            overlap = len(set(query_tokens) & set(counts))
            if overlap:
                score += overlap / max(len(set(query_tokens)), 1) * 0.01
            if score > 0:
                scored.append(RetrievedChunk(chunk.text, chunk.source, chunk.chunk_id, score))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]
