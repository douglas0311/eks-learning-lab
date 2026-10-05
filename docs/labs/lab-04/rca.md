# Lab 04 Root cause analysis

**Status:** cause supported by selector, Pod-label, and EndpointSlice evidence; HTTP recovery documented in the investigator’s OneNote notes on October 5, 2026.

## Summary and impact

The internal simple-test Service had no backend endpoints because its selector (`app=simple-test-v2`) did not match the application Pods (`app=simple-test`). Access through the Service failed while the application responded locally. Both Pods were Running and Ready with zero restarts. This was a controlled lab incident; no production outage or measured duration is claimed.

## Causal chain

The Service selector excluded both intended application Pods. Kubernetes therefore had no matching Pod addresses to publish as backend endpoints for that Service. The empty EndpointSlice is consistent with the failed Service path. Healthy application processes did not compensate for a selector mismatch.

The earlier malformed DNS query and the separate exec authorization issue were diagnostic distractions, not this selector failure's cause. OneNote records the corrected DNS lookup resolving the full Service name to 172.20.205.240. DNS resolution succeeded while the Service HTTP request failed with curl error 7.

## Remediation and validation

Douglas proposed restoring the Service selector to `app=simple-test`. His post-fix Service listing confirms that selector, and the repeated HTTP HEAD request through the same Service name returned `HTTP/1.1 200 OK`, with response date `Mon, 05 Oct 2026 23:19:15 GMT`. The retained OneNote output establishes recovery of that tested path, not that both backend Pods were individually exercised. A post-recovery EndpointSlice listing and the exact repair operation were not retained. These are reviewed investigator outputs; the assistant did not run live recovery checks.

## Prevention and follow-up

Validate selectors against workload labels in configuration review. Include a real HTTP check through the Service from a cluster client, since localhost and port-forward checks can miss Service routing defects. Observe ready backend endpoint availability alongside Pod health. Preserve before/after output with timestamps for future investigations.

The intentionally faulty exercise remains reusable. This documentation update does not change the scenario or deploy infrastructure.

[Engineering notes and evidence](engineering-notes.md)
