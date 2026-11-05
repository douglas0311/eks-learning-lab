terraform {
  required_version = ">= 1.10.0"
  backend "s3" {
    bucket       = "douglas-sre-s3-terraform-state"
    key          = "rag-interview/terraform.tfstate"
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

module "vectors" {
  source             = "../../modules/knowledge_base_vectors"
  environment        = "lab"
  vector_bucket_name = "rag-interview-lab-vectors"
  vector_index_name  = "kb-index"
  vector_dimension   = 1024
  force_destroy      = true
}
module "ingest" {
  source             = "../../modules/knowledge_base_lambda"
  project_name       = "rag-interview"
  environment        = "lab"
  aws_region         = "us-east-1"
  aws_account_id     = "490224159848"
  function_name      = "rag-interview-lab-ingestor"
  source_bucket_name = "rag-interview-lab-knowledge-source"
  source_bucket_arn  = "arn:aws:s3:::rag-interview-lab-knowledge-source"
  vector_bucket_name = module.vectors.vector_bucket_name
  vector_index_name  = module.vectors.vector_index_name
  layer_zip_path     = "../../modules/knowledge_base_lambda/layer/pypdf-layer.zip"
}
module "query" {
  source             = "../../modules/knowledge_base_query"
  environment        = "lab"
  aws_region         = "us-east-1"
  aws_account_id     = "490224159848"
  function_name      = "rag-interview-lab-query"
  vector_bucket_name = module.vectors.vector_bucket_name
  vector_index_name  = module.vectors.vector_index_name
}
output "source_bucket" { value = "rag-interview-lab-knowledge-source" }
output "query_function" { value = module.query.function_name }
