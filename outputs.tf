output "cluster_name" {
  description = "Name of the EKS cluster."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS Kubernetes API endpoint."
  value       = module.eks.cluster_endpoint
}

output "cluster_oidc_issuer_url" {
  description = "OIDC issuer URL, useful for later IAM roles for service accounts."
  value       = module.eks.cluster_oidc_issuer_url
}

output "node_group_name" {
  description = "Name of the managed EKS node group."
  value       = module.eks.node_group_name
}

output "aws_load_balancer_controller_role_arn" {
  description = "IAM role ARN to annotate on the AWS Load Balancer Controller service account."
  value       = module.aws_load_balancer_controller_iam.role_arn
}

output "configure_kubectl" {
  description = "Command to add this cluster to kubeconfig."
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "vpc_id" {
  description = "ID of the EKS VPC."
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs used by the managed node group."
  value       = module.networking.private_subnet_ids
}

output "kubecost_role_arn" {
  description = "IAM role ARN for KubeCost IRSA (annotate kubecost service account with this)."
  value       = module.observability.kubecost_role_arn
}

output "grafana_access" {
  description = "Command to access Grafana locally via port-forward."
  value       = "kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80"
}

output "prometheus_access" {
  description = "Command to access Prometheus locally via port-forward."
  value       = "kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090"
}

output "kubecost_access" {
  description = "Command to access KubeCost locally via port-forward."
  value       = "kubectl port-forward -n kubecost svc/kubecost-cost-analyzer 9090:9090"
}
