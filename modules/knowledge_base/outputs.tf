output "bucket_name" {
  description = "Name of the knowledge source S3 bucket."
  value       = aws_s3_bucket.knowledge_source.bucket
}

output "bucket_arn" {
  description = "ARN of the knowledge source S3 bucket."
  value       = aws_s3_bucket.knowledge_source.arn
}
