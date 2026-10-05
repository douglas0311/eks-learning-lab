# Lab 04 Internal service connectivity

A client inside the cluster cannot access `http://simple-test.simple-test.svc.cluster.local:80/` after a recent change. Application Pods appear Running and Ready. Identify where the request stops and explain why.

- [Activation and recovery guide](../../simple-test/lab-04-start.md)
- [Engineering notes](engineering-notes.md) — selector mismatch identified; HTTP recovery documented.
- [Unexpected diagnostic access incident](../../incidents/INC-001-pods-exec/rca.md) — separate from the intended network exercise.

[Root cause analysis](rca.md) records the evidence, remediation, and validation limits. A green activation workflow means the exercise symptom was established, not that normal service access is healthy.
