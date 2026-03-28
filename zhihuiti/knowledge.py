"""知识库 — Knowledge Base with TF-IDF-like retrieval.

Provides ingestion, storage, querying, and pruning of knowledge chunks.
Chunks are stored in SQLite via the Memory layer and retrieved using
a simple TF-IDF keyword matching approach (no external embedding deps).

Usage:
    kb = KnowledgeBase(memory)
    kb.ingest_file("notes.md")
    results = kb.query("how to optimize trading")
    kb.prune(min_confidence=0.3, max_age_days=90)
"""

from __future__ import annotations

import json
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zhihuiti.models import KnowledgeChunk

if TYPE_CHECKING:
    from zhihuiti.memory import Memory

console = Console()

# ---------------------------------------------------------------------------
# Text processing helpers
# ---------------------------------------------------------------------------

# Common English stop words for TF-IDF filtering
_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for on with "
    "at by from as into through during before after above below between "
    "out off over under again further then once here there when where "
    "why how all each every both few more most other some such no nor "
    "not only own same so than too very and but if or because until "
    "while about this that these those it its he she they we you i me "
    "him her them my your his our their what which who whom".split()
)

_WORD_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]+")


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, filtering stop words."""
    words = _WORD_RE.findall(text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _term_freq(tokens: list[str]) -> dict[str, float]:
    """Compute normalized term frequency for a token list."""
    counts = Counter(tokens)
    if not counts:
        return {}
    max_count = max(counts.values())
    return {t: c / max_count for t, c in counts.items()}


def _idf(term: str, doc_token_sets: list[set[str]]) -> float:
    """Compute smoothed inverse document frequency for a term across documents."""
    n = len(doc_token_sets)
    if n == 0:
        return 0.0
    df = sum(1 for doc in doc_token_sets if term in doc)
    if df == 0:
        return 0.0
    # Smoothed IDF: always positive even with single document
    return math.log(1 + n / df)


def _tfidf_score(query_tokens: list[str], doc_tokens: list[str],
                 doc_token_sets: list[set[str]]) -> float:
    """Score a document against a query using TF-IDF."""
    if not query_tokens or not doc_tokens:
        return 0.0
    tf = _term_freq(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        if qt in tf:
            score += tf[qt] * _idf(qt, doc_token_sets)
    return score


# ---------------------------------------------------------------------------
# Markdown / text splitting
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)", re.MULTILINE)


def _split_markdown(text: str, source: str = "") -> list[KnowledgeChunk]:
    """Split markdown text into chunks on headers/sections."""
    chunks: list[KnowledgeChunk] = []

    # Find all header positions
    headers = list(_HEADER_RE.finditer(text))

    if not headers:
        # No headers — treat as single chunk
        content = text.strip()
        if content:
            chunks.append(KnowledgeChunk(
                id=uuid.uuid4().hex[:12],
                source=source,
                title="(untitled)",
                content=content,
                chunk_type="markdown",
            ))
        return chunks

    # Add content before first header if any
    pre = text[:headers[0].start()].strip()
    if pre:
        chunks.append(KnowledgeChunk(
            id=uuid.uuid4().hex[:12],
            source=source,
            title="(preamble)",
            content=pre,
            chunk_type="markdown",
        ))

    for i, match in enumerate(headers):
        title = match.group(2).strip()
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        content = text[start:end].strip()
        if content:
            chunks.append(KnowledgeChunk(
                id=uuid.uuid4().hex[:12],
                source=source,
                title=title,
                content=content,
                chunk_type="markdown",
            ))

    return chunks


def _split_plain(text: str, source: str = "",
                 max_chunk_size: int = 1500) -> list[KnowledgeChunk]:
    """Split plain text into chunks by paragraphs or size."""
    chunks: list[KnowledgeChunk] = []
    paragraphs = re.split(r"\n\s*\n", text)

    current = ""
    idx = 0
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) > max_chunk_size and current:
            chunks.append(KnowledgeChunk(
                id=uuid.uuid4().hex[:12],
                source=source,
                title=f"section-{idx}",
                content=current.strip(),
                chunk_type="text",
            ))
            idx += 1
            current = ""
        current += para + "\n\n"

    if current.strip():
        chunks.append(KnowledgeChunk(
            id=uuid.uuid4().hex[:12],
            source=source,
            title=f"section-{idx}",
            content=current.strip(),
            chunk_type="text",
        ))

    return chunks


# ---------------------------------------------------------------------------
# KnowledgeBase
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """Knowledge ingestion, storage, and TF-IDF retrieval engine.

    Uses the Memory SQLite layer for persistence and provides:
      - store()       — save a single KnowledgeChunk
      - query()       — TF-IDF keyword search across all chunks
      - ingest_file() — split and store a markdown/text file
      - prune()       — remove old or low-confidence chunks
    """

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store(self, chunk: KnowledgeChunk) -> str:
        """Persist a KnowledgeChunk to the database. Returns the chunk id."""
        with self.memory._lock:
            self.memory.conn.execute(
                """INSERT OR REPLACE INTO knowledge_chunks
                   (id, source, title, content, chunk_type, tags, confidence, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    chunk.id,
                    chunk.source,
                    chunk.title,
                    chunk.content,
                    chunk.chunk_type,
                    json.dumps(chunk.tags),
                    chunk.confidence,
                    json.dumps(chunk.metadata),
                ),
            )
            self.memory.conn.commit()
        return chunk.id

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, text: str, top_k: int = 5,
              min_confidence: float = 0.0) -> list[KnowledgeChunk]:
        """Search knowledge chunks using TF-IDF keyword matching.

        Args:
            text: The search query string.
            top_k: Maximum number of results to return.
            min_confidence: Minimum confidence threshold for results.

        Returns:
            A list of KnowledgeChunk objects ranked by relevance.
        """
        query_tokens = _tokenize(text)
        if not query_tokens:
            return []

        rows = self.memory._query(
            "SELECT id, source, title, content, chunk_type, tags, "
            "confidence, metadata, created_at FROM knowledge_chunks "
            "WHERE confidence >= ?",
            (min_confidence,),
        )

        if not rows:
            return []

        # Build token sets for IDF computation
        doc_data: list[tuple[dict, list[str], set[str]]] = []
        for row in rows:
            tokens = _tokenize(row["title"] + " " + row["content"])
            doc_data.append((dict(row), tokens, set(tokens)))

        doc_token_sets = [d[2] for d in doc_data]

        # Score each document
        scored: list[tuple[float, dict]] = []
        for row_dict, tokens, token_set in doc_data:
            score = _tfidf_score(query_tokens, tokens, doc_token_sets)
            if score > 0:
                scored.append((score, row_dict))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[KnowledgeChunk] = []
        for _score, row_dict in scored[:top_k]:
            results.append(KnowledgeChunk(
                id=row_dict["id"],
                source=row_dict["source"],
                title=row_dict["title"],
                content=row_dict["content"],
                chunk_type=row_dict["chunk_type"],
                tags=json.loads(row_dict["tags"]) if row_dict["tags"] else [],
                confidence=row_dict["confidence"],
                created_at=row_dict["created_at"] or "",
                metadata=json.loads(row_dict["metadata"]) if row_dict["metadata"] else {},
            ))

        return results

    # ------------------------------------------------------------------
    # Ingest file
    # ------------------------------------------------------------------

    def ingest_file(self, file_path: str, tags: list[str] | None = None,
                    confidence: float = 0.5) -> list[str]:
        """Split a markdown or text file into chunks and store them.

        Args:
            file_path: Path to the file to ingest.
            tags: Optional tags to apply to all chunks.
            confidence: Default confidence for ingested chunks.

        Returns:
            List of chunk IDs that were stored.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        text = path.read_text(encoding="utf-8", errors="replace")
        source = str(path.resolve())

        # Choose splitter based on extension
        if path.suffix.lower() in (".md", ".markdown"):
            chunks = _split_markdown(text, source=source)
        else:
            chunks = _split_plain(text, source=source)

        # Apply tags and confidence
        ids: list[str] = []
        for chunk in chunks:
            chunk.tags = tags or []
            chunk.confidence = confidence
            self.store(chunk)
            ids.append(chunk.id)

        return ids

    # ------------------------------------------------------------------
    # Prune
    # ------------------------------------------------------------------

    def prune(self, min_confidence: float = 0.3,
              max_age_days: int = 90) -> int:
        """Remove low-confidence or old chunks.

        Args:
            min_confidence: Remove chunks below this confidence.
            max_age_days: Remove chunks older than this many days.

        Returns:
            Number of chunks deleted.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()

        with self.memory._lock:
            cursor = self.memory.conn.execute(
                "DELETE FROM knowledge_chunks "
                "WHERE confidence < ? OR created_at < ?",
                (min_confidence, cutoff),
            )
            deleted = cursor.rowcount
            self.memory.conn.commit()

        return deleted

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int | float]:
        """Return summary statistics about the knowledge base."""
        row = self.memory._query_one(
            "SELECT COUNT(*) as total, "
            "COALESCE(AVG(confidence), 0) as avg_confidence, "
            "COUNT(DISTINCT source) as sources "
            "FROM knowledge_chunks"
        )
        if row:
            return {
                "total_chunks": row["total"],
                "avg_confidence": round(row["avg_confidence"], 3),
                "unique_sources": row["sources"],
            }
        return {"total_chunks": 0, "avg_confidence": 0.0, "unique_sources": 0}

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def print_report(self) -> None:
        """Print a summary report of the knowledge base."""
        stats = self.get_stats()
        console.print(Panel(
            f"  Chunks: {stats['total_chunks']}\n"
            f"  Sources: {stats['unique_sources']}\n"
            f"  Avg confidence: {stats['avg_confidence']:.3f}",
            title="知识库 Knowledge Base",
            border_style="blue",
        ))

        # Show recent chunks
        rows = self.memory._query(
            "SELECT id, source, title, chunk_type, confidence, created_at "
            "FROM knowledge_chunks ORDER BY created_at DESC LIMIT 10"
        )
        if rows:
            table = Table(title="Recent Chunks")
            table.add_column("ID", style="dim")
            table.add_column("Title")
            table.add_column("Source", style="cyan", max_width=30)
            table.add_column("Type")
            table.add_column("Confidence", justify="right")
            for r in rows:
                src = (r["source"] or "")
                if len(src) > 30:
                    src = "..." + src[-27:]
                table.add_row(
                    r["id"],
                    r["title"] or "",
                    src,
                    r["chunk_type"],
                    f"{r['confidence']:.2f}",
                )
            console.print(table)
