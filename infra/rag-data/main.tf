terraform {
  required_version = ">= 1.10.0"
  backend "s3" {
    bucket       = "douglas-sre-s3-terraform-state"
    key          = "rag-interview/data.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.0" }
  }
}
provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = ["490224159848"]
  default_tags { tags = { Project = "rag-interview", Environment = "lab", ManagedBy = "Terraform" } }
}
module "source" {
  source       = "../../modules/knowledge_base"
  project_name = "rag-interview"
  environment  = "lab"
}

output "source_bucket" { value = module.source.bucket_name }
