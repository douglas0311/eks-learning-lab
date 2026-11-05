variable "aws_region" {
  description = "AWS region where Lambda and CloudWatch resources are deployed."
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID. Used to scope IAM and resource-based policy ARNs."
  type        = string
}

variable "project_name" {
  description = "Project name used in resource names and tags."
  type        = string
}

variable "environment" {
  description = "Environment name used in resource names and tags."
  type        = string
}

variable "function_name" {
  description = "Name of the Lambda function."
  type        = string
}

variable "source_bucket_name" {
  description = "Name of the existing S3 knowledge-source bucket."
  type        = string
}

variable "source_bucket_arn" {
  description = "ARN of the existing S3 knowledge-source bucket."
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days for the Lambda log group."
  type        = number
  default     = 7
}

variable "iam_policy_attachment_ids" {
  description = <<-EOT
    List of aws_iam_user_policy_attachment IDs from the root module.
    Used to enforce that Terraform execution policies are fully propagated
    before any resource that depends on those permissions is created.
    IAM is eventually consistent — without this, the log group creation
    can race ahead of policy propagation and fail with AccessDenied.
  EOT
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------
# Phase 4 variables
# -----------------------------------------------------------------------

variable "vector_bucket_name" {
  description = "Name of the S3 Vectors bucket. Used to scope Lambda runtime IAM policy."
  type        = string
}

variable "vector_index_name" {
  description = "Name of the vector index. Used to scope Lambda runtime IAM policy and passed as env var."
  type        = string
}

variable "embedding_model_id" {
  description = "Amazon Bedrock embedding model ID. Used to scope bedrock:InvokeModel permission."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "embedding_dimensions" {
  description = "Number of vector dimensions produced by the embedding model. Must match the vector index."
  type        = number
  default     = 1024
}

variable "layer_zip_path" {
  description = <<-EOT
    Absolute or module-relative path to the pre-built pypdf Lambda layer ZIP.
    Build with:
      mkdir -p /tmp/pypdf-layer/python
      pip install pypdf==4.3.1 -t /tmp/pypdf-layer/python --quiet
      cd /tmp/pypdf-layer && zip -r9 pypdf-layer.zip python/
      cp /tmp/pypdf-layer/pypdf-layer.zip <repo>/modules/knowledge_base_lambda/layer/pypdf-layer.zip
  EOT
  type        = string
  default     = null
}
