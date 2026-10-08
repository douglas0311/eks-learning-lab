output "kubecost_role_arn" {
  description = "IAM role ARN for KubeCost IRSA."
  value       = var.enable_monitoring ? aws_iam_role.kubecost[0].arn : null
}
