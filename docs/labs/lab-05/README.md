# Lab 05 — Ingress delivery incident

The team added an Ingress named `simple-test-lab05` in namespace `simple-test` to provide an internal load-balancer entry point for the application. The new entry point is not becoming available as expected.

Investigate the failed delivery, identify the responsible configuration or component, and propose the smallest justified correction. Support the conclusion with evidence and explain how you would validate recovery.

HTTP is expected on port 80. The intended client is inside the VPC/cluster; no public DNS name or TLS certificate is part of this exercise.

Deliver: observations, commands and results, hypothesis, root cause, proposed remediation, and recovery evidence. Distinguish what each test proves from what it leaves unresolved.

- [Start, recovery and cleanup](../../simple-test/lab-05-start.md)
- [Engineering notes](engineering-notes.md)

The learner-facing notes intentionally contain no root cause or diagnostic command sequence.
