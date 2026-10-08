# Lab 06 — Basic commands and how to read the results

Use this beside the [concept refresh](concept-refresh.md). The refresh explains the components; this guide gives you tools to collect evidence and build a hypothesis. It does not name the injected fault or prescribe a correction.

All commands below inspect resources. Do not run patch, delete, or apply as diagnostic experiments. Use the recovery workflow after reviewing your hypothesis.

## Before copying commands

```bash
LAB_NS='simple-test'
kubectl config current-context
kubectl -n "$LAB_NS" get pods -l app=sre-storage -o wide
```

Confirm the context is your lab cluster. Select a current storage-worker Pod from the output; do not reuse yesterday's name. Assign variables only after finding the corresponding object:

```bash
POD='replace-with-observed-pod-name'
PVC='replace-with-observed-claim-name'
PV='replace-with-observed-volume-name'
SC='replace-with-observed-storageclass-name'
```

Replace the quoted placeholder text. `$POD` means the value you assigned, and `"$POD"` keeps it as one argument. PVCs are namespaced; PVs and StorageClasses are cluster-scoped and do not need `-n`.

**Expected** below means the healthy reference, not a prediction that the activated fault will produce that result. Examples are illustrative and are not captured outputs from your cluster.

## A. Workload: what is running, and what does it need?

```bash
kubectl -n "$LAB_NS" get deployment sre-storage
kubectl -n "$LAB_NS" get pods -l app=sre-storage -o wide
kubectl -n "$LAB_NS" describe pod "$POD"
kubectl -n "$LAB_NS" get deployment sre-storage -o yaml
```

**Observe:**

| Output | What to examine | Healthy reference / interpretation |
| --- | --- | --- |
| Deployment | READY, UP-TO-DATE, AVAILABLE | One desired worker, one Ready/available replica |
| Pod | READY, STATUS, RESTARTS, NODE | Normally 1/1 Ready; node assignment identifies where it runs |
| Describe: Conditions | PodScheduled, Initialized, ContainersReady, Ready | Shows which stages completed; use the reason/message when false |
| Describe: Volumes and Mounts | Volume names, claim references, mount paths | Describes the workload's storage dependencies |
| Describe: Events | Reason, message, age, repeated count | Explains what Kubernetes attempted and why it could not proceed |
| Deployment YAML | `spec.template.spec.volumes` and container `volumeMounts` | Desired configuration for new Pods |

**Limits:** Running is not equivalent to Ready. A desired Deployment configuration is not proof that the current Pod successfully mounted storage. A Pod with no started container may have no application logs.

**Question to take away:** Which stage has not completed, and which observation supports that conclusion?

## B. StorageClass: how should storage be provisioned?

`StorageClass` is the term; `sc` is its kubectl abbreviation.

```bash
kubectl get storageclass
kubectl describe storageclass "$SC"
kubectl get storageclass "$SC" -o yaml
```

**Observe:**

- `PROVISIONER`: which driver handles provisioning. This cluster uses `ebs.csi.aws.com` for EBS.
- `VOLUMEBINDINGMODE`: when binding/provisioning should occur. `WaitForFirstConsumer` considers the consuming Pod before provisioning.
- `RECLAIMPOLICY`: what should happen to backing storage when its claim is released. This lab uses `Delete` for disposable data.
- `parameters`: storage settings such as `type: gp3` and encryption.
- A `(default)` indicator in the list identifies a default class. A dedicated class does not have to be default when explicitly selected by a claim.

**Illustrative healthy fields:**

```text
PROVISIONER:        ebs.csi.aws.com
RECLAIMPOLICY:      Delete
VOLUMEBINDINGMODE:  WaitForFirstConsumer
```

**Limits:** an existing class is a provisioning recipe, not proof that a volume has been created. Pending before a consumer exists can be expected with delayed binding.

**Question to take away:** What driver and binding behavior does the requested class specify?

## C. PVC and PV: was storage requested and assigned?

```bash
kubectl -n "$LAB_NS" get pvc
kubectl -n "$LAB_NS" describe pvc "$PVC"
kubectl -n "$LAB_NS" get pvc "$PVC" -o yaml
```

**Observe:** PVC `STATUS`, `VOLUME`, `CAPACITY`, `ACCESS MODES`, and `STORAGECLASS`. Describe also shows Events and consuming Pods when applicable. Compare the claim's request with the resulting status.

For a healthy provisioned claim, expect `Bound` and a PV name in `VOLUME`. You can print that name without modifying anything:

```bash
kubectl -n "$LAB_NS" get pvc "$PVC" \
  -o jsonpath='{.spec.volumeName}{"\n"}'
```

If it is empty, do not invent a PV name. Record that binding has not supplied one and use the claim's status/Events to understand why. If there is a name, assign it to `PV` and inspect it:

```bash
kubectl get pv
kubectl describe pv "$PV"
kubectl get pv "$PV" -o yaml
```

**Observe:**

| PV field | Meaning |
| --- | --- |
| `status.phase` | Lifecycle state, such as Bound |
| `spec.claimRef` | Namespace/name/UID of the associated claim |
| `spec.capacity` and `accessModes` | Capacity and permitted access mode |
| `spec.storageClassName` | Class associated with this volume |
| `spec.csi.driver` | CSI driver handling this volume |
| `spec.csi.volumeHandle` | Provider volume identifier; for EBS, a volume ID |
| `spec.nodeAffinity` | Node/topology restrictions for using the volume |
| `spec.persistentVolumeReclaimPolicy` | Actual reclaim policy on this PV |

**Limits:** Bound proves assignment, not successful attachment, mounting, or application reads. Do not change or delete a claim simply to make its status change.

**Question to take away:** Which facts establish binding, and which part of storage access still needs evidence?

## D. Events: why is progress blocked?

```bash
kubectl -n "$LAB_NS" get events --sort-by=.metadata.creationTimestamp
kubectl -n "$LAB_NS" get events \
  --field-selector "involvedObject.name=$POD" \
  --sort-by=.metadata.creationTimestamp
```

The second command narrows the list by object name. Keep the resource identity and timestamp when recording output; names can be reused. `describe` is often easier for a first look at one object's Events.

**Observe:** the component reporting the event, Reason, full message, time, and recurrence. A scheduling event and a mount event concern different stages. An AWS authorization error in a provisioning event concerns a different identity from a Forbidden response to your own kubectl command.

**Limits:** Events are temporary and may be aggregated. Sorting by creation timestamp does not necessarily sort repeated events by their latest occurrence. Old warnings may remain after recovery, so compare current status and current tests.

**Question to take away:** Is the message about a resource dependency, scheduling, provisioning, attachment, mounting, or access permissions? What in the text supports your classification?

## E. CSI and topology: use when the evidence points there

```bash
kubectl get csidriver ebs.csi.aws.com
kubectl -n kube-system get deployment ebs-csi-controller
kubectl -n kube-system get daemonset ebs-csi-node
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get volumeattachments
```

**Observe:** controller READY versus desired replicas; DaemonSet desired/current/ready node counts; the zone of the chosen node; VolumeAttachment PV/node references and ATTACHED status.

The CSI controller handles volume operations; the node component participates in mounting on that node. For a scheduled EBS workload, the node must be compatible with the volume's zone. Inspect the actual PV topology rather than assuming all nodes can use every volume.

If an event calls for driver logs, first obtain the Pod name:

```bash
kubectl -n kube-system get pods -o wide
CSI_POD='replace-with-observed-ebs-csi-controller-pod-name'
kubectl -n kube-system logs "$CSI_POD" -c ebs-plugin \
  --since=10m --tail=100
```

**Limits:** one controller Pod's logs do not cover every replica or sidecar. Missing VolumeAttachment may be expected if earlier stages have not completed. These checks are not mandatory detours for every Pending Pod.

## F. Container access: only after a container starts

```bash
kubectl -n "$LAB_NS" logs "$POD" -c storage-worker --tail=50
kubectl -n "$LAB_NS" exec "$POD" -c storage-worker -- ls -ld /data
kubectl -n "$LAB_NS" exec "$POD" -c storage-worker -- df -h /data
kubectl -n "$LAB_NS" exec "$POD" -c storage-worker -- cat /data/lab-marker
```

**Observe:** startup messages, directory permissions, mounted filesystem capacity, and whether the disposable marker can be read. Successful recovery requires the **original** marker; writing a replacement would invalidate that evidence.

**Limits:** an exec failure because the container has not started is not proof of bad file permissions. A directory existing is not proof that it is backed by the intended volume; relate it to the Pod volume specification and PV. The marker value is generated for each activation, so do not expect a fixed example string.

## Bring an evidence-based question

> I expected ____. Command ____ showed ____. This supports ____, but does not establish ____. My hypothesis is ____. I would test it with ____ because that would distinguish it from ____.

You do not need to use every command. Bring the outputs most relevant to the question. Requesting help to interpret a new field is part of the exercise.

Sources: [kubectl quick reference](https://kubernetes.io/docs/reference/kubectl/quick-reference/), [PersistentVolumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/).
