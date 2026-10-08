# Preserve existing resource identities when enabling the optional stack.

moved {
  from = kubernetes_namespace.monitoring
  to   = kubernetes_namespace.monitoring[0]
}

moved {
  from = kubernetes_namespace.kubecost
  to   = kubernetes_namespace.kubecost[0]
}

moved {
  from = helm_release.kube_prometheus_stack
  to   = helm_release.kube_prometheus_stack[0]
}

moved {
  from = helm_release.kubecost
  to   = helm_release.kubecost[0]
}

moved {
  from = aws_iam_role.kubecost
  to   = aws_iam_role.kubecost[0]
}

moved {
  from = aws_iam_policy.kubecost
  to   = aws_iam_policy.kubecost[0]
}

moved {
  from = aws_iam_role_policy_attachment.kubecost
  to   = aws_iam_role_policy_attachment.kubecost[0]
}
