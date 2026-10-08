# Permit the diagnostic user to open authenticated tunnels to monitoring UIs.
resource "kubernetes_role_v1" "lab_monitoring_tunnels" {
  count = var.enable_monitoring ? 1 : 0

  metadata {
    name      = "lab-monitoring-tunnels"
    namespace = "monitoring"
  }
  rule {
    api_groups = [""]
    resources  = ["pods/portforward"]
    verbs      = ["create"]
  }
  depends_on = [module.observability]
}

resource "kubernetes_role_binding_v1" "lab_monitoring_tunnels" {
  count = var.enable_monitoring ? 1 : 0

  metadata {
    name      = "lab-monitoring-tunnels"
    namespace = "monitoring"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.lab_monitoring_tunnels[0].metadata[0].name
  }
  subject {
    kind      = "User"
    name      = "arn:aws:iam::490224159848:user/day7-cli-user"
    api_group = "rbac.authorization.k8s.io"
  }
}

moved {
  from = kubernetes_role_v1.lab_monitoring_tunnels
  to   = kubernetes_role_v1.lab_monitoring_tunnels[0]
}

moved {
  from = kubernetes_role_binding_v1.lab_monitoring_tunnels
  to   = kubernetes_role_binding_v1.lab_monitoring_tunnels[0]
}
