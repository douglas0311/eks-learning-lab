# Lab 05.1 — Root cause analysis

**Status:** request-level recovery verified by the investigator on October 6, 2026.

## Impact and failure mechanism

The internal ALB returned HTTP 404 for GET `/`. The Ingress rule matched `/application` with Prefix semantics, so the requested root path did not match the application route. Local NGINX returned HTTP 200, and the Service had two endpoints on port 80. The controller had successfully reconciled the declared configuration; that configuration did not serve the user's intended URL.

## Evidence

- Ingress backend: `simple-test:80`; path `/application`; pathType `Prefix`.
- Requests from two source Pods to the ALB root returned HTTP 404; one complete header identified `awselb/2.0`.
- A local HEAD request returned HTTP 200 from NGINX.
- The Service's empty loadBalancer status was expected for a ClusterIP Service and was not the cause.

## Correction and verification

Restore the Ingress path to `/`, retaining Prefix matching and the existing Service/application configuration. A repeated GET to the original ALB root returned `HTTP/1.1 200 OK` at `2026-10-06 22:24:59 GMT`, with `Content-Type: text/html`.

The retained recovery excerpt does not include the response body or prove sustained availability, every backend's health, or completed teardown. See [engineering notes](engineering-notes.md) for source attribution and command context.

## Prevention and learning

Test the actual client URL and method after routing changes. Treat controller reconciliation, target health checks, and application requests as distinct checks. Record rejected hypotheses and what disproved them. Compare the requested host/path with the declared routing contract before changing working client interfaces.
