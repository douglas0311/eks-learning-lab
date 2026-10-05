# Lab 05 — Ingress activation and recovery

Prepared for October 6, 2026. Douglas runs all workflows. Preparation and offline tests do not establish live AWS success; the first activation must verify its prerequisites and the intended symptom.

## Before activation

Read the [concept refresh](../labs/lab-05/concept-refresh.md) to recall components, traffic flow, and terminology. It contains no scenario answer or diagnostic sequence.

## Start

Run workflows from `main`, waiting for each result:

1. **Terraform Provision** — if the environment was destroyed.
2. **Deploy simple-test** — for a fresh cluster. If already installed, do not repeat the initial-deployment workflow blindly.
3. **Configure SRE observability** — for the current cluster.
4. If reusing Lab 04, run **Run SRE lab 04 → restore** first, even if you manually repaired its Service. This also removes its recovery marker. Other active labs must likewise be recovered first.
5. Refresh your local access:

```bash
aws eks update-kubeconfig --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default
kubectl auth can-i create pods --subresource=exec -n simple-test
kubectl -n simple-test get pods
```

6. Run **Run SRE lab 05 → operation: activate**.
7. After green activation, read the [problem statement](../labs/lab-05/README.md) and start collecting evidence.

A green activation means the existing internal application check passed and the expected controller symptom was observed. A red activation may indicate a prerequisite or automation problem; preserve its URL and first failed step. Do not repeatedly activate over an interrupted run: use cleanup first.

## Operations

| Operation | Purpose |
| --- | --- |
| activate | Verify the application/controller, save ownership data, create the exercise, and verify the intended symptom |
| check | Verify HTTP through the internal ALB from a temporary in-cluster client; no repair is applied |
| restore | Apply the scenario repair, wait for an ALB address, and verify HTTP through it |
| cleanup | Delete only the exercise-owned Ingress, wait for controller-managed deletion, then remove the recovery record |

Restore and check may take several minutes. Restore leaves the Ingress and recovery record in place for inspection; it is not cleanup. A recovery timeout preserves the record so the operation can be retried or cleaned up.

## Scope and access

The ALB is **internal**, with HTTP on port 80. It is tested from inside the cluster, not directly from a laptop without VPC connectivity. No custom public DNS, TLS certificate, or internet-facing endpoint is needed. A hostname in Ingress status alone does not establish HTTP health.

The existing controller, its IAM role, subnet discovery tags, application Service, and monitoring are reused. This is ingress (incoming application traffic), not egress (outbound traffic).

The application dashboard remains useful for workload context, but it is not continuous ALB HTTP monitoring. Controller events and logs are available through the operator's existing read access. No extra operator admin permissions are required to investigate; recovery uses the workflow's administrator role.

## Learning agreement

Start with observations and a hypothesis. Ask for hints when needed: first a guiding question, then a command, then an explanation. There is no requirement to solve the lab without help. Avoid reading `scripts/sre/lab05.py`, its tests, or workflow implementation while investigating; these contain the scenario's answer.

## Session closure and costs

After collecting evidence, run **Run SRE lab 05 → cleanup**, then **Terraform Decommission**. A successfully provisioned ALB incurs charges until removed. The workflow has no automatic overnight teardown.

Decommission also runs the same cleanup before planning destruction so the controller remains available to remove its AWS resources. If cleanup fails or finalizers remain, Decommission stops before Terraform destroy. Do not remove finalizers to bypass it; inspect the controller and IAM errors, then retry cleanup. Never delete the cluster first while this Ingress still owns an ALB.

If the cluster was already manually removed, the Kubernetes cleanup step cannot verify external ALB cleanup. Inspect AWS resources separately; an absent cluster is not evidence that a controller-managed ALB was deleted.

## Implementation reference

The repository pins AWS Load Balancer Controller Helm chart 1.8.1 (controller v2.8.1). Configuration was checked against its [v2.8 Ingress annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/). Live reconciliation, IAM, ALB creation and HTTP must still be verified by the learner's workflow run.
