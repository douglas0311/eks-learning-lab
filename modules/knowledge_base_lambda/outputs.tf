output "function_name" {
  description = "Name of the deployed Lambda function."
  value       = aws_lambda_function.ingestor.function_name
}

output "function_arn" {
  description = "ARN of the deployed Lambda function."
  value       = aws_lambda_function.ingestor.arn
}

output "execution_role_arn" {
  description = "ARN of the Lambda execution IAM role."
  value       = aws_iam_role.lambda_execution.arn
}

output "log_group_name" {
  description = "CloudWatch Log Group name for the Lambda function."
  value       = aws_cloudwatch_log_group.lambda.name
}

output "pypdf_layer_arn" {
  description = "ARN of the pypdf Lambda layer version (Phase 4)."
  value       = aws_lambda_layer_version.pypdf.arn
}

output "execution_role_name" {
  description = "Name of the Lambda execution IAM role."
  value       = aws_iam_role.lambda_execution.name
}
