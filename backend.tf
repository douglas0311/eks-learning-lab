# Shared by Terraform CLI operations; initialize with AWS credentials before use.
terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    bucket              = "douglas-sre-s3-terraform-state"
    key                 = "eks-lab/terraform.tfstate"
    region              = "us-east-1"
    encrypt             = true
    use_lockfile        = true
    allowed_account_ids = ["490224159848"]
  }
}
