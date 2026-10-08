# Lab 06 — Root cause analysis

**Date:** October 8, 2026
**Scope:** controlled storage-worker exercise in `simple-test`
**Recovery:** original marker successfully read; cleanup completion not yet reported.

## Impact

The `sre-storage` worker remained Pending and could not start. No production impact or measured outage duration is claimed. The separate web application was not the failing workload.

## Root cause

The Deployment Pod template referenced PVC `sre-storage-data-v2`, which did not exist in its namespace. The intended claim, `sre-storage-data`, existed and was Bound. The scheduler rejected assignment before container startup.

## Decisive evidence

1. `FailedScheduling` explicitly reported the missing claim.
2. The Deployment and Pod descriptions referenced that exact nonexistent name.
3. Namespace PVC inventory showed the intended claim and its bound PV.
4. After recovery, reading `/data/lab-marker` returned the original `39a5a93f30a84019827abeb8d48a8d83` value.

## Correction and validation

Use the original claim in the Deployment template. Do not create a new empty volume as a substitute for the original data. The supplied marker read confirmed that the recovered workload could access the earlier content. A declaration-only check would have been insufficient.

## Prevention and follow-up

Validate namespace-scoped references before rollout; verify workload readiness and expected data, not only manifest acceptance. Keep storage recovery separate from deletion. Preserve final evidence before cleanup and Decommission. Add targeted dashboard coverage when a workload is not represented by existing filters.

The capacity failure during Provision was an independent prerequisite issue; it was not the cause of this missing-claim event.

[Detailed engineering notes](engineering-notes.md)
