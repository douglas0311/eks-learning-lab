variable "project_name" {
  description = "Project name used for resource naming."
  type        = string

  default = "terraform-sre-lab"
}

variable "environment" {
  description = "Environment name."
  type        = string

  default = "lab"
}

variable "vpc_id" {
  description = "ID of the VPC where the ALB will be deployed."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs used by the ALB."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_ids) == 2
    error_message = "Exactly two public subnets must be provided."
  }
}

variable "application_port" {
  description = "Port where the application will listen."
  type        = number

  default = 8080
}