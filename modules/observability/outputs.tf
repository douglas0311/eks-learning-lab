output "kubecost_role_arn" {
  description = "IAM role ARN for KubeCost IRSA."
  value       = aws_iam_role.kubecost.arn
}
