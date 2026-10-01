# Lab 03 Root cause analysis

**Status:** cause supported; workload recovery and dashboard normalization reported.

## Summary and impact

The updated Pod template required a specific node hostname. That node existed and was Ready, but was cordoned. The other node could accept Pods but did not match the hostname constraint. The new Pod remained Pending and the new revision could not complete its rollout.

Existing workload Pods remained present. The retained notes do not establish a measured end-to-end outage or exact availability reduction.

## Causal chain

The required node selector narrowed placement to one node. Its `spec.unschedulable=true` then excluded that node for the new application Pod. The scheduler accurately reported a selector mismatch for one node and an unschedulable condition for the other. Ready status, low resource use, and valid hostname spelling could not override those placement restrictions.

## Recovery

The controlled restore operation restores the saved template and reverses the exercise-owned cordon. The investigator recorded two ready application Pods after recovery and reported normalization of the scheduling and replica graphs. The notes do not include the raw HTTP recovery output.

## Prevention and follow-up

Before constraining a workload to a specific node, validate eligible-node count, scheduling state, and maintenance intent. In production, prefer placement requirements tied to workload needs rather than transient hostnames unless pinning is deliberate. Keep Ready and unschedulable status visible as separate signals.

The exercise deliberately preserves the scenario for reuse. Follow-up for the investigator: record exact dashboard series names and timestamps instead of interpreting unlabeled graph values.

[Investigation evidence](engineering-notes.md)
