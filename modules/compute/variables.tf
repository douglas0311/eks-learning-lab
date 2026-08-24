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
  description = "VPC where the EC2 instances will run."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs used by the Auto Scaling Group."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) == 2
    error_message = "Exactly two private subnets must be provided."
  }
}

variable "application_security_group_id" {
  description = "Security Group assigned to application instances."
  type        = string
}

variable "target_group_arn" {
  description = "Target Group where ASG instances will be registered."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string

  default = "t3.micro"
}

variable "desired_capacity" {
  description = "Desired number of EC2 instances."
  type        = number

  default = 2
}

variable "min_size" {
  description = "Minimum number of EC2 instances."
  type        = number

  default = 2
}

variable "max_size" {
  description = "Maximum number of EC2 instances."
  type        = number

  default = 2
}