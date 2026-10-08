# Lab 06 — Engineering notes

**Investigator:** Douglas García Jiménez
**Date:** October 8, 2026
**Status:** root cause identified; original marker successfully read after recovery. Cleanup and Decommission completion are not yet evidenced.

## Scope and sources

Source: Douglas's OneNote page **Lab 6**, with the conversation supplying his clarification about comparison and the recovery output. This is a controlled lab, not a production outage. Exact activation/recovery timestamps and workflow URLs were not supplied. The screenshots remain in OneNote; the excerpts below come from its text and the conversation.

The separate storage worker `sre-storage` in namespace `simple-test` could not start. The existing `simple-test` web application was a comparison point, not an equivalent replica of the failing worker.

## 1. Observe the symptom

Douglas saw no obvious change in the Grafana view he was using, then found:

```text
sre-storage-8567b7bf64-d7h9g   0/1   Pending   0
```

The output showed no assigned node or Pod IP. A dashboard without an obvious change does not prove health; its workload filters and query scope matter. No dashboard coverage conclusion was established from that observation alone.

```bash
kubectl describe pod sre-storage-8567b7bf64-d7h9g -n simple-test
```

Relevant event:

```text
Warning FailedScheduling
0/3 nodes are available: persistentvolumeclaim "sre-storage-data-v2" not found.
```

This blocked scheduling before the application container started. There were no application logs to inspect yet; `--previous` would not help with a container that had never run.

## 2. Trace the declared dependency

Douglas inspected the Deployment configuration:

```bash
kubectl get deployment -n simple-test -o yaml
```

```yaml
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: sre-storage-data-v2
```

The Pod description independently showed `ClaimName: sre-storage-data-v2` and a mount at `/data`. A mount declaration describes intent; it does not establish that the mount succeeded.

Other recorded fields were `SEED: false` and `MARKER: 39a5a93f30a84019827abeb8d48a8d83`.

## 3. Compare for orientation

Douglas compared a running web Pod, `simple-test-54b5776bf7-5hwsl`, with the storage worker. The web Pod used a temporary `emptyDir` mounted at `/tmp`; the worker requested persistent storage at `/data`.

He explicitly clarified that this comparison helped him identify which components to inspect. He did **not** treat different storage configurations in different applications as proof of a defect. That is a useful distinction: comparison generates questions; matching a failed reference to the resource inventory supplies stronger evidence.

## 4. Inspect storage configuration and inventory

```bash
SC='sre-lab06-gp3'
kubectl describe storageclass "$SC"
kubectl get storageclass "$SC" -o yaml
```

| Observed field | Value | Meaning and limit |
| --- | --- | --- |
| Provisioner | `ebs.csi.aws.com` | Class uses the EBS CSI provisioner; does not prove this Pod has a volume |
| Type | `gp3` | Requested EBS volume type |
| Encryption | `true` | Class requests encryption |
| Reclaim policy | `Delete` | Deleting the claim can lead to deletion of its backing volume |
| Binding mode | `WaitForFirstConsumer` | Provisioning/binding considers consumer scheduling requirements |
| Events | none | No events on this object; not proof that the storage path is healthy |

The first storage inspections did not immediately answer the question. Douglas continued toward the specific missing dependency instead of abandoning the hypothesis.

```bash
LAB_NS='simple-test'
kubectl -n "$LAB_NS" get pvc
kubectl -n "$LAB_NS" describe pvc sre-storage-data
```

```text
NAME               STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
sre-storage-data   Bound    pvc-c0ae1304-2eff-4650-a53e-4da617dfff59       1Gi        RWO            sre-lab06-gp3
```

The existing claim was `sre-storage-data`, in the same namespace, and was Bound. The requested `sre-storage-data-v2` was absent from the supplied inventory. Bound established the existing claim's association with a PV; it did not establish a successful mount in the affected Pod.

## 5. Hypothesis and cause

The Deployment template referenced a nonexistent PVC. The scheduler could not assign the worker Pod to a node because the required claim was absent from its namespace.

Douglas proposed changing the claim reference to the intended existing PVC, `sre-storage-data`. The correction belongs in the Deployment's Pod template so replacement Pods inherit it. Creating an empty replacement claim merely to satisfy the incorrect name would not recover the original data.

The event, Deployment reference, and namespace inventory support this diagnosis. `Pending` alone would not identify a node problem, and the error alone would not prove that an EBS volume had been created.

## 6. Recovery evidence

After recovery, Douglas supplied:

```bash
kubectl -n simple-test exec deployment/sre-storage \
  -c storage-worker -- cat /data/lab-marker
```

```text
39a5a93f30a84019827abeb8d48a8d83
```

The output matches the marker recorded before recovery. This validates readability of the original marker through the recovered workload, beyond checking that its configuration references the intended claim. The trailing `%` in the terminal paste is consistent with zsh marking output without a final newline; it is not part of the recorded marker.

The evidence does not claim a full filesystem integrity audit, a new post-recovery PVC UID capture, or a completed teardown. Recovery and cleanup are different operations: recovery preserves the disposable data; cleanup intentionally removes it.

## Learning and assistance

Douglas independently connected the scheduling event, template reference, and actual claim inventory. Earlier exposure and the command guide helped him orient in an unfamiliar area. Assistance clarified terminology and proposed reading the pre-existing marker to close the investigation.

Corrections retained from the review:

- Pods and PVCs belong to a namespace; nodes, PVs, and StorageClasses are cluster-scoped.
- A Pending Pod does not by itself locate the fault at the node.
- Data lives on the backing volume, not inside the PVC API object.
- Replacing a Pod can preserve data on its existing persistent volume. Deleting the PVC is a separate lifecycle action.
- An `emptyDir` survives container restarts within the same Pod, but is removed when the Pod is removed.
- Useful troubleshooting does not require every command to produce the answer. State what each observation establishes and what remains unknown.

## Separate environment prerequisite incident

Before this exercise, Provision hit the two-node pod-slot limit after EBS CSI was added. Both `t3.small` nodes had 11 assigned Pods; the Prometheus admission hook could not schedule, and Helm timed out. Terraform's fixed node count was changed from two to three. This capacity issue was separate from the deliberately injected missing-claim reference.

[Root cause analysis](rca.md) · [Next lab](../lab-07/README.md)
