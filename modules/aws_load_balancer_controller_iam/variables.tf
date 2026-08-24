variable "cluster_name" {
  description = "EKS cluster name used in IAM resource names."
  type        = string
}

variable "oidc_issuer_url" {
  description = "OIDC issuer URL emitted by the EKS cluster."
  type        = string
}
