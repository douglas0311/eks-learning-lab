output "function_name" {
  description = "Query component function name."
  value       = aws_lambda_function.query.function_name
}

output "function_arn" {
  description = "Query component function arn."
  value       = aws_lambda_function.query.arn
}

output "execution_role_arn" {
  description = "Query component execution role arn."
  value       = aws_iam_role.lambda_execution.arn
}

output "log_group_name" {
  description = "Query component log group name."
  value       = aws_cloudwatch_log_group.lambda.name
}

output "vector_index_arn" {
  description = "Query component vector index arn."
  value       = local.vector_index_arn
}
