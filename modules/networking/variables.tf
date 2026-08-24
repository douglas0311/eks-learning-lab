variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string

  default = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability Zones where the workload will be deployed."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Exactly two Availability Zones must be provided."
  }
}

variable "environment" {
  description = "Environment name used for resource tagging."
  type        = string

  default = "lab"
}

variable "project_name" {
  description = "Project name used for resource naming and tagging."
  type        = string

  default = "eks-learning-lab"
}

variable "cluster_name" {
  description = "EKS cluster name used for Kubernetes subnet discovery tags."
  type        = string
}
