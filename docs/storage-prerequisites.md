# EKS storage prerequisites

Terraform owns the EBS CSI managed add-on, its IAM role, and the managed-policy attachment. The scenario workflow owns its disposable workload, StorageClass, claim, and dynamically provisioned volume. The volume is therefore cleaned up through Kubernetes/CSI before Terraform removes the controller.

The existing cluster OIDC provider is reused. IRSA trust restricts the role to `system:serviceaccount:kube-system:ebs-csi-controller-sa` and audience `sts.amazonaws.com`. No EBS permissions are added to the node role or the local operator. The CSI role uses the AWS managed `AmazonEBSCSIDriverPolicyV2`; its canonical ARN was verified with IAM, independently from examples that show a different policy path.

`ebs_csi_addon_version` can pin a compatible add-on version. When null, EKS selects its compatible default on creation and Terraform records the installed version. This does not assert that a particular latest version is installed. Record the actual version after Provision:

```bash
aws eks describe-addon \
  --cluster-name eks-learning-lab-lab-eks \
  --addon-name aws-ebs-csi-driver \
  --region us-east-1 --profile default \
  --query 'addon.{Status:status,Version:addonVersion,Role:serviceAccountRoleArn}'
```

The dedicated lab StorageClass uses `ebs.csi.aws.com`, gp3, encryption, WaitForFirstConsumer and Delete reclamation. The owner token is also an EBS tag so cleanup can verify that no owned volume remains. The class is not made default and existing observability workloads continue to use their current ephemeral storage settings.

The local operator's existing cluster read policy provides storage inspection, and existing namespace exec access covers the worker. The recovery workflow uses the Terraform role. No new operator mutation permission is required.

References: [EBS CSI prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [canonical managed policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonEBSCSIDriverPolicyV2.html), [CSI StorageClass parameters](https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/master/docs/parameters.md), [CSI volume tagging](https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/master/docs/tagging.md).
