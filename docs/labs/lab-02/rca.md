# Lab 02 Root cause analysis

**Status:** cause confirmed by resource and node evidence; workload recovery recorded.

## Summary and impact

A controlled update increased the application container's CPU request from 25m to 4 CPUs. Each available node had only 1930m allocatable CPU. The new Pod could not be scheduled and the rollout stalled, while the older application Pods remained running. No customer-facing outage or duration was measured.

## Evidence and contributing condition

The failing Pod requested 4000m, greater than the allocatable capacity of either node even before existing reservations. Events reported Insufficient cpu on both nodes and Too many pods on one. Low observed CPU consumption did not make the oversized request schedulable.

## Remediation and verification

The investigator proposed restoring the prior request and limit through the lab's baseline configuration. Post-recovery output recorded the two original Pods as `1/1 Running`, with zero restarts. HTTP verification is not present in that retained output, so it remains a separate check rather than an assumed result.

## Prevention and follow-up

Review resource changes against node sizes and workload measurements before rollout. Add a review check for CPU units and whether one Pod can fit on one eligible node. For real growth, separately evaluate right-sizing versus larger nodes; adding more nodes of the same insufficient size would not solve this particular mismatch.

These follow-ups are recommendations for the automation maintainer; the exercise intentionally retains its fault configuration for repeatability.

[Investigation evidence](engineering-notes.md)
