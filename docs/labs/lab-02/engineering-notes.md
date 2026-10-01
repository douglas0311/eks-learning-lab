# Lab 02 Engineering notes

## Context

Investigator: Douglas García Jiménez. A new application Pod remained Pending while two older Pods continued running. The notes identify failing ReplicaSet `simple-test-78cc77fdc7` and healthy ReplicaSet `simple-test-8555f99cd9`.

## Evidence and initial hypothesis

I inspected the Pending Pod's events:

```text
0/2 nodes are available: 1 Too many pods, 2 Insufficient cpu.
preemption: 0/2 nodes are available: 2 Preemption is not helpful for scheduling.
```

The scheduler reported more than one constraint. The CPU mismatch alone was sufficient to prevent placement on either node; the Pod count limit on one node was an additional observed constraint, not something to omit from the record.

I compared the new and healthy Pod resource specifications:

| Setting | Healthy Pod | Pending Pod |
| --- | --- | --- |
| CPU request | 25m | 4 |
| CPU limit | 100m | 4 |
| Memory request | 32Mi | 32Mi |
| Memory limit | 64Mi | 64Mi |

`kubectl top nodes` showed 58m and 67m CPU usage, approximately 3% on each node. My initial interpretation was that the nodes had enough CPU because current usage was low. I also initially misread the unqualified value `4` as millicores.

A follow-up capacity check showed:

```bash
kubectl get nodes   -o custom-columns='NAME:.metadata.name,CPU_CAPACITY:.status.capacity.cpu,CPU_ALLOCATABLE:.status.allocatable.cpu'
```

```text
NAME                           CPU_CAPACITY   CPU_ALLOCATABLE
ip-10-0-11-216.ec2.internal      2              1930m
ip-10-0-12-44.ec2.internal       2              1930m
```

## Corrected interpretation

`4` means four CPUs, or 4000m. It is 160 times the previous 25m request and exceeds each node's entire 1930m allocatable CPU. Current consumption is not the scheduler's reservation budget. A single Pod's request cannot be split between the two nodes. Existing requests further reduce remaining capacity.

The correct finding is **an oversized CPU request**, not insufficient CPU requested by the application. The new ReplicaSet reflects a changed Pod template; it did not independently increase the request. See the [Kubernetes resource documentation](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

## A diagnostic command that did not test the hypothesis

My notes recorded `kubectl logs ... -- previous`, which returned a complaint about a container named `previous`. The intended option is `--previous`, without a space. Even with correct syntax, a Pod that never started has no previous container execution log. Scheduler events are the relevant evidence here.

The `0/1` READY column means zero of one containers is ready; it is not the Deployment's desired-versus-actual replica count.

## Recovery and learning

I recommended restoring the previous resource configuration, then investigating why the request changed. After recovery the retained output showed both original application Pods `1/1 Running` with zero restarts. This supports workload recovery; the excerpt alone does not establish end-to-end HTTP availability.

I performed the initial investigation and comparison independently. Review assistance clarified CPU units, resource requests, and the node allocatable check. The next time I see Insufficient cpu, I will compare requests and allocatable capacity before using utilization to support a conclusion.

[Root cause analysis](rca.md)
