variable "project_name" {
  description = "Project name."
  type        = string
}

variable "environment" {
  description = "Environment name."
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where the SSM resources will be created."
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of the private subnets where the SSM interface endpoints will be deployed."
  type        = list(string)
}

variable "application_security_group_id" {
  description = "ID of the application Security Group allowed to reach the SSM interface endpoints."
  type        = string
}