# Lab 03 Engineering notes

## Context and timeline

Investigator: Douglas García Jiménez. Controlled scheduling exercise, September 30, 2026, as recorded in the session history. The notes use local times without an explicit timezone; the user's working timezone was America/Costa_Rica.

I opened Grafana around 11:22 and recorded initial observations around 11:25. I later correlated the SchedulingDisabled signal and a Pending application Pod with approximately 11:27, the observed start of the issue. I did not record an exact recovery timestamp.

## What the dashboard did and did not establish

The scheduling-disabled signal changed from zero to one. Node Ready stayed at one, node pressure stayed at zero, and container restarts stayed at zero. These observations directed attention to scheduling rather than container startup.

The raw notes describe desired/available replicas as “2 then 1” and allocatable CPU as “2 cores.” Without the original panel series and exact values, those notes are insufficient to reconstruct exact replica availability or CPU allocation. The CLI evidence below is the stronger basis for the diagnosis. A plotted memory limit of 64Mi is not evidence of memory consumption or pressure.

## Investigation

The affected Pod was `simple-test-7b8c5b8bd6-58n2g`. Its event reported:

```text
0/2 nodes are available: 1 node(s) didn't match Pod's node affinity/selector,
1 node(s) were unschedulable.
```

I compared placement constraints on the Pending Pod and a healthy Pod:

```bash
kubectl -n simple-test get pod <pod-name>   -o jsonpath='{.spec.nodeSelector}{"\n"}{.spec.affinity}{"\n"}'
```

| Pod | nodeSelector |
| --- | --- |
| Pending | amd64 architecture and hostname ip-10-0-11-219.ec2.internal |
| Healthy | amd64 architecture only |

I then checked whether that hostname existed and inspected its status:

```bash
kubectl get nodes -L kubernetes.io/hostname,kubernetes.io/arch
kubectl get nodes --field-selector spec.unschedulable=true
kubectl get nodes --field-selector spec.unschedulable=false
```

```text
ip-10-0-11-219.ec2.internal   Ready,SchedulingDisabled   amd64
ip-10-0-12-221.ec2.internal   Ready                      amd64
```

The requested hostname was correct. The decisive observation was the additional SchedulingDisabled status on that matching node. The other node was schedulable but did not satisfy the hostname selector.

## Hypothesis refinement

I first suspected a label mismatch. Comparing the full node status showed that matching labels alone were insufficient: the only matching node was cordoned. Both conditions in the scheduling event mattered.

The configuration shown is `nodeSelector`, not Pod affinity. Node selectors and node affinity concern node labels; Pod affinity concerns the placement of other Pods. See [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/).

My attempted `-- previous` log command was malformed. Correcting it to `--previous` would not produce container history for this unscheduled Pod. The FailedScheduling event, placement requirements, and node status supported the conclusion.

## Recovery and verification

I proposed either restoring scheduling on the matching node after confirming why it was cordoned, or removing the unintended hostname restriction from the Deployment template. In a real environment, I would consult the node/operator owner before overriding maintenance intent.

The lab's restore operation returned the node and application template to their recorded configuration. The retained post-recovery listing showed two application Pods `1/1 Running`. I also reported that the replica and scheduling graphs returned to normal. Node readiness had already been healthy; this should not be reported as recovery from NotReady.

## Learning record

I requested two commands and conceptual guidance, then compared the constraints and identified SchedulingDisabled. The reusable question is: “Does an eligible node also accept new Pods?” A node can be Ready while excluding new placements.

[Root cause analysis](rca.md)
