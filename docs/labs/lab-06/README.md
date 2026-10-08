# Lab 06 — A storage-dependent workload does not become ready

**Status:** prepared October 7, 2026; live Provision and activation pending.

A small storage worker previously became ready and retained its data across a Pod replacement. Following a workload configuration change, the worker no longer becomes ready. Investigate why it cannot resume normal operation while preserving its existing data.

## Expected behavior

- Namespace: `simple-test`.
- Workload: Deployment `sre-storage`, one replica.
- The worker uses a mounted persistent volume at `/data`.
- When healthy, its container verifies the existing marker and the Pod becomes Ready.
- The original web application remains available internally. This worker has no Service, Ingress, or HTTP endpoint.

Your task is to identify the failing stage, collect evidence, form a testable hypothesis, and propose the smallest correction that preserves the existing data. Do not delete storage objects or force-remove finalizers as a diagnostic shortcut.

Read the [concept refresh](concept-refresh.md), [basic command guide](command-guide.md), and [start guide](../../simple-test/lab-06-start.md). Record observations in the [engineering notes](engineering-notes.md). Implementation and tests contain spoilers and should be reviewed after the investigation.

A green activation means the baseline and intended symptom were verified. If activation fails, preserve the first error rather than assuming the exercise is ready. Ask for a guiding question when a component or event is unfamiliar.

## Environment capacity

The managed node group uses three nodes. With the current `t3.small` configuration,
each node advertises 11 allocatable pod slots (33 total). Node-level DaemonSets
also consume slots on every new node, so not all additional slots are available
to applications. CPU and memory requests remain separate scheduling constraints.

Provision on October 8, 2026 exposed the previous two-node limit: both nodes had
11 assigned pods after EBS CSI was added. The Prometheus admission patch Job
could not schedule (`Too many pods`), and Helm timed out in its post-install hook.
Prometheus also reported insufficient memory on one node. This was an environment
capacity issue, separate from the intentional storage exercise.

After publishing the capacity change, start a **new Terraform Provision run from
main**. A re-run of the old failed run uses its old commit. Terraform uses the
existing S3 state to reconcile the partially provisioned environment. Verify three
Ready nodes, the monitoring workloads, and the Provision result before deploying
the application or activating the exercise. The third node adds running cost and
is removed with the managed node group during Decommission.
