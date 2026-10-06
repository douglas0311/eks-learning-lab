# Lab 05.2 — Refreshment before investigation

This reviews what Labs 05 and 05.1 taught us. It does not identify the next injected fault.

## Start with the user's experience

Before investigating, write the exact method, scheme, hostname, port, path, client location, expected response, actual response, and time. Reproduce that request early. Keep the original command so you can repeat the same test after a correction.

A **baseline** is recorded evidence of normal behavior before a change. It is not a command. Here, the activation workflow checks that the application page is reachable through the internal ALB before introducing the exercise.

## Components and contracts

| Term | What to remember |
| --- | --- |
| Ingress | Desired host/path routing and a reference to a Service port |
| Controller | Reconciles Kubernetes configuration into AWS resources using its own AWS permissions |
| ALB listener | Client-facing protocol and port |
| Target group | Backend destinations and forwarding settings used by the ALB |
| Service `port` | Interface offered to clients and referenced by the Ingress backend |
| Service `targetPort` | Numeric destination or a name resolved against the container's named ports |
| EndpointSlice | Addresses and readiness information for the Service's selected backends |
| Pod | A workload instance; Running does not establish every access path is healthy |
| `spec` / `status` | Desired configuration / observed state reported by controllers |

For IP targets, the controller uses Service/EndpointSlice information to configure Pod targets. Do not assume the ALB request must traverse the Service ClusterIP. Client-facing settings and backend settings describe different connections.

## What our earlier evidence established

| Observation | What it established | What it did not establish |
| --- | --- | --- |
| Ingress backend 8080; Service port 80 | A backend reference mismatch in Lab 05 | That changing the working Service was the best correction |
| `SuccessfullyReconciled` | The controller applied the declared configuration | That the requested URL returned the expected page |
| Empty ClusterIP Service loadBalancer status | No Service-owned load balancer was published | A missing Ingress hostname or a fault |
| EndpointSlice has two addresses | Backends were selected | Successful HTTP through every route |
| Local `curl -I` returns 200 | That Pod answered a local HEAD request | GET body correctness or ALB reachability |
| ALB returns an HTTP error | A server returned an HTTP response | That the application generated it or the request reached a particular Pod |
| ALB GET `/` returns 200 after repair | That request recovered at that time | Sustained availability or every replica's behavior |

An HTTP status and `Server` header are clues, not a complete root cause. Correlate them with configuration and logs. A healthy `/healthz` check and a request to `/` test different contracts.

## DNS, paths, and command details

- `nslookup` takes only a hostname: no `http://` and no trailing `/`. A malformed DNS query does not establish a DNS outage.
- `curl -i` issues GET and includes response headers. `curl -I` issues HEAD. Reproduce the user's method before comparing results.
- `kubectl exec POD -- curl URL` makes POD the client. It does not force the ALB to choose that Pod as its backend.
- Prefix matching does not automatically rewrite a path. In Lab 05.1, `/application` did not match the requested `/`.
- An internal ALB must be tested from a reachable network. A failed laptop request may have a different cause from a failed in-cluster request.
- A historical Event may remain after repair. Compare timestamps, recurrence, current configuration, and current responses.

## Apply these habits

1. Reproduce the exact user request and preserve its output.
2. State what each observation proves and what remains uncertain.
3. Form a hypothesis and choose a test that could disprove it.
4. Revise the hypothesis when new evidence contradicts it.
5. Propose the smallest justified change that preserves the client contract.
6. Repeat the original request after repair; retain response headers and relevant body evidence.

## Self-check questions

- Can an Ingress reconcile successfully while the application URL fails? Why?
- Why can a ClusterIP Service have an empty loadBalancer status?
- What changes when you run the same ALB curl command from a different Pod?
- Which part of the path does a local application test skip?
- What evidence would justify calling a correction successful?

Use the [previous concept reference](../lab-05/concept-refresh.md) for additional definitions. The [AWS controller annotation reference](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/) describes configuration fields; consult it when a field needs clarification, without assuming that an unfamiliar field is wrong.
