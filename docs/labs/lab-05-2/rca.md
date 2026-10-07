# Lab 05.2 — Backend protocol mismatch

**Date:** October 7, 2026. Controlled lab, not a production incident.

**Impact:** the internal ALB root request returned HTTP 502 while local HTTP requests to NGINX returned 200.

## Cause and evidence

The Ingress annotation selected HTTPS for ALB-to-backend forwarding. NGINX listened for plain HTTP on port 80. The listener accepted client HTTP on port 80, independently from the backend protocol. NGINX logged binary input consistent with TLS handshake bytes and responded 400; the client received an ALB 502.

Service selection, endpoint addresses, and named port mapping matched. Reconciliation succeeded because the configuration was accepted, not because the complete request was successful. HTTP `/healthz` checks were configured separately from backend forwarding.

## Remediation and verification

Change backend-protocol to HTTP, preserving the existing user URL and application. The operator's manual patch was denied; **Run SRE lab 05.2 → restore** provided the authorized recovery path. Afterward, the original ALB request returned HTTP 200 with 648 bytes received.

The retained evidence does not include the body contents, a recovery timestamp, target-health output, or teardown confirmation. See the [engineering notes](engineering-notes.md) for the full evidence and rejected interpretations.

## Prevention

Validate the client-facing and backend connections separately. Keep a real request check after configuration changes, even when reconciliation and health checks succeed. Use workflow restore for lab recovery rather than assuming the diagnostic operator can modify resources.

[ALB error reference](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html) · [Controller annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/)
