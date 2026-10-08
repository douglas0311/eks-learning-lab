module "networking" {
  source = "./modules/networking"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  cluster_name       = local.cluster_name
}

module "eks" {
  source = "./modules/eks"

  # Managed nodes require the private-subnet NAT route before they bootstrap.
  depends_on = [module.networking]

  project_name                = var.project_name
  environment                 = var.environment
  cluster_name                = local.cluster_name
  kubernetes_version          = var.kubernetes_version
  vpc_id                      = module.networking.vpc_id
  vpc_cidr                    = var.vpc_cidr
  private_subnet_ids          = module.networking.private_subnet_ids
  cluster_public_access_cidrs = var.cluster_public_access_cidrs
  node_instance_type          = var.node_instance_type
}

module "aws_load_balancer_controller_iam" {
  source = "./modules/aws_load_balancer_controller_iam"

  cluster_name    = module.eks.cluster_name
  oidc_issuer_url = module.eks.cluster_oidc_issuer_url
}

module "observability" {
  source = "./modules/observability"

  # Observability stack must be installed after EKS nodes are ready
  # and the OIDC provider exists.
  depends_on = [
    module.eks,
    module.aws_load_balancer_controller_iam,

  ]

  cluster_name             = module.eks.cluster_name
  oidc_provider_arn        = module.aws_load_balancer_controller_iam.oidc_provider_arn
  oidc_provider_hostpath   = trimprefix(module.eks.cluster_oidc_issuer_url, "https://")
  lb_controller_role_arn   = module.aws_load_balancer_controller_iam.role_arn
  vpc_id                   = module.networking.vpc_id
  enable_monitoring        = var.enable_monitoring
  prometheus_stack_version = var.prometheus_stack_version
  kubecost_version         = var.kubecost_version
}

locals {
  cluster_name = "${var.project_name}-${var.environment}-eks"
}
