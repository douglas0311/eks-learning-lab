output "endpoint" {
  description = "RDS PostgreSQL endpoint."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "RDS PostgreSQL port."
  value       = aws_db_instance.this.port
}

output "db_name" {
  description = "RDS database name."
  value       = aws_db_instance.this.db_name
}

output "username" {
  description = "RDS database username."
  value       = aws_db_instance.this.username
}

output "secret_arn" {
  description = "ARN of the Secrets Manager secret containing database credentials."
  value       = aws_secretsmanager_secret.database.arn
}