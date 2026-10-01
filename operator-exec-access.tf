# Shared manifest also allows the manual access workflow to repair a running lab.
locals {
  operator_exec_rbac = [for document in split("\n---\n", file("${path.module}/kubernetes/simple-test/operator-exec.yaml")) : yamldecode(document)]
}

resource "kubernetes_role_v1" "lab_operator_exec" {
  metadata {
    name      = local.operator_exec_rbac[0].metadata.name
    namespace = kubernetes_namespace_v1.simple_test.metadata[0].name
  }
  dynamic "rule" {
    for_each = local.operator_exec_rbac[0].rules
    content {
      api_groups = rule.value.apiGroups
      resources  = rule.value.resources
      verbs      = rule.value.verbs
    }
  }
}

resource "kubernetes_role_binding_v1" "lab_operator_exec" {
  metadata {
    name      = local.operator_exec_rbac[1].metadata.name
    namespace = kubernetes_namespace_v1.simple_test.metadata[0].name
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.lab_operator_exec.metadata[0].name
  }
  dynamic "subject" {
    for_each = local.operator_exec_rbac[1].subjects
    content {
      kind      = subject.value.kind
      name      = subject.value.name
      api_group = subject.value.apiGroup
    }
  }
}
