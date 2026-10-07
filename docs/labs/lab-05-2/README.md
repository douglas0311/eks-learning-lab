# Lab 05.2 — An internal application request regresses

**Status:** completed October 7, 2026; the original ALB request returned HTTP 200 after restore.

An internal client previously received the `simple-test` page through the ALB. Following a configuration change, the same request no longer receives the expected application response. Determine where the failure occurs and support the conclusion with evidence.

## Request contract

- Client: a Pod inside this cluster, with access to the internal ALB.
- Method: GET.
- URL: `http://<current-ingress-hostname>/`, using the hostname published by Ingress `simple-test-lab05` in namespace `simple-test`.
- Expected response: HTTP 200 and a page containing `simple-test is running`.
- Actual response: reproduce and record it after activation succeeds; do not infer it from Pod readiness or workflow color.

Keep the public interface unchanged when proposing a correction. Explain why your evidence locates the fault and which alternative explanation you ruled out. No production traffic or public endpoint is involved.

Read the [refreshment](concept-refresh.md), then follow the [start guide](../../simple-test/lab-05-2-start.md). Use [engineering notes](engineering-notes.md) to record your work. Implementation and tests contain spoilers; save them for the review.

If you need help, request one guiding question at a time. This iteration practices applying the request contract and interpreting evidence rather than memorizing the previous fix.

[Completed RCA — contains the solution](rca.md) · [Next: Lab 06](../lab-06/README.md)
