# Lab 05 — Root cause and recovery blocker

**Status:** intended fault diagnosed; end-to-end ALB recovery still unverified as of October 6, 2026.

## Intended fault

The Ingress backend referenced Service port 8080, but the Service exposed port 80. The Service's named targetPort `http` resolved to containerPort 80. The controller reported `FailedBuildModel` because the Service did not offer the referenced port.

Douglas compared the Ingress, Service and container port definitions. Both changing the Service-facing port and correcting the Ingress reference could address the mismatch, but changing the Service would alter the interface used by existing internal HTTP clients. Correcting the newly introduced Ingress reference preserves that interface and does not change the ALB listener or NGINX's listening port.

## Additional environment defect

[Restore run 37482696306](https://github.com/douglas0311/eks-learning-lab/actions/runs/37482696306) passed the backend correction and internal HTTP probe, then timed out waiting for an ALB hostname. The investigator supplied subsequent `FailedDeployModel` events denying `wafv2:GetWebACLForResource` to the controller's assumed IAM role. This is separate from the operator's Kubernetes access and the workflow's AWS identity.

The repository policy was abbreviated and lacked that integration action. The persistent fix replaces it with the official controller v2.8.1 policy, matching the installed chart. This fixes the documented omission; successful AWS reconciliation still requires live validation. No claim of ALB HTTP recovery is made.

## Closure sequence

For the current environment: run **Repair load balancer controller IAM**, then **Run SRE lab 05 → cleanup**, then **Terraform Decommission**. Cleanup must finish while the controller is available. A retained finalizer or denied operation is a reason to investigate, not to force-delete the object. The user requested teardown, so successful repair need not be followed by a new restore/ALB test before cleanup.

The original scenario was a guided investigation. The learner identified the IAM denial from Events; that unintended preparation defect belongs to the environment, not to the intended exercise.
