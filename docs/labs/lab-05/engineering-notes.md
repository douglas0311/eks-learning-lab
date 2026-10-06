# Lab 05 Engineering notes

**Status:** prepared on October 5, 2026; live activation and investigation pending.

**Investigator:** Douglas García Jiménez.

## Incident scope

An internal application entry point is not becoming available after an Ingress was introduced. Record the environment and workflow URL when the exercise is activated.

## Observations and evidence

Pending investigation. For each test, record time, source, target, command, output, and interpretation.

## Hypothesis and competing explanations

Pending investigation. Explain which evidence supports the hypothesis and which observation could disprove it.

## Root cause and remediation

Pending investigation. Do not infer the cause from a workflow color alone.

## Recovery and closure

Pending investigation. Retest the affected request path and preserve output before cleanup and Decommission.

## Learning and assistance

Record any help requested and what it clarified. The aim is stronger independent reasoning, not a zero-help score.

## October 6 update

The guided investigation identified a mismatch between the Ingress backend reference (8080), Service port (80), and the correctly named container destination (`http`, port 80). The discussion distinguished a Service's client-facing port from its targetPort and evaluated the impact of changing an existing client interface.

The restore workflow then reached a second blocker: `FailedDeployModel` with an IAM denial for `wafv2:GetWebACLForResource` on the controller's role. Douglas identified the permission error from Events. Recovery through the ALB has not yet been established. The original "pending" sections above remain placeholders for the full investigator evidence; they are not evidence of a completed recovery.

[Root cause and environment repair](rca.md). The user will run cleanup and teardown after applying the controller IAM repair.
