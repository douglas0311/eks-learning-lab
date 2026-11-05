variable "aws_region" {
  description = "AWS region of the existing vector index."
  type        = string
}

variable "aws_account_id" {
  description = "Expected AWS account; prevents planning against the wrong account."
  type        = string
}

variable "environment" {
  description = "Environment name used in resource names and tags."
  type        = string
}

variable "vector_bucket_name" {
  description = "Existing vector bucket; dependency only."
  type        = string
}

variable "vector_index_name" {
  description = "Existing index; dependency only."
  type        = string
}

variable "embedding_model_id" {
  description = "Must match the ingestor embedding model."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
  validation {
    condition     = var.embedding_model_id == "amazon.titan-embed-text-v2:0"
    error_message = "Phase 5A requires the ingestion Titan Text Embeddings V2 model."
  }
}

variable "embedding_dimensions" {
  description = "Must match the existing index and ingestor."
  type        = number
  default     = 1024
  validation {
    condition     = contains([256, 512, 1024], var.embedding_dimensions)
    error_message = "Titan V2 dimensions must be 256, 512, or 1024 and match ingestion."
  }
}

variable "top_k" {
  description = "Default nearest-neighbor count; lab limit 1–100."
  type        = number
  default     = 3
  validation {
    condition     = var.top_k >= 1 && var.top_k <= 100 && floor(var.top_k) == var.top_k
    error_message = "top_k must be an integer between 1 and 100."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 7
}

variable "function_name" {
  description = "Name of the query Lambda function."
  type        = string
}

variable "generation_model_id" {
  description = "Verified Nova Micro US inference profile used for grounded answers."
  type        = string
  default     = "us.amazon.nova-micro-v1:0"
  validation {
    condition     = var.generation_model_id == "us.amazon.nova-micro-v1:0"
    error_message = "Phase 5B uses only the directly tested Nova Micro profile."
  }
}

variable "generation_max_tokens" {
  description = "Maximum answer output tokens; bounds lab cost and response length."
  type        = number
  default     = 512
  validation {
    condition     = var.generation_max_tokens >= 64 && var.generation_max_tokens <= 1024 && floor(var.generation_max_tokens) == var.generation_max_tokens
    error_message = "generation_max_tokens must be an integer between 64 and 1024."
  }
}
