# Lab 07 — Command companion

These are diagnostic tools, not a mandatory sequence or the injected solution.
All commands below are read-only. Replace `POD` with an observed application Pod
name. Expected observations describe a healthy reference, not measured results.

```bash
LAB_NS='simple-test'
kubectl config current-context
kubectl -n "$LAB_NS" get pods -l app=simple-test -o wide
POD='replace-with-an-observed-pod-name'
```

## A. What does the autoscaler report?

```bash
kubectl -n "$LAB_NS" get hpa
kubectl -n "$LAB_NS" describe hpa simple-test
kubectl -n "$LAB_NS" get hpa simple-test -o yaml
```

Observe target reference, metric type, current/target values, minimum/maximum,
current/desired replicas, conditions, reasons, and events. A healthy resource HPA
has a usable current measurement after collection begins. `<unknown>` means the
measurement is not available for that evaluation; it does not mean zero usage.
No replica change alone proves neither health nor failure.

## B. What configuration is requested, and what do actual Pods have?

```bash
kubectl -n "$LAB_NS" get deployment simple-test -o yaml
kubectl -n "$LAB_NS" describe deployment simple-test
kubectl -n "$LAB_NS" get pod "$POD" -o yaml
kubectl -n "$LAB_NS" describe pod "$POD"
```

Compare the template and actual container settings, readiness, ownership, and
resource requests/limits. Admission defaults and a rollout in progress can make
actual Pods differ from a new template. An observed difference is a question to
investigate, not automatically the cause. Ready Pods establish readiness, not
HPA health.

## C. Are resource measurements available?

```bash
kubectl -n "$LAB_NS" top pods --containers
kubectl top nodes
kubectl -n kube-system get deployment metrics-server
kubectl get apiservice v1beta1.metrics.k8s.io
```

Observe measurement availability, units, and the metrics API Available condition.
`1m` means one millicore; `1` means one core. These commands show usage rather than
reserved capacity. A healthy Metrics Server does not establish that every HPA
configuration is valid. If access is Forbidden, record the permission boundary;
do not interpret it as a measurement failure in the cluster.

## D. Is there a workload rollout or a scheduling problem?

```bash
kubectl -n "$LAB_NS" get deployment simple-test
kubectl -n "$LAB_NS" get replicasets -l app=simple-test
kubectl -n "$LAB_NS" get pods -l app=simple-test -o wide
kubectl -n "$LAB_NS" get events --sort-by=.metadata.creationTimestamp
```

Compare desired, updated, ready, and available replicas. Inspect scheduling events
if a Pod is Pending. Event creation time is not necessarily its latest occurrence;
repeated events can be aggregated. Old events can outlive the condition they describe.

## E. Does the application itself respond?

```bash
kubectl -n "$LAB_NS" exec "$POD" -c simple-test -- \
  curl -i --connect-timeout 5 --max-time 15 http://127.0.0.1:80/
kubectl -n "$LAB_NS" exec "$POD" -c simple-test -- \
  curl -i --connect-timeout 5 --max-time 15 http://simple-test.simple-test.svc.cluster.local:80/
```

Expect HTTP 200 with the simple-test page in a healthy setup. The first test uses
the local container listener; the second traverses the Service. Neither generates
sustained load nor proves scale-out. Do not start an unbounded load generator.

## F. What can historical monitoring add?

In Grafana, match namespace/workload filters and the incident time window. Compare
CPU usage, requested CPU, desired replicas, and available replicas when those
panels exist. Check query units and labels before interpreting an empty graph.
The existing dashboard may not expose HPA conditions; use Kubernetes status for
those. A flat graph can mean stable behavior, absent series, or the wrong scope.

## Evidence template

> Question: ...
> Command and time: ...
> Relevant output: ...
> This supports ... but does not establish ...
> Next distinguishing test: ...

After restore, verify application response and a usable HPA measurement. Record
whether real scale-out was tested; this lab's restore/check operations do not
claim a load test.
