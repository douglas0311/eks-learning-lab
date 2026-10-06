# Controller IAM policy provenance

`policy.json` is the unmodified AWS Load Balancer Controller **v2.8.1** installation policy, matching the controller version supplied by the pinned Helm chart 1.8.1.

Source: https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.8.1/docs/install/iam_policy.json

SHA-256: `d25c6192f7187427d21ecb41109afe29002bf84bdf97f3f3e00684a96d1fe1f1`

The previous abbreviated policy omitted WAF integration actions. On October 6, recovery of Lab 05 reached AWS reconciliation but failed on `wafv2:GetWebACLForResource`. The official policy includes supported integrations (WAF, Shield, certificates and authentication) and resource/tag conditions for applicable mutations, rather than the previous broad EC2/ELB mutation statements. Its inclusion does not enable paid WAF or Shield resources by itself.

Terraform continues to manage the same policy ARN and role attachment. No trust-policy, controller-version, operator-permission, or application change is involved. Future controller upgrades must review the corresponding versioned upstream policy, rather than fetching an unpinned policy at runtime.

For an already running cluster, **Repair load balancer controller IAM** applies this same checked-in document to the existing policy after account and attachment checks. It retains previous policy versions and refuses to exceed the five-version limit. This is an intentional out-of-band repair of a Terraform-managed policy; the desired document in Terraform is identical, so a future refresh/provision converges to the same content. The next fresh Provision creates the corrected policy automatically.

The repair runner needs IAM read access plus `iam:CreatePolicyVersion` for the fixed policy ARN. A denied repair must be investigated; it does not justify granting the operator broad administration permissions. The workflow neither runs Terraform nor restarts or deploys a workload.
