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
  description = "VPC where RDS instances will run."
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
variable "db_name" {
  description = "Database name."
  type        = string

  default = "appdb"
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string

  default = "db.t3.micro"
}
variable "allocated_storage" {
  description = "Initial database storage size in GB "
  type        = number

  default = 20
}
variable "backup_retention_period" {
  description = "Number of days to retain automated backups."
  type        = number

  default = 7
}

variable "engine_version" {
  description = "PostgreSQL engine version."
  type        = string

  default = "16"
}
