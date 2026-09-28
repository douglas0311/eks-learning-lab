# ECR and the GitHub IAM role persist between labs; Provision prepares cluster access.
locals {
  simple_test_namespace = yamldecode(file("${path.module}/kubernetes/simple-test/namespace.yaml"))
  simple_test_rbac      = [for document in split("\n---\n", file("${path.module}/kubernetes/simple-test/rbac.yaml")) : yamldecode(document)]
}

resource "aws_eks_access_entry" "simple_test_deployer" {
  cluster_name      = module.eks.cluster_name
  principal_arn     = "arn:aws:iam::490224159848:role/GitHubActionsSimpleTestRole"
  type              = "STANDARD"
  kubernetes_groups = ["simple-test-deployers"]
}

resource "kubernetes_namespace_v1" "simple_test" {
  metadata {
    name   = local.simple_test_namespace.metadata.name
    labels = local.simple_test_namespace.metadata.labels
  }

  depends_on = [module.eks]
}

resource "kubernetes_role_v1" "simple_test_deployer" {
  metadata {
    name      = local.simple_test_rbac[0].metadata.name
    namespace = kubernetes_namespace_v1.simple_test.metadata[0].name
  }

  dynamic "rule" {
    for_each = local.simple_test_rbac[0].rules
    content {
      api_groups = rule.value.apiGroups
      resources  = rule.value.resources
      verbs      = rule.value.verbs
    }
  }
}

resource "kubernetes_role_binding_v1" "simple_test_deployer" {
  metadata {
    name      = local.simple_test_rbac[1].metadata.name
    namespace = kubernetes_namespace_v1.simple_test.metadata[0].name
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.simple_test_deployer.metadata[0].name
  }

  dynamic "subject" {
    for_each = local.simple_test_rbac[1].subjects
    content {
      kind      = subject.value.kind
      name      = subject.value.name
      api_group = subject.value.apiGroup
    }
  }
}
