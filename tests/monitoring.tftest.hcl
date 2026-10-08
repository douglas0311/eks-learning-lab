# Offline plans only: mocked providers never contact AWS, Helm, or Kubernetes.
mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}
mock_provider "helm" {}
mock_provider "kubernetes" {}

variables {
  cluster_name           = "test-cluster"
  oidc_provider_arn      = "arn:aws:iam::123456789012:oidc-provider/example.com"
  oidc_provider_hostpath = "example.com"
  lb_controller_role_arn = "arn:aws:iam::123456789012:role/test"
  vpc_id                 = "vpc-0123456789abcdef0"
}

run "without_optional_monitoring" {
  command = plan
  module { source = "./modules/observability" }
  variables { enable_monitoring = false }
  assert {
    condition = (
      length(helm_release.kube_prometheus_stack) == 0 &&
      length(helm_release.kubecost) == 0 &&
      length(kubernetes_namespace.monitoring) == 0 &&
      length(kubernetes_namespace.kubecost) == 0 &&
      length(aws_iam_role.kubecost) == 0 &&
      length(aws_iam_policy.kubecost) == 0 &&
      length(aws_iam_role_policy_attachment.kubecost) == 0
    )
    error_message = "The optional monitoring stack must be absent."
  }
  assert {
    condition     = helm_release.metrics_server.name == "metrics-server" && helm_release.aws_load_balancer_controller.name == "aws-load-balancer-controller"
    error_message = "Essential metrics and networking components must remain installed."
  }
  assert {
    condition     = output.kubecost_role_arn == null
    error_message = "Disabled stack must not expose a nonexistent IAM role."
  }
}

run "with_optional_monitoring" {
  command = plan
  module { source = "./modules/observability" }
  variables { enable_monitoring = true }
  assert {
    condition = (
      length(helm_release.kube_prometheus_stack) == 1 &&
      length(helm_release.kubecost) == 1 &&
      length(kubernetes_namespace.monitoring) == 1 &&
      length(kubernetes_namespace.kubecost) == 1 &&
      length(aws_iam_role.kubecost) == 1 &&
      length(aws_iam_role_policy_attachment.kubecost) == 1
    )
    error_message = "Enabling monitoring must include namespaces, releases, and supporting IAM."
  }
}
