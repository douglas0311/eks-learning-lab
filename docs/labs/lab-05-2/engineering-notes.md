# Lab 05.2 — Engineering notes

**Investigator:** Douglas García Jiménez

**Investigation date:** October 7, 2026

**Status:** original ALB request recovered with HTTP 200 and 648 bytes received after workflow restore.

## Scope and sources

An internal client could not retrieve the `simple-test` page through the ALB. These notes organize Douglas's OneNote page **Lab 5.2**, supplemented by the conversation for the CPU/memory sample, workflow recovery, and learning reflection. Commands split across the original page were reconstructed; outputs are evidence excerpts, not a claim that every proposed test ran.

## 1. Reproduce the user request

```bash
kubectl -n simple-test get pods
kubectl -n simple-test get ingress
kubectl -n simple-test exec simple-test-7468c59f88-bgzfk -- \
  curl -i --connect-timeout 5 --max-time 15 \
  http://internal-k8s-simplete-simplete-9f966dc949-1061350200.us-east-1.elb.amazonaws.com/
```

```text
HTTP/1.1 502 Bad Gateway
Server: awselb/2.0
```

Ingress `simple-test-lab05` had class `alb`, no explicit host restriction, an internal ALB hostname, and port 80. Unlike the previous investigation, Douglas reproduced the affected request early.

Initial hypothesis: the gateway received an invalid backend response, possibly because the application was failing. Correction during review: HTTP 502 alone does not establish that the application processed a valid HTTP request. Failures establishing backend communication can also result in 502.

## 2. Validate routing references and workload selection

```bash
kubectl -n simple-test describe ingress simple-test-lab05
kubectl -n simple-test get ingress simple-test-lab05 -o yaml
kubectl -n simple-test get service simple-test -o yaml
kubectl -n simple-test get service simple-test -o wide
kubectl -n simple-test get endpointslices \
  -l kubernetes.io/service-name=simple-test -o wide
kubectl -n simple-test get pods -o wide
kubectl -n simple-test get deployment simple-test \
  -o jsonpath='{.spec.template.spec.containers[*].ports}'; echo
```

| Component | Observed evidence |
| --- | --- |
| Ingress event | `SuccessfullyReconciled`, 11m, x2 over 14m |
| Ingress route | Backend port 80, path `/` |
| Service | ClusterIP `172.20.129.42`, port 80/TCP, targetPort `http`, selector `app=simple-test` |
| EndpointSlice | `simple-test-4vqng`, IPv4, port 80, addresses `10.0.11.151,10.0.12.118` |
| Pod `simple-test-7468c59f88-bgzfk` | `10.0.12.118`, 1/1 Running, zero restarts |
| Pod `simple-test-7468c59f88-tkptp` | `10.0.11.151`, 1/1 Running, zero restarts |
| Container | Port 80 named `http`; original excerpt was truncated after this field |

The references and selected addresses were consistent. This did not validate every Ingress annotation or prove successful ALB-to-backend communication. Reconciliation success meant the declared configuration had been applied.

Repeating the ALB curl from both Pods returned the same error. These were two source clients, not proof that each request selected the source Pod as its destination.

## 3. Inspect application evidence

```bash
kubectl -n simple-test describe pod simple-test-7468c59f88-tkptp
kubectl -n simple-test logs simple-test-7468c59f88-tkptp
```

Douglas described the Pod details as clean. The logs contained successful HTTP requests and a different type of rejected input:

```text
10.0.12.103 - - [07/Oct/2026:20:29:55 +0000] "GET / HTTP/1.1" 200 648 "-" "Wget"
10.0.12.128 - - [07/Oct/2026:20:32:48 +0000] "GET / HTTP/1.1" 200 648 "-" "curl/8.17.0"
10.0.12.128 - - [07/Oct/2026:20:33:16 +0000] "\x16\x03\x01..." 400 157 "-" "-"
10.0.12.13 - - [07/Oct/2026:20:33:27 +0000] "GET / HTTP/1.1" 200 648 "-" "Wget"
10.0.11.34 - - [07/Oct/2026:21:08:31 +0000] "\x16\x03\x01..." 400 157 "-" "-"
```

Binary request excerpts are intentionally shortened. The original entries are preserved in the source backup. Timestamps are UTC; they were not converted into an inferred incident duration.

The quoted field describes the request received by NGINX; the following number is its response status. The binary prefix is consistent with a TLS handshake reaching a plain HTTP listener. That interpretation gained support from the later configuration evidence. The client-facing 502 and the NGINX 400 occur at different boundaries and need not be the same status.

Do not attribute a historical 200 entry to the current failing ALB request without time/source correlation. No request ID or packet trace was captured.

### Local comparison and resource sample

Douglas first used HEAD, then repeated with GET to match the client method:

```bash
kubectl -n simple-test exec simple-test-7468c59f88-tkptp -- \
  curl -I --connect-timeout 5 --max-time 15 http://127.0.0.1:80
kubectl -n simple-test exec simple-test-7468c59f88-tkptp -- \
  curl -i --connect-timeout 5 --max-time 15 http://127.0.0.1:80/
```

Both returned:

```text
HTTP/1.1 200 OK
Server: nginx/1.28.3
```

The conversation also supplied a `kubectl top` sample for this Pod: CPU `1m`, memory `2Mi`. These observations provided no evidence of saturation at that time. They did not categorically rule out intermittent latency or failure processing different traffic.

`-I` sends HEAD. `-i` includes headers with the normal GET response. Explicit `/` is the root path; port 80 was already present in the original local command.

## 4. Inspect the two connections separately

```bash
kubectl -n simple-test get ingress simple-test-lab05 \
  -o jsonpath='{.metadata.annotations}'; echo
```

Relevant annotations:

```text
alb.ingress.kubernetes.io/backend-protocol: HTTPS
alb.ingress.kubernetes.io/healthcheck-path: /healthz
alb.ingress.kubernetes.io/healthcheck-protocol: HTTP
alb.ingress.kubernetes.io/listen-ports: [{"HTTP":80}]
alb.ingress.kubernetes.io/scheme: internal
alb.ingress.kubernetes.io/target-type: ip
```

The ALB listener used HTTP 80, while backend forwarding used HTTPS against the application's HTTP-only port 80. Health checks used HTTP independently; this configuration could pass health checks while user requests failed. Actual target-health output was not captured.

Douglas proposed changing backend-protocol to HTTP. He also tried `https://` on the client URL and received:

```text
curl: (28) Connection timed out after 5002 milliseconds
command terminated with exit code 28
```

That test changed the client-to-ALB connection to port 443. It did not change backend forwarding, and the declared listener was HTTP 80. The timeout did not test the backend's response through the original listener.

## 5. Correction attempt and permission boundary

The proposed manual command was:

```bash
kubectl -n simple-test annotate ingress simple-test-lab05 \
  alb.ingress.kubernetes.io/backend-protocol=HTTP --overwrite
```

It failed with Forbidden: operator `day7-cli-user` could not patch `ingresses` in API group `networking.k8s.io` in namespace `simple-test`. No correction was applied by that command. This was the operator's diagnostic access boundary, separate from the routing fault. The assistant should have directed recovery through the workflow initially.

Douglas then ran **Run SRE lab 05.2 → restore**, using the existing workflow role. No expansion of the operator's permissions was required.

## 6. Recovery evidence

Douglas repeated the original HTTP ALB request from `simple-test-7468c59f88-tkptp`. The supplied output showed:

```text
100   648  100   648
HTTP/1.1 200 OK
```

This confirms a successful response and 648 bytes received for that test. The retained excerpt does not show the HTML body text, per-backend verification, or sustained availability. The exact recovery timestamp, workflow URL, and completed teardown evidence were not supplied.

## Learning and assistance

Douglas independently reproduced the failure and checked routing references, endpoints, Pod state, logs, local HTTP, and resource utilization. Guidance helped interpret the binary log entry, avoid overgeneralizing from 502 or local 200, and compare the client-facing and backend protocols. He then identified the annotation mismatch and proposed the correction.

The investigation did not require a fixed checklist at every boundary. Next time, choose the next test from the evidence and explain which hypothesis it distinguishes. A 5XX does not automatically identify the Pod as the cause.

Douglas elected to progress to storage rather than repeat more Ingress variants. The next lab retains the same reasoning method while introducing new components and signals.

[Root cause analysis](rca.md) · [Next lab](../lab-06/README.md)
