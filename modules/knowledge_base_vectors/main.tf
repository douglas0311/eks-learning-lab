# -----------------------------------------------------------------------
# Phase 4 — S3 Vectors Module
#
# Creates the vector bucket and vector index used by the knowledge base
# ingestion pipeline.
#
# Notes:
#   - Vector bucket and index names must be globally unique within the
#     account/region combination.
#   - After an index is created, dimension, distance_metric, and
#     index_name cannot be changed without destroying and recreating it
#     (which also destroys all stored vectors).
#   - SSE is always enabled on vector buckets (AES256 by default).
# -----------------------------------------------------------------------

resource "aws_s3vectors_vector_bucket" "kb" {
  vector_bucket_name = var.vector_bucket_name

  encryption_configuration {
    sse_type = "AES256"
  }

  # force_destroy allows terraform destroy to succeed even when the bucket
  # still contains vectors. Safe for a PoC; set to false in production.
  force_destroy = var.force_destroy

  tags = {
    Name        = var.vector_bucket_name
    Environment = var.environment
  }
}

resource "aws_s3vectors_index" "kb" {
  vector_bucket_name = aws_s3vectors_vector_bucket.kb.vector_bucket_name
  index_name         = var.vector_index_name

  # Must match the embedding model output dimensions exactly.
  # amazon.titan-embed-text-v2:0 at 1024 dims → set dimension = 1024.
  dimension = var.vector_dimension

  # float32 is the native type for Titan Embed V2 output.
  data_type = "float32"

  # Cosine similarity is the standard for semantic/embedding search.
  distance_metric = "cosine"

  tags = {
    Name        = var.vector_index_name
    Environment = var.environment
  }
}
