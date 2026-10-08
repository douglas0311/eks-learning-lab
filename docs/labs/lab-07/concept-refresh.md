# Lab 07 — Concept refresh

## Carry forward from Lab 06

An object reference is not proof of a working dependency. Compare the requested
configuration with the real object and its status. Read the full event before
choosing a subsystem. Comparisons orient investigation; differences are not
automatically defects. Close recovery with a functional test relevant to the
failure, as you did when reading the original storage marker.

## Components and boundaries

| Component or term | Meaning |
| --- | --- |
| HPA | HorizontalPodAutoscaler: evaluates measurements and adjusts a target workload's replica count |
| scaleTargetRef | The workload an HPA controls; check namespace, kind, and name |
| Deployment | Reconciles the desired number of application replicas |
| Metrics Server | Supplies recent resource measurements through the resource metrics API |
| Prometheus / Grafana | Historical monitoring and visualization; this lab's resource HPA does not query Grafana |
| CPU request | A scheduling reservation and denominator for CPU utilization targets |
| CPU limit | A runtime CPU ceiling; distinct from the request |
| Utilization | Usage expressed relative to requested resources, not a percentage of a whole node |
| minReplicas / maxReplicas | Bounds on the workload replica count, not a promise that all replicas can schedule |
| Stabilization | Controller history used to avoid rapid scaling reversals |
| Node scaling | Changes cluster capacity; different from HPA, which changes workload replicas |

For example, 20m CPU usage against a 50m request is 40% utilization. This is an
illustration, not an observed measurement. A lower request changes the percentage
without changing measured CPU usage. More replicas can still remain Pending if
node capacity is insufficient.

## Reading HPA status

- **AbleToScale:** can the controller interact with the target's scale information?
- **ScalingActive:** can it evaluate the configured scaling metric?
- **ScalingLimited:** is a recommendation constrained by the configured bounds?

Always read status, reason, and message together. A limit-related condition can be
normal at low demand. Unknown is not the same as zero. Metrics and controller
status are asynchronous; capture timestamps and allow reconciliation time.

## Questions to ask yourself

1. Which component measures usage, and which changes the replica count?
2. Does a working HTTP endpoint prove the autoscaler is healthy?
3. What could explain desired replicas exceeding available replicas?
4. What evidence distinguishes low demand from an inability to evaluate demand?

Reference: [Kubernetes HPA documentation](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/).
