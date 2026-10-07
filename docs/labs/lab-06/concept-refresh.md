# Lab 06 — Storage refreshment

This is a vocabulary and reasoning reference, not a diagnosis of the injected fault.

## Carry forward the lessons from Ingress

Start with the expected behavior and reproduce the symptom before selecting a cause. Distinguish configuration accepted by a controller from a workload actually working. Inspect the correct connection or dependency instead of assuming that healthy surrounding components prove the whole path is healthy.

In Lab 05.2, the listener, backend connection, and health check had separate settings. Storage also has several stages; evidence from one stage does not establish success at every stage. Choose tests to distinguish hypotheses rather than repeating every command from the previous lab.

A **baseline** is evidence of healthy behavior before a change. Here, the workflow checks the same stored marker before and after a Pod replacement.

## The components

| Term | Role | Scope |
| --- | --- | --- |
| Pod volume | A volume named in the Pod specification | Pod |
| volumeMount | Where a container sees that volume, such as `/data` | Container |
| PVC — PersistentVolumeClaim | A request for storage; the Pod references it by name | Namespace |
| PV — PersistentVolume | Kubernetes representation of the backing storage | Cluster |
| StorageClass | Provisioning settings and the driver used for a class of storage | Cluster |
| CSI — Container Storage Interface | Standard interface used by storage drivers | Driver/controller and node components |
| EBS volume | The actual AWS block device | AWS Availability Zone |

The dependency relationship is:

```text
Pod volume reference → PVC → bound PV → EBS volume
                        ↓
                   StorageClass → CSI provisioning settings
```

The container's `volumeMount.name` refers to a volume in its Pod specification. The volume's `persistentVolumeClaim.claimName` refers to a PVC in the same namespace. These are different references with different meanings.

## Provisioning, scheduling, attachment, and mounting

These concepts describe related work, not a rigid sequence for every configuration:

- **Provisioning:** creating backing storage for a claim.
- **Binding:** associating a PVC with a PV.
- **Scheduling:** choosing a node compatible with the Pod's requirements, including storage topology.
- **Attachment:** making an EBS volume available to the chosen EC2 node.
- **Mounting:** exposing the filesystem to the container at its mount path.
- **Application access:** reading/writing files successfully with the container's user and permissions.

With **WaitForFirstConsumer**, provisioning/binding waits for a consuming Pod so topology can be considered. A Pending PVC before a consumer exists can therefore be expected. Pending is a state to explain with Events, not a root cause by itself.

An EBS volume belongs to an Availability Zone. A compatible node must be in that zone. The normal EBS CSI provisioner for this cluster is `ebs.csi.aws.com`; this is not EKS Auto Mode.

## Access modes and persistence

**ReadWriteOnce (RWO)** means the volume can be mounted read-write by one node. It does not mean “exactly one Pod”; multiple Pods on that node can potentially access it. This lab uses one worker replica and a Recreate strategy to keep the first storage exercise focused.

A filesystem inside a container is not the same as a persistent volume. An **emptyDir** survives container restarts within the same Pod but is removed with that Pod. A PVC-backed EBS volume can outlive an individual Pod. Survival depends on the storage lifecycle, not merely a directory being named `/data`.

## Deletion and ownership

- **Reclaim policy Delete:** deleting the claim can lead to removal of the dynamically provisioned PV and backing volume.
- **Reclaim policy Retain:** backing storage remains for deliberate recovery or disposal.
- **Finalizer:** cleanup coordination recorded on an object. Removing one manually can bypass required cleanup.

This lab uses Delete for disposable data. Deleting a Pod is not equivalent to deleting its PVC. Do not delete a PVC to test a hypothesis: that may remove the very data you need to preserve.

The recovery workflow validates the original marker without writing it again. Cleanup deliberately removes the worker and its data after evidence collection.

## Reading signals carefully

| Observation | Useful interpretation | Limit |
| --- | --- | --- |
| Pod Pending | Startup has not completed | Does not identify scheduling, reference, or provisioning cause by itself |
| PVC Pending | No completed binding yet | May be expected with delayed binding |
| PVC Bound | A PV was assigned | Does not prove successful attachment, mount, or application reads |
| Pod Running | Containers have started or are starting/restarting | Does not establish readiness or data correctness |
| Pod Ready | Its readiness condition is satisfied | Understand what the configured probe checks |
| CSI controller healthy | Driver controller is running | Does not prove every claim can provision successfully |
| Forbidden | The requested operation is unauthorized | Does not establish a storage fault |

Controller operations use the CSI role's AWS permissions. Your diagnostic Kubernetes identity and the workflow's recovery identity have different permissions, as in Lab 05.2.

## Read-only command reference

Choose commands based on the question you are answering; this is not a required sequence.

```bash
kubectl -n simple-test get pods -l app=sre-storage -o wide
kubectl -n simple-test describe deployment sre-storage
kubectl -n simple-test get deployment sre-storage -o yaml
kubectl -n simple-test get pvc
kubectl -n simple-test describe pvc <claim-name>
kubectl get pv
kubectl describe pv <volume-name>
kubectl get storageclass
kubectl describe storageclass <class-name>
kubectl -n simple-test describe pod <pod-name>
kubectl -n simple-test get events --sort-by=.metadata.creationTimestamp
kubectl -n kube-system get deployment ebs-csi-controller
kubectl -n kube-system get daemonset ebs-csi-node
```

Replace placeholders with observed names. Pod logs/exec may be unavailable when no container has started; Events and specifications can still provide evidence. Your operator can inspect resources; recovery is performed through the workflow rather than manual patches.

## Self-check

1. Which object does a Pod reference directly: a PVC or a PV?
2. Why can a Pending claim be expected with WaitForFirstConsumer?
3. Does Bound prove that the application can read its files?
4. What should persist after replacing a Pod, and how could you demonstrate it?
5. Why is deleting a PVC a consequential action in this lab?

Sources: [Kubernetes persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/), [EBS CSI on EKS](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html).
