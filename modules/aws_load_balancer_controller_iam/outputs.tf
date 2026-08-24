output "role_arn" {
  description = "IAM role ARN assumed by the controller through IRSA."
  value       = aws_iam_role.controller.arn
}

output "oidc_provider_arn" {
  description = "IAM OIDC provider for this EKS cluster."
  value       = aws_iam_openid_connect_provider.eks.arn
}
