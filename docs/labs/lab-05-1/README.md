# Lab 05.1 — Internal entry-point regression

The application previously responded through its internal load-balancer entry point. Following a configuration change, a client using that same entry point no longer receives the expected application response.

Determine which part of the request path explains the regression. Present evidence, a hypothesis, the smallest justified correction, and a recovery test. Do not assume the cause is the same as Lab 05.

Client scope: inside the cluster/VPC, HTTP, using the hostname published by Ingress `simple-test-lab05` in namespace `simple-test`. Public DNS and TLS are not part of this exercise.

- [Concept refresh](../lab-05/concept-refresh.md)
- [Start and cleanup](../../simple-test/lab-05-1-start.md)
- [Engineering notes](engineering-notes.md)

No diagnostic sequence is provided. Ask for a guiding question first if you become stuck.

**Completed October 6, 2026:** the investigator recorded recovery of the original request. [RCA — contains the solution](rca.md). Next: [Lab 05.2](../lab-05-2/README.md).
