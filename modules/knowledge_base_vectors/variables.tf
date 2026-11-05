variable "environment" {
  description = "Environment name used in resource names and tags."
  type        = string
}

variable "vector_bucket_name" {
  description = "Name of the S3 Vectors bucket."
  type        = string
}

variable "vector_index_name" {
  description = "Name of the vector index within the bucket."
  type        = string
}

variable "vector_dimension" {
  description = <<-EOT
    Number of dimensions for each stored vector.
    Must exactly match the output dimensions of the chosen embedding model.
    amazon.titan-embed-text-v2:0 supports 256, 512, or 1024. Default: 1024.
  EOT
  type        = number
  default     = 1024

  validation {
    condition     = contains([256, 512, 1024], var.vector_dimension)
    error_message = "vector_dimension must be 256, 512, or 1024 (Titan Embed V2 supported values)."
  }
}

variable "force_destroy" {
  description = "Allow terraform destroy to remove the bucket even when it contains vectors. Set false in production."
  type        = bool
  default     = true
}
