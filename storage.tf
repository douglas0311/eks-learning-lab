# Storage prerequisites only. The lab workflow owns its disposable PVC/PV workload.
# Reuse the existing OIDC provider; do not create a second provider for the cluster.
data "aws_iam_policy_document" "ebs_csi_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [module.aws_load_balancer_controller_iam.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${trimprefix(module.eks.cluster_oidc_issuer_url, "https://")}:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "${trimprefix(module.eks.cluster_oidc_issuer_url, "https://")}:sub"
      values   = ["system:serviceaccount:kube-system:ebs-csi-controller-sa"]
    }
  }
}

resource "aws_iam_role" "ebs_csi" {
  name               = "${local.cluster_name}-ebs-csi"
  assume_role_policy = data.aws_iam_policy_document.ebs_csi_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEBSCSIDriverPolicyV2"
}

variable "ebs_csi_addon_version" {
  description = "Optional compatible EBS CSI add-on version pin. Null selects the EKS default on creation; the installed version is retained in state."
  type        = string
  default     = null
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name             = module.eks.cluster_name
  addon_name               = "aws-ebs-csi-driver"
  addon_version            = var.ebs_csi_addon_version
  service_account_role_arn = aws_iam_role.ebs_csi.arn
  preserve                 = false

  # Nodes and role permissions must exist before the add-on can become healthy.
  depends_on = [module.eks, aws_iam_role_policy_attachment.ebs_csi]
}

output "ebs_csi_addon_version" {
  description = "Installed EBS CSI version for the lab evidence record."
  value       = aws_eks_addon.ebs_csi.addon_version
}
