# ---------------------------------
# Namespace
# ---------------------------------

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
    labels = {
      name = "monitoring"
    }
  }
}

resource "kubernetes_namespace" "kubecost" {
  metadata {
    name = "kubecost"
    labels = {
      name = "kubecost"
    }
  }
}

# ---------------------------------
# metrics-server
# Required for kubectl top nodes/pods and HPA.
# ---------------------------------

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.metrics_server_version
  namespace  = "kube-system"

  values = [file("${path.root}/kubernetes/metrics-server/values.yaml")]

  timeout = 300
}

# ---------------------------------
# AWS Load Balancer Controller
# Watches for Ingress/Service resources and provisions ALBs/NLBs.
# The IAM role is created by the aws_load_balancer_controller_iam module.
# We create the ServiceAccount here (not via Helm) so the IRSA annotation
# referencing the role ARN can be set before the controller pod starts.
#
# wait = false: The LBC installs a validating webhook. If Terraform waits
# for all pods to be Ready before proceeding, the webhook can cause a
# deadlock on t3.small nodes where image pulls are slow. Setting wait=false
# lets Terraform record the release as deployed and move on; the controller
# will finish starting in the background within ~60s.
# ---------------------------------

resource "kubernetes_service_account" "aws_load_balancer_controller" {
  metadata {
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = var.lb_controller_role_arn
    }
    labels = {
      "app.kubernetes.io/name"      = "aws-load-balancer-controller"
      "app.kubernetes.io/component" = "controller"
    }
  }
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = var.lb_controller_version
  namespace  = "kube-system"

  values = [templatefile("${path.root}/kubernetes/aws-load-balancer-controller/values.yaml", {
    cluster_name = var.cluster_name
    vpc_id       = var.vpc_id
  })]

  # Increased from 300s — t3.small nodes need more time to pull the image.
  timeout = 600

  # Do not block Terraform waiting for webhook readiness — avoids deadlock.
  wait = false

  # Controller pod must start after the ServiceAccount exists
  depends_on = [kubernetes_service_account.aws_load_balancer_controller]
}

# ---------------------------------
# kube-prometheus-stack
# Deploys: Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics
# ---------------------------------

resource "helm_release" "kube_prometheus_stack" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = var.prometheus_stack_version
  namespace  = kubernetes_namespace.monitoring.metadata[0].name

  values = [file("${path.root}/kubernetes/prometheus/values.yaml")]

  # Give Prometheus enough time to pull images on t3.small nodes
  timeout = 600

  depends_on = [kubernetes_namespace.monitoring]
}

# ---------------------------------
# KubeCost
# ---------------------------------

resource "helm_release" "kubecost" {
  name       = "kubecost"
  repository = "https://kubecost.github.io/cost-analyzer/"
  chart      = "cost-analyzer"
  version    = var.kubecost_version
  namespace  = kubernetes_namespace.kubecost.metadata[0].name

  values = [file("${path.root}/kubernetes/kubecost/values.yaml")]

  timeout = 600

  depends_on = [kubernetes_namespace.kubecost]
}

# ---------------------------------
# IRSA: KubeCost Cost Explorer + CloudWatch
# ---------------------------------

data "aws_iam_policy_document" "kubecost_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_hostpath}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_hostpath}:sub"
      values   = ["system:serviceaccount:kubecost:kubecost-cost-analyzer"]
    }
  }
}

resource "aws_iam_role" "kubecost" {
  name               = "${var.cluster_name}-kubecost"
  assume_role_policy = data.aws_iam_policy_document.kubecost_assume_role.json

  tags = {
    Name = "${var.cluster_name}-kubecost"
  }
}

resource "aws_iam_policy" "kubecost" {
  name        = "${var.cluster_name}-kubecost"
  description = "Allows KubeCost to read AWS Cost Explorer and CloudWatch for cost allocation."
  policy      = file("${path.module}/kubecost-policy.json")
}

resource "aws_iam_role_policy_attachment" "kubecost" {
  role       = aws_iam_role.kubecost.name
  policy_arn = aws_iam_policy.kubecost.arn
}
