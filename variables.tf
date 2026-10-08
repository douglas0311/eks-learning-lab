variable "aws_region" {
  description = "AWS region for the lab."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used in resource names and tags."
  type        = string
  default     = "eks-learning-lab"
}

variable "environment" {
  description = "Environment name used in resource names and tags."
  type        = string
  default     = "lab"
}

variable "vpc_cidr" {
  description = "CIDR block for the EKS VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Exactly two Availability Zones in the selected AWS region."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Exactly two Availability Zones must be supplied."
  }
}

variable "kubernetes_version" {
  description = "EKS Kubernetes minor version. Keep this explicit so upgrades are deliberate."
  type        = string
  default     = "1.36"
}

variable "cluster_public_access_cidrs" {
  description = "CIDR ranges permitted to reach the public EKS API endpoint."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_instance_type" {
  description = "EC2 instance type for the managed node group."
  type        = string
  default     = "t3.small"
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

variable "enable_monitoring" {
  description = "Install the optional Prometheus/Grafana/Alertmanager and Kubecost stack. Metrics Server and networking controllers remain enabled."
  type        = bool
  default     = false
}
