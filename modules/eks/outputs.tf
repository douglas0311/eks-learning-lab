output "cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  description = "EKS Kubernetes API endpoint."
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_oidc_issuer_url" {
  description = "OIDC issuer URL for future IAM roles for service accounts."
  value       = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

output "node_group_name" {
  description = "Name of the managed EKS node group."
  value       = aws_eks_node_group.this.node_group_name
}

output "cluster_ca_certificate" {
  description = "Base64-encoded CA certificate for the EKS cluster."
  value       = aws_eks_cluster.this.certificate_authority[0].data
}

output "cluster_auth_token" {
  description = "Token for authenticating to the EKS cluster."
  value       = data.aws_eks_cluster_auth.this.token
  sensitive   = true
}
