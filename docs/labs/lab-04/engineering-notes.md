# Lab 04 Engineering notes

## Status and scope

Investigator: Douglas García Jiménez. Investigation opened October 1, 2026. The activation workflow completed successfully after an automation correction. The Service selector mismatch was identified during the October 5 follow-up. OneNote Lab-04.1 records the corrected selector and an HTTP 200 recovery response on October 5; a post-recovery EndpointSlice listing was not retained.

The reported path is client inside the cluster → Service → Pod → NGINX. This exercise does not require a public load balancer or HTTPS termination.

## Initial observations

I checked Grafana and the Pod listing. Application Pods appeared Running with no restarts. A Pod phase graph changed during the workflow period, but a Pod phase series measures object state, not an HTTP transaction. The available screenshots and notes do not establish which series caused every change.

I attempted DNS and TCP tests inside each application Pod. Both were rejected before execution by Kubernetes authorization. These attempts could not establish either DNS failure or TCP failure. I recorded the investigation separately as [INC-001](../../incidents/INC-001-pods-exec/engineering-notes.md).

## Application log evidence

The notes contain HTTP 200 entries, including a loopback request at `2026-10-01 17:32:57 +0000` and internal client requests at `17:51:22 +0000` and `17:59:42 +0000`. Those entries establish successful requests from those clients at those times. They do not prove that the affected request succeeded after the scenario change.

## Lab 04.1 follow-up — October 5, 2026

### Diagnostic access

An actual `kubectl exec ... -- id` succeeded and returned `uid=101(nginx) gid=101(nginx)`. This establishes successful execution inside the container; nginx is the container's Linux identity, not the operator's IAM identity. The earlier actual Forbidden response is documented separately in INC-001.

The mentor's earlier verification command was incorrect: `kubectl auth can-i create pods/exec` parses `exec` as a resource name. Use:

```bash
kubectl auth can-i create pods --subresource=exec -n simple-test
```

A `no` from the former command did not establish that exec remained forbidden. No broader permissions were justified by that result.

### Investigation evidence

- OneNote records HTTP/1.1 200 OK from a localhost HEAD request on port 80, while the HEAD request through the Service from Pod `simple-test-7649f694f5-9xk9c` failed: `curl: (7) Failed to connect to simple-test.simple-test.svc.cluster.local port 80 after 7 ms: Could not connect to server`.
- An initial DNS error referred to `simple-test.simple-test.svc.cluster.loca`, missing the final `l`. That NXDOMAIN response cannot establish failure of the correctly spelled name. The corrected lookup output in OneNote resolves `simple-test.simple-test.svc.cluster.local` to `172.20.205.240`, using DNS server `172.20.0.10`.
- `/etc/resolv.conf` contained `nameserver 172.20.0.10` and `search simple-test.svc.cluster.local svc.cluster.local cluster.local ec2.internal`.
- Service `simple-test` existed in namespace `simple-test`, with ClusterIP `172.20.205.240`, port `80/TCP`, and selector `app=simple-test-v2`.
- EndpointSlice `simple-test-4kc4h` showed IPv4 with PORTS and ENDPOINTS both `<unset>`.
- Pods `simple-test-7649f694f5-2kf2d` and `simple-test-7649f694f5-9xk9c` were both Running, 1/1 Ready, with zero restarts. Both had label `app=simple-test` and template hash `7649f694f5`.

### Hypothesis and conclusion

I compared the Service selector with the intended backend Pods' labels. The Service selected `app=simple-test-v2`, while both Pods had `app=simple-test`. The mismatch explains the empty backend endpoint set and why Service access failed even though the application responded locally. I proposed restoring the Service selector to `app=simple-test` and validating the same HTTP path again.

### Recovery evidence from OneNote Lab-04.1

The post-fix Service listing shows the same ClusterIP (`172.20.205.240`) with selector `app=simple-test`. Both application Pods remained 1/1 Running with zero restarts. Douglas repeated the same HTTP HEAD request from Pod `simple-test-7649f694f5-9xk9c` through the Service name and recorded:

```text
HTTP/1.1 200 OK
Server: nginx/1.28.3
Date: Mon, 05 Oct 2026 23:19:15 GMT
Content-Type: text/html
Content-Length: 648
```

That response date is 17:19:15 in Costa Rica (UTC-6). This validates recovery of the tested Service path. It does not prove both backends were exercised. The exact repair command and post-recovery EndpointSlice listing were not retained, and no measured outage duration is claimed.

### Technical clarifications and lessons

- The DNS server IP and the Service ClusterIP serve different purposes and need not match.
- A DNS response proves the server answered that query; NXDOMAIN does not prove successful name resolution.
- Search entries are suffixes. The short name `simple-test` plus `simple-test.svc.cluster.local` yields `simple-test.simple-test.svc.cluster.local`; resolv.conf was not missing a component.
- CoreDNS discovers Service records through Kubernetes. Finding a Service through kubectl proves its API object exists, not that HTTP requests succeed.
- DNS resolution and Service backend selection are separate checks. After resolution, traffic to the Service requires usable backend endpoints.
- EndpointSlice reconciliation is automatic; the operator does not manually register Pod IPs after correcting a selector.
- Healthy Pods and infrastructure metrics do not prove end-to-end application reachability.

The investigator reported spending extra time recalling Service, EndpointSlice, and DNS relationships. Mentoring supplied command guidance and interpretation; Douglas compared the actual selector and labels and articulated the failure mechanism and proposed remediation. The improvement is a repeatable diagnostic checklist, not memorizing every command.

### Reusable validation commands

```bash
POD=simple-test-7649f694f5-2kf2d # Replace if the Pod has changed.
kubectl -n simple-test exec "$POD" -- curl -i --connect-timeout 5 --max-time 15 http://127.0.0.1:80
kubectl -n simple-test exec "$POD" -- nslookup simple-test.simple-test.svc.cluster.local
kubectl -n simple-test get service simple-test -o wide
kubectl -n simple-test get endpointslices -l kubernetes.io/service-name=simple-test -o wide
kubectl -n simple-test get pods --show-labels
kubectl -n simple-test exec "$POD" -- curl -i --connect-timeout 5 --max-time 15 http://simple-test.simple-test.svc.cluster.local
```

Record timestamps, output, and exit status. Compare results before and after recovery; do not infer successful Service access from a localhost request alone.

## Automation issue kept separate

An earlier activation run failed in the verification script with `TypeError: 'NoneType' object is not iterable`. The maintainer corrected handling of an empty API collection and added regression coverage in commit `4add743`. Later activation succeeded according to the session record. This was an automation defect, not the learner's network root cause.

## Evidence provenance

This update uses the commands and outputs pasted by Douglas and his recovery confirmation in the October 5 conversation. OneNote Lab-04.1 was subsequently read and cross-checked in My Notebook → SRE - FinOps → New Section Group → New Section 1. It supplies the corrected DNS response, the curl connection error, and the post-fix Service listing and HTTP response. Raw command outputs were preserved during the editorial update; misleading interpretations were corrected. Historical October 1 observations above remain separate from the recreated environment.

[Root cause analysis](rca.md)
