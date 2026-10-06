# Lab 05 — Engineering notes

**Investigator:** Douglas García Jiménez
**Review date:** October 6, 2026
**Status:** intended cause diagnosed; a separate controller IAM defect blocked the original recovery attempt. Later Lab 05.1 evidence demonstrates a working ALB request, not a retest of this original run.

## Scope and sources

A controlled exercise introduced an internal Ingress for `simple-test`. The entry point did not become available. These notes organize Douglas's OneNote page **Lab 5**, supplemented by the permission error and workflow result supplied in the conversation. Commands below are reconstructed into executable form; proposed checks are not presented as observed results.

## Component refresher

- **Ingress:** desired HTTP routing configuration.
- **AWS Load Balancer Controller:** translates that configuration into AWS resources and reconciles changes.
- **ALB:** handles client traffic once provisioned and configured.
- **Service port:** the port clients use on the Service and the port referenced by the Ingress backend.
- **targetPort:** the destination port on selected Pods; a name must resolve against a named container port.

With ALB target type `ip`, the controller uses the Service and EndpointSlices to identify Pod targets. The ALB can forward directly to Pod IPs; the Service ClusterIP is not necessarily a data-plane hop.

## Evidence and reasoning

### 1. Inspect the entry point and controller events

```bash
kubectl -n simple-test get ingress
kubectl -n simple-test describe ingress simple-test-lab05
```

Observed: name `simple-test-lab05`, class `alb`, host `*`, port `80`, and an empty ADDRESS. The empty address established that no hostname had been published; it did not identify the cause. Host `*` represented no explicit host restriction.

The Ingress was internal, used IP targets, listened on HTTP 80, and checked `/healthz`. Its backend was `simple-test:8080`.

```text
Warning FailedBuildModel 4m14s (x18 over 15m) ingress
Failed build model due to ingress: simple-test/simple-test-lab05:
unable to find port 8080 on service simple-test/simple-test
```

Douglas interpreted this as the controller being unable to resolve a backend port. “Build model” refers to constructing the desired AWS resource configuration. `simple-test/simple-test` identifies namespace/Service, not two different Services.

### 2. Compare the referenced port with the offered port

```bash
kubectl -n simple-test get ingress simple-test-lab05 -o yaml
kubectl -n simple-test get service simple-test -o yaml
kubectl -n simple-test get deployment simple-test \
  -o jsonpath='{.spec.template.spec.containers[*].ports}'; echo
```

Relevant observations:

| Layer | Observed configuration | Interpretation |
| --- | --- | --- |
| Ingress backend | Service `simple-test`, port `8080` | Requires a Service port that does not exist |
| Service | `name: http`, `port: 80`, `targetPort: http`, TCP | Offers 80 and resolves a named destination |
| Container | `[{"containerPort":80,"name":"http","protocol":"TCP"}]` | Named destination `http` resolves to 80 |

`http` is a port name here, not an automatic conversion to 80 or 8080. The Service's port name and its targetPort name serve different roles even when their spelling matches.

## Hypothesis and remediation decision

The new Ingress referenced port 8080 while the existing Service exposed 80. The controller event and both specifications supported this hypothesis.

Douglas considered changing the Service to 8080 and initially thought changing the Ingress backend would change application behavior. The discussion clarified that correcting the backend reference to 80 does not change NGINX's listening port or the ALB listener. Changing the existing Service port could disrupt its internal clients. The chosen correction preserved the working Service interface.

## Separate recovery blocker

The [restore workflow](https://github.com/douglas0311/eks-learning-lab/actions/runs/37482696306) failed. Subsequent events supplied in the conversation showed `FailedDeployModel` and an `AccessDeniedException` for `wafv2:GetWebACLForResource` on the load balancer controller's assumed role.

This was a second, unintended environment issue. The repository's abbreviated controller policy was replaced with the official policy matching controller v2.8.1. The workflow identity, the operator's Kubernetes permissions, and the controller's AWS role are separate permission boundaries. Diagnosing the first fault did not establish end-to-end recovery.

## Validation checklist and reusable commands

These are validation steps, not a claim that every output was retained:

```bash
kubectl -n simple-test get ingress simple-test-lab05 \
  -o jsonpath='{.spec.rules[*].http.paths[*].backend.service}'; echo
kubectl -n simple-test get service simple-test -o wide
kubectl -n simple-test get endpointslices \
  -l kubernetes.io/service-name=simple-test -o wide
kubectl -n simple-test get pods -o wide
kubectl -n simple-test describe ingress simple-test-lab05
kubectl -n kube-system get deployment aws-load-balancer-controller
kubectl -n kube-system logs \
  -l app.kubernetes.io/name=aws-load-balancer-controller \
  --all-containers=true --prefix=true --since=20m --tail=200
ALB_HOST=$(kubectl -n simple-test get ingress simple-test-lab05 \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
printf 'ALB hostname: %s\n' "$ALB_HOST"
```

If the hostname is empty, investigate reconciliation first. Otherwise, choose a current application Pod and issue a request from inside the cluster because this ALB is internal:

```bash
POD='replace-with-a-current-pod-name'
kubectl -n simple-test exec "$POD" -- \
  curl -i --connect-timeout 5 --max-time 15 "http://${ALB_HOST}/"
```

## Learning and evidence limits

This was a guided introduction to Ingress troubleshooting. Douglas connected the event to the configuration mismatch and identified the later permission denial. The key decision was to preserve the existing client interface while repairing the new reference.

The original notes contain no successful ALB HTTP response for this run. Lab 05.1 later records a successful root request on October 6; that evidence is documented in its own notes. Teardown completion is not inferred from either HTTP success or workflow preparation.

[Root cause analysis](rca.md)
