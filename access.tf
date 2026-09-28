# Read-only SRE diagnostics for the local lab user.
# Includes Secrets because Helm stores release metadata there by default.
resource "aws_eks_access_entry" "lab_operator" {
  cluster_name  = module.eks.cluster_name
  principal_arn = "arn:aws:iam::490224159848:user/day7-cli-user"
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "lab_operator_read" {
  cluster_name  = aws_eks_access_entry.lab_operator.cluster_name
  principal_arn = aws_eks_access_entry.lab_operator.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminViewPolicy"

  access_scope {
    type = "cluster"
  }
}
