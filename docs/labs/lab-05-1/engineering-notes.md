# Lab 05.1 — Engineering notes

**Investigator:** Douglas García Jiménez
**Investigation date:** October 6, 2026
**Status:** routing fault diagnosed; the previously failing request subsequently returned HTTP 200.

## Scope and evidence sources

The internal ALB entry point failed to serve the application's root page. These notes organize Douglas's OneNote page **Lab 5.1** and preserve the progression of his hypotheses. Recovery output and the DNS-command correction come from the conversation. Duplicate command/output passages were consolidated; no unrecorded test is claimed as completed.

## 1. Initial configuration checks

```bash
kubectl -n simple-test get ingress
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

Observed configuration:

| Component | Evidence |
| --- | --- |
| Ingress | `simple-test-lab05`, class `alb`, no host restriction, backend `simple-test:80`, path `/application`, pathType `Prefix` |
| Published hostname | `internal-k8s-simplete-simplete-9f966dc949-724833531.us-east-1.elb.amazonaws.com` |
| Event | `SuccessfullyReconciled`, 5m45s, x2 over 7m41s |
| Service | ClusterIP `172.20.173.216`, TCP 80, targetPort `http`, selector `app=simple-test`, `status.loadBalancer: {}` |
| EndpointSlice | `simple-test-lwbvr`, IPv4, port 80, addresses `10.0.12.235,10.0.11.170` |
| Container | `containerPort: 80`, name `http`, TCP |

Both application Pods were `1/1 Running`, with zero restarts in the recorded snapshot:

| Pod | IP | Node |
| --- | --- | --- |
| `simple-test-67455f997b-7k9f8` | `10.0.11.170` | `ip-10-0-11-225.ec2.internal` |
| `simple-test-67455f997b-xn8x8` | `10.0.12.235` | `ip-10-0-12-55.ec2.internal` |

These checks established consistent Service selection and port mapping. They did not prove that the user's requested URL matched the Ingress rule.

## 2. Initial hypothesis — rejected

Douglas noticed the Service's empty `status.loadBalancer` and proposed adding the Ingress hostname there to make the two objects match.

Correction: this Service is `ClusterIP`; it does not own the ALB. An empty loadBalancer status is expected for this type. The Ingress publishes the ALB hostname, and status is controller-reported state rather than a routing setting to repair manually. `SuccessfullyReconciled` means the controller applied the declared configuration; an incorrect route can still reconcile successfully.

Douglas also inspected Deployments without finding supporting evidence. The source included `kubectl describe deployment simple-test -n simple-tes`; the namespace was misspelled. The corrected command is:

```bash
kubectl -n simple-test describe deployment simple-test
```

No useful output from that branch of the investigation was retained.

## 3. Reproduce the affected request

From the first Pod:

```bash
kubectl -n simple-test exec simple-test-67455f997b-7k9f8 -- \
  curl -i --connect-timeout 5 --max-time 15 \
  http://internal-k8s-simplete-simplete-9f966dc949-724833531.us-east-1.elb.amazonaws.com/
```

```text
HTTP/1.1 404 Not Found
Server: awselb/2.0
```

Repeating from `simple-test-67455f997b-xn8x8` also returned HTTP 404. Its pasted server-header excerpt was truncated to `awselb/2.`.

The original interpretation was that the request reached the Service and the Pod could not find the page. That conclusion exceeded the evidence: a response from the ALB does not prove forwarding to the application. The `Server` header was a useful clue, to be combined with routing evidence. Changing the Pod used for `exec` changes the request's source, not the backend selected by the ALB.

### Local application comparison

```bash
kubectl -n simple-test exec simple-test-67455f997b-xn8x8 -- \
  curl -I --connect-timeout 5 --max-time 15 http://127.0.0.1:80
```

```text
HTTP/1.1 200 OK
Server: nginx/1.28.
```

This established a successful local HEAD response from that Pod. It did not validate ALB routing or the complete response body. Use GET (`curl -i`) when reproducing a user's GET request; HEAD (`curl -I`) is a different method.

### DNS test correction

The conversation included `nslookup http://.../`, which returned NXDOMAIN. `nslookup` expects a hostname, without a scheme or path. That result did not establish a DNS outage. The corrected form is:

```bash
kubectl -n simple-test exec simple-test-67455f997b-xn8x8 -- \
  nslookup internal-k8s-simplete-simplete-9f966dc949-724833531.us-east-1.elb.amazonaws.com
```

A corrected lookup result was not supplied. The completed HTTP request already showed that curl could resolve and reach its destination in that test.

## 4. Revised hypothesis and corrective action

The requested path was `/`, but the Ingress declared `/application` with `pathType: Prefix`. The root request did not match that route. A Prefix match does not automatically rewrite the application's URL.

Douglas proposed restoring the Ingress path to `/` while retaining Prefix matching. This preserves the expected user URL and leaves the working Service and application unchanged. The ALB health-check path `/healthz` is independent from the user routing path; a successful health check alone would not establish that `/` is correctly routed.

## 5. Recovery evidence

After the correction, Douglas repeated the root request from `simple-test-67455f997b-7k9f8` and supplied this output in the conversation:

```text
HTTP/1.1 200 OK
Date: Tue, 06 Oct 2026 22:24:59 GMT
Content-Type: text/html
```

This is 16:24:59 in Costa Rica. It confirms that the previously failing request returned HTTP 200 in that test. The retained excerpt does not contain the body, per-target results, or sustained availability measurements. It does not establish teardown completion.

## 6. Learning and assistance

Douglas independently checked the Ingress, Service, named port mapping, EndpointSlices, and Pods. Guidance helped distinguish observed status from desired configuration and interpret the HTTP response boundary. He then revised the hypothesis using the actual request path.

His reflection: reproducing the user's error earlier would have focused the investigation sooner. The next iteration will practice that habit without assuming the same failure mechanism.

Before each investigation, record: exact URL and method, client location, expected behavior, actual response, timestamp, and the boundary each test reaches. A hypothesis should include a test that could disprove it.

[Root cause analysis](rca.md)
