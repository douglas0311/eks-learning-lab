# Historical Terraform state reconciliation

This record describes the September 27, 2026 reconciliation after resources had been manually removed. It is a historical operation record, not a command sequence to repeat against today's state.

## Recorded outcome

The original cluster, node group, and network were verified absent in AWS. Four IAM roles, two policies, six policy attachments, and the earlier cluster OIDC provider remained.

Using locked `terraform state rm`, the session removed 26 deleted-resource records and seven data-source records from state. It did not destroy infrastructure. The 13 remaining IAM records were compared with the backup and preserved. Remote lineage was retained; serial changed from 1 to 2. The backend object was `eks-lab/terraform.tfstate` in the existing versioned S3 state bucket. Exact backup version identifiers remain in the original private session record.

Historical outputs could retain old identifiers until the next plan/apply refreshed them. Those values were not proof that a cluster still existed.

## Validation at that time

The session recorded successful init, validate, and plan with Terraform 1.16.4. The plan proposed 26 creations, five replacements, four updates, and four unchanged resources. Replacements concerned the prior OIDC provider and four EKS role policy attachments; updates concerned IAM roles. The plan was not applied during reconciliation.

Workflow and manifest checks were recorded, and the container had passed an earlier local HTTP test. These are historical results, not a new validation of the currently running environment.

## Subsequent state

Provision and Decommission now use the remote backend. ECR, the app deployment role, and cluster access preparation were subsequently implemented, and the application was deployed during the later labs. The original document's setup checklist is therefore superseded by the [current application playbook](../simple-test/playbook.md).

Do not restore an obsolete artifact state over the current remote state. Do not commit Terraform state, plans, or credentials. Consult the [state rm reference](https://developer.hashicorp.com/terraform/cli/commands/state/rm) before a separately authorized reconciliation.
