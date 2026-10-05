# Lab 04 Root cause analysis

**Status:** cause supported by selector, Pod-label, and EndpointSlice evidence; recovery reported by the investigator on October 5, 2026.

## Summary and impact

The internal simple-test Service had no backend endpoints because its selector (`app=simple-test-v2`) did not match the application Pods (`app=simple-test`). Access through the Service failed while the application responded locally. Both Pods were Running and Ready with zero restarts. This was a controlled lab incident; no production outage or measured duration is claimed.

## Causal chain

The Service selector excluded both intended application Pods. Kubernetes therefore had no matching Pod addresses to publish as backend endpoints for that Service. The empty EndpointSlice is consistent with the failed Service path. Healthy application processes did not compensate for a selector mismatch.

The earlier malformed DNS query and the separate exec authorization issue were diagnostic distractions, not this selector failure's cause. The retained transcript does not include the corrected DNS lookup response, so DNS success is not asserted from configuration alone.

## Remediation and validation

Douglas proposed restoring the Service selector to `app=simple-test` and subsequently confirmed resolution. The expected recovery checks are populated backend endpoints and a successful HTTP request through the same Service name. Raw post-recovery output and the exact repair operation were not retained; the status reflects operator-reported recovery rather than an independently executed check.

## Prevention and follow-up

Validate selectors against workload labels in configuration review. Include a real HTTP check through the Service from a cluster client, since localhost and port-forward checks can miss Service routing defects. Observe ready backend endpoint availability alongside Pod health. Preserve before/after output with timestamps for future investigations.

The intentionally faulty exercise remains reusable. This documentation update does not change the scenario or deploy infrastructure.

[Engineering notes and evidence](engineering-notes.md)
