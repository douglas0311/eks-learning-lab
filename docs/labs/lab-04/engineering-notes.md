# Lab 04 Engineering notes

## Status and scope

Investigator: Douglas García Jiménez. Investigation opened October 1, 2026. The activation workflow completed successfully after an automation correction. The application connectivity diagnosis remains open in the retained notes. No solution to the intended scenario is disclosed here.

The reported path is client inside the cluster → Service → Pod → NGINX. This exercise does not require a public load balancer or HTTPS termination.

## Initial observations

I checked Grafana and the Pod listing. Application Pods appeared Running with no restarts. A Pod phase graph changed during the workflow period, but a Pod phase series measures object state, not an HTTP transaction. The available screenshots and notes do not establish which series caused every change.

I attempted DNS and TCP tests inside each application Pod. Both were rejected before execution by Kubernetes authorization. These attempts could not establish either DNS failure or TCP failure. I recorded the investigation separately as [INC-001](../../incidents/INC-001-pods-exec/engineering-notes.md).

## Application log evidence

The notes contain HTTP 200 entries, including a loopback request at `2026-10-01 17:32:57 +0000` and internal client requests at `17:51:22 +0000` and `17:59:42 +0000`. Those entries establish successful requests from those clients at those times. They do not prove that the affected request succeeded after the scenario change.

## Next investigation steps

Validate diagnostic authorization with the rebuilt environment, then resume the intended DNS, TCP, and HTTP tests. Capture the exact timestamp, client Pod, target, command, exit status, and output. State what each result proves and what it leaves unresolved before proposing a configuration change.

Do not infer full Service-path health from a successful localhost or port-forward request. Preserve the evidence before running restore.

## Automation issue kept separate

An earlier activation run failed in the verification script with `TypeError: 'NoneType' object is not iterable`. The maintainer corrected handling of an empty API collection and added regression coverage in commit `4add743`. Later activation succeeded according to the session record. This was an automation defect, not the learner's network root cause.

## Open questions

- Does the operator's new exec permission work in the recreated cluster?
- What do DNS, TCP, and HTTP tests show when they actually execute?
- Which component and configuration explain the reported service failure?
- What recovery check will exercise the same path as the failing request?
