"""
Phase 4 — Knowledge Base Ingestion Pipeline
Lambda handler: PDF extraction → chunking → Bedrock embeddings → S3 Vectors

Phase 3 responsibility (still present):
  - Receive S3 ObjectCreated event
  - Log bucket name and object key

Phase 4 additions:
  - Download PDF from S3
  - Extract text with pypdf (text-based PDFs only; image-only PDFs logged and skipped)
  - Split text into overlapping fixed-size chunks
  - Generate one embedding per chunk via Amazon Bedrock Titan Embed Text V2
  - Write vectors to S3 Vectors with deterministic keys (idempotent re-processing)
  - Store chunk text and source metadata alongside each vector

Not implemented here (later phases):
  - Query / retrieval
  - LLM answer generation
  - Re-ranking
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import urllib.parse
from io import BytesIO
from typing import Generator

import boto3
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Environment-driven configuration
# All values are required at runtime; Lambda will log a clear error on startup
# if any are missing.
# ---------------------------------------------------------------------------
VECTOR_BUCKET_NAME: str = os.environ["VECTOR_BUCKET_NAME"]
VECTOR_INDEX_NAME: str = os.environ["VECTOR_INDEX_NAME"]
EMBEDDING_MODEL_ID: str = os.environ.get(
    "EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
)
EMBEDDING_DIMENSIONS: int = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
AWS_REGION: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# Chunking parameters — tuned for engineering runbook PDFs.
# 800 chars ≈ ~200 tokens (well within Titan's 8192-token limit per chunk).
# 200-char overlap preserves sentence context across chunk boundaries.
CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", "800"))
CHUNK_OVERLAP: int = int(os.environ.get("CHUNK_OVERLAP", "200"))

# ---------------------------------------------------------------------------
# AWS clients — initialised outside the handler for connection reuse across
# warm invocations.
# ---------------------------------------------------------------------------
s3_client = boto3.client("s3")
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
s3vectors_client = boto3.client("s3vectors", region_name=AWS_REGION)


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_bytes: bytes, object_key: str) -> tuple[str, int]:
    """
    Extract all text from a PDF byte stream using pypdf.

    Returns
    -------
    (full_text, page_count)

    Raises
    ------
    ValueError  — if the PDF contains no extractable text (image-only / scanned).
    Exception   — propagated as-is for other pypdf errors.
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    pages_text: list[str] = []

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
            pages_text.append(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "PDF page extraction error | key=%s | page=%d | error=%s",
                object_key,
                page_num,
                exc,
            )
            pages_text.append("")

    full_text = "\n".join(pages_text)

    # Normalise whitespace — collapse runs of blank lines and trim edges.
    full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()

    if not full_text:
        raise ValueError(
            f"PDF contains no extractable text (image-only or encrypted): {object_key}"
        )

    logger.info(
        "PDF extracted | key=%s | pages=%d | chars=%d",
        object_key,
        page_count,
        len(full_text),
    )
    return full_text, page_count


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> Generator[str, None, None]:
    """
    Yield fixed-size overlapping text chunks.

    Strategy: slide a window of `chunk_size` characters across the text,
    advancing by `(chunk_size - overlap)` characters each step.
    Chunks are trimmed of leading/trailing whitespace and empty chunks are
    skipped.

    This is intentionally simple — the goal for Phase 4 is a working
    pipeline, not optimised chunking.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    step = chunk_size - overlap
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            yield chunk
        start += step


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def embed_text(text: str) -> list[float]:
    """
    Call Amazon Bedrock Titan Embed Text V2 and return the embedding vector.

    The text is truncated to 20000 chars before sending (Titan's ~8192-token
    hard limit corresponds to roughly 25000-30000 chars for English text; we
    stay well within it).
    """
    body = json.dumps(
        {
            "inputText": text[:20_000],
            "dimensions": EMBEDDING_DIMENSIONS,
            "normalize": True,
        }
    )

    response = bedrock_runtime.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    result = json.loads(response["body"].read())
    return result["embedding"]


# ---------------------------------------------------------------------------
# Deterministic vector key
# ---------------------------------------------------------------------------

def vector_key(object_key: str, chunk_index: int) -> str:
    """
    Build a deterministic, stable vector key from the S3 object key and
    chunk index.

    Using a SHA-256 prefix + human-readable suffix keeps keys:
      - Unique per (document, chunk) pair
      - Idempotent: re-processing the same object produces the same keys,
        so PutVectors overwrites existing entries rather than duplicating them.
      - Safe for S3 Vectors key constraints (alphanumeric + hyphens, ≤512 chars)

    Example: "a3f2c1d8-report-2024-q1-pdf-chunk-0003"
    """
    raw = f"{object_key}::{chunk_index}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:8]

    # Build a readable suffix from the object key (strip path, replace
    # non-alphanumeric chars with hyphens, limit length).
    basename = object_key.split("/")[-1]
    safe_name = re.sub(r"[^a-z0-9]+", "-", basename.lower())[:40].strip("-")

    return f"{digest}-{safe_name}-chunk-{chunk_index:04d}"


# ---------------------------------------------------------------------------
# S3 Vectors write
# ---------------------------------------------------------------------------

def put_vectors(vectors: list[dict]) -> None:
    """
    Write a batch of vectors to the configured S3 Vectors index.

    Each item in `vectors` follows the PutVectors API shape:
        {
            "key":      str,
            "data":     {"float32": [float, ...]},
            "metadata": {...}
        }

    S3 Vectors PutVectors is idempotent: if a key already exists in the
    index, the existing entry is overwritten. This is the primary mechanism
    for idempotency when the same PDF is re-uploaded.

    The API accepts up to 100 vectors per call. We batch at 10 to stay well
    within request-size limits (1024-dim float32 vectors are ~4KB each).
    """
    BATCH_SIZE = 10
    total = len(vectors)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = vectors[batch_start : batch_start + BATCH_SIZE]

        s3vectors_client.put_vectors(
            vectorBucketName=VECTOR_BUCKET_NAME,
            indexName=VECTOR_INDEX_NAME,
            vectors=batch,
        )

        logger.info(
            "PutVectors batch written | index=%s | batch=%d-%d | total=%d",
            VECTOR_INDEX_NAME,
            batch_start,
            batch_start + len(batch) - 1,
            total,
        )


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

def handler(event: dict, context) -> dict:  # noqa: ANN001
    """
    Entry point for S3 ObjectCreated events.

    Flow:
      1. Parse the S3 event record.
      2. Download the PDF from S3.
      3. Extract text from the PDF.
      4. Chunk the text.
      5. Embed each chunk via Bedrock.
      6. Write vectors to S3 Vectors.

    A single Lambda invocation processes one S3 event (which typically
    contains one record for ObjectCreated notifications). Multiple records
    are handled sequentially.
    """
    logger.info("Phase 4 KB ingestor invoked | event=%s", json.dumps(event))

    records = event.get("Records", [])
    if not records:
        logger.warning("Event contained no Records. Nothing to process.")
        return {"statusCode": 200, "body": "no records"}

    results = []

    for record in records:
        event_name = record.get("eventName", "unknown")
        s3_info = record.get("s3", {})
        bucket_name = s3_info.get("bucket", {}).get("name", "unknown")
        raw_key = s3_info.get("object", {}).get("key", "unknown")
        object_key = urllib.parse.unquote_plus(raw_key)
        object_size = s3_info.get("object", {}).get("size", -1)

        logger.info(
            "Processing S3 event | event=%s | bucket=%s | key=%s | size_bytes=%d",
            event_name,
            bucket_name,
            object_key,
            object_size,
        )

        try:
            result = _process_document(bucket_name, object_key)
            results.append(result)

        except ValueError as exc:
            # Image-only PDF or no extractable text — log and continue.
            logger.error(
                "Document skipped | key=%s | reason=%s", object_key, exc
            )
            results.append(
                {
                    "key": object_key,
                    "status": "skipped",
                    "reason": str(exc),
                }
            )

        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Document ingestion failed | key=%s | error=%s", object_key, exc
            )
            results.append(
                {
                    "key": object_key,
                    "status": "error",
                    "reason": str(exc),
                }
            )

    return {
        "statusCode": 200,
        "body": json.dumps({"records_processed": len(results), "results": results}),
    }


def _process_document(bucket_name: str, object_key: str) -> dict:
    """
    Full ingestion pipeline for a single S3 object.

    Returns a summary dict with chunk and vector counts.
    """
    # ------------------------------------------------------------------
    # Step 1: Download PDF
    # ------------------------------------------------------------------
    logger.info("Downloading PDF | bucket=%s | key=%s", bucket_name, object_key)
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    pdf_bytes = s3_response["Body"].read()
    logger.info(
        "Download complete | key=%s | bytes=%d", object_key, len(pdf_bytes)
    )

    # ------------------------------------------------------------------
    # Step 2: Extract text
    # ------------------------------------------------------------------
    full_text, page_count = extract_text_from_pdf(pdf_bytes, object_key)

    # ------------------------------------------------------------------
    # Step 3: Chunk
    # ------------------------------------------------------------------
    chunks = list(chunk_text(full_text))
    chunk_count = len(chunks)
    logger.info(
        "Chunking complete | key=%s | chunks=%d | chunk_size=%d | overlap=%d",
        object_key,
        chunk_count,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
    )

    if chunk_count == 0:
        raise ValueError(f"No chunks produced for {object_key} — text may be too short.")

    # ------------------------------------------------------------------
    # Step 4 + 5: Embed each chunk and prepare PutVectors payloads
    # ------------------------------------------------------------------
    # Derive a stable document name for metadata (basename without extension).
    doc_name = object_key.split("/")[-1]

    vectors: list[dict] = []

    for chunk_index, chunk_text_value in enumerate(chunks):
        logger.info(
            "Embedding chunk | key=%s | chunk=%d/%d",
            object_key,
            chunk_index + 1,
            chunk_count,
        )

        embedding = embed_text(chunk_text_value)

        vectors.append(
            {
                "key": vector_key(object_key, chunk_index),
                "data": {"float32": embedding},
                # Metadata stored alongside each vector.
                # Kept minimal: enough to identify the source document and
                # retrieve the chunk text for answer generation in Phase 5.
                "metadata": {
                    "source_bucket": bucket_name,
                    "source_key": object_key,
                    "document_name": doc_name,
                    "chunk_index": chunk_index,
                    "chunk_total": chunk_count,
                    "page_count": page_count,
                    # Chunk text is stored here so Phase 5 retrieval does not
                    # need a separate S3 round-trip.  Truncated to 2000 chars
                    # to stay within S3 Vectors metadata size limits (~4KB).
                    "chunk_text": chunk_text_value[:2000],
                },
            }
        )

    # ------------------------------------------------------------------
    # Step 6: Write to S3 Vectors
    # ------------------------------------------------------------------
    put_vectors(vectors)

    logger.info(
        "Ingestion complete | key=%s | pages=%d | chunks=%d | vectors_written=%d",
        object_key,
        page_count,
        chunk_count,
        len(vectors),
    )

    return {
        "key": object_key,
        "status": "ok",
        "pages": page_count,
        "chunks": chunk_count,
        "vectors_written": len(vectors),
    }
