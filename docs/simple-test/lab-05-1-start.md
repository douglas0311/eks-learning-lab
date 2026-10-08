# Lab 05.1 — Start and cleanup

> Workflow navigation update: use **SRE labs (current: 06)** and select the scenario named in this guide. The old per-lab workflow names below are historical; see the [archive and operation mapping](../../archive/workflows/README.md).


## Finish the current environment first

Run from the latest `main`:

1. **Repair load balancer controller IAM** — updates the existing controller policy only, retaining its previous version. Wait for success. If it fails, preserve the error; do not proceed on an assumption of repaired permissions.
2. **Run SRE lab 05 → cleanup** — wait for the exercise Ingress to disappear with controller cleanup completed.
3. **Terraform Decommission** — destroy the environment after cleanup succeeds. It includes the same cleanup guard before Terraform destroy.

Do not manually remove finalizers or delete the cluster before controller cleanup. An ALB may have been partially created despite a failed restore. The assistant does not execute these workflows.

## Fresh environment for 5.1

1. Read the [concept refresh](../labs/lab-05/concept-refresh.md).
2. Run **Terraform Provision**. It now uses the corrected version-pinned controller IAM policy; no separate IAM repair is needed for a fresh environment.
3. Run **Deploy simple-test**.
4. Run **Configure SRE observability**.
5. Update kubeconfig with your existing command and verify operator exec access if needed.
6. Run **Run SRE lab 05.1 → activate** from `main`. Wait for green before starting the investigation.
7. Read the [problem statement](../labs/lab-05-1/README.md).

Activation first creates an internal ALB and verifies a real HTTP response through it. Only after this healthy starting point does it introduce and verify the new scenario. If the initial check fails, the exercise fault has not been injected; preserve the run URL and diagnose the environment. ALB provisioning can take several minutes, and it incurs charges until cleanup.

The variant shares the Ingress name and recovery record with Lab 05, so the two cannot run simultaneously. Always clean up the previous scenario before activation. Interrupted runs retain ownership/recovery data; use cleanup rather than another activation.

## Operations

- **check:** validate the expected application response through the ALB without changing routing.
- **restore:** use the saved scenario to repair the appropriate configuration, then validate HTTP. Leaves resources available for inspection.
- **cleanup:** remove the exercise-owned Ingress and wait for controller cleanup; removes the recovery record afterward.

The shared recovery implementation supports the old Lab 05 record. Cleanup remains available through either workflow and Terraform Decommission. A green repair or restore is not a substitute for keeping the exact client response in your notes.

After collecting evidence: **cleanup → Terraform Decommission**. If cleanup fails, keep the controller available and inspect the error. No automatic overnight cleanup is scheduled.

## Independent investigation

Use the vocabulary reference, but avoid implementation files and tests: they contain the injected configuration. This variant is an opportunity to apply the concepts from the guided session. Request hints progressively if needed; no score depends on avoiding all help.
