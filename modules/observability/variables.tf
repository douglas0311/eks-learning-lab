variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
}

variable "oidc_provider_arn" {
  description = "ARN of the EKS OIDC provider (from aws_load_balancer_controller_iam module)."
  type        = string
}

variable "oidc_provider_hostpath" {
  description = "Host path of the OIDC issuer (without https://)."
  type        = string
}

variable "lb_controller_role_arn" {
  description = "IAM role ARN for the AWS Load Balancer Controller IRSA (from aws_load_balancer_controller_iam module)."
  type        = string
}

variable "lb_controller_version" {
  description = "Helm chart version for the AWS Load Balancer Controller."
  type        = string
  default     = "1.8.1"
}

variable "metrics_server_version" {
  description = "Helm chart version for metrics-server."
  type        = string
  default     = "3.12.1"
}

variable "prometheus_stack_version" {
  description = "Helm chart version for kube-prometheus-stack."
  type        = string
  default     = "61.3.2"
}

variable "kubecost_version" {
  description = "Helm chart version for KubeCost cost-analyzer."
  type        = string
  default     = "2.3.4"
}

variable "vpc_id" {
  type = string
}
variable "enable_monitoring" {
  description = "Install the optional Prometheus/Grafana/Alertmanager and Kubecost stack. Metrics Server and networking controllers remain enabled."
  type        = bool
  default     = false
}
