# EKS egress playbook

This design guide explains IPv4 outbound Internet access for workloads in private subnets and how to validate that path. It is a future lab guide, not a report that these checks have been executed against the current environment. Inspect the existing network before creating additional resources.

## Outbound and inbound traffic

Egress is a connection initiated by the workload, such as an HTTPS request to an API. Ingress is a connection initiated by a client toward the application. A public NAT gateway supports outbound connections and their responses; it does not expose simple-test to incoming connections from a Mac.

Local port-forward is an authenticated tunnel. Public application access would require a separate ingress design. NGINX's listening port 80 is distinct from the destination port 443 typically used for outbound HTTPS.

## Required components

| Component | Role |
| --- | --- |
| Pod networking and Amazon VPC CNI | Connect the workload to the VPC |
| Cluster DNS | Resolve destination names |
| Private subnet route table | Route outbound IPv4 traffic toward NAT |
| Public NAT gateway and Elastic IP | Translate outbound private traffic |
| Public subnet route table | Route NAT traffic toward the Internet gateway |
| Internet gateway | Connect the VPC to the Internet |
| Security groups and network ACLs | Apply AWS network controls |
| NetworkPolicy-capable CNI | Enforce selected Pod-level network rules when enabled |

Reference path: Pod → node/CNI networking → private route → public NAT gateway → public route → Internet gateway → HTTPS destination. Additional source translation on the node depends on CNI configuration.

## Inspect the existing environment

Review Terraform's networking module and the VPC resource map. Do not create another NAT gateway simply because it appears in this guide.

```bash
aws sts get-caller-identity --profile default
aws eks describe-cluster --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default \
  --query 'cluster.resourcesVpcConfig'
kubectl get nodes -o wide
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n simple-test get networkpolicy
```

Record node subnet IDs, effective route tables, NAT IDs, and Elastic IPs. Control-plane subnet configuration alone does not prove where worker nodes run. When a subnet lacks an explicit route-table association, inspect the VPC main route table.

## Terraform design review

An authorized infrastructure operator should review the following before applying any network change:

1. The VPC has an Internet gateway attached.
2. The public subnet has a `0.0.0.0/0` route to that gateway.
3. A public NAT gateway has an Elastic IP and reaches Available state in the public subnet.
4. The private worker subnets have effective `0.0.0.0/0` routes to the intended NAT gateway.
5. Effective node and, where configured, Pod security groups allow the destination traffic.
6. Network ACLs allow both directions, including return ports. They are stateless; security groups are stateful.
7. The Terraform plan does not unexpectedly replace the VPC or EKS cluster.

A shared NAT can reduce lab resources but introduces an availability-zone dependency and possible cross-zone traffic. A resilient design may use NAT per zone and local routing. NAT processing, gateway time, and public IPv4 addresses can incur charges. IPv6 requires a different design. See [AWS private subnet and NAT architecture](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-example-private-subnets-nat.html).

## Separate authorization DNS and HTTPS tests

First establish permission to run the diagnostic command:

```bash
kubectl auth can-i create pods/exec -n simple-test
```

The operator now has namespace-scoped exec declared in Terraform. Creating a new client Pod requires a different permission; use an authorized operator or a dedicated workflow for that step. Select an approved image pinned by digest, and compare the client's network policies, subnets, and security groups with the workload under investigation. Do not label the client `app=simple-test`, because the application's Service uses that label.

```bash
# Replace <test-pod> with the current authorized diagnostic Pod.
kubectl -n simple-test exec <test-pod> -- nslookup example.com
kubectl -n simple-test exec <test-pod> -- \
  curl -I --connect-timeout 5 --max-time 15 https://example.com
```

DNS needs a valid response; curl needs a TLS connection and an HTTP response. An HTTP 403 shows an HTTP responder was reached, but may come from a proxy or intermediary and does not establish application authorization. A timeout alone does not identify the blocking component. Missing diagnostic tools and Forbidden errors are not network test results.

An ImagePullBackOff prevents the test container from running; investigate node image access and events first. Successful image pulling and successful workload egress are different checks. ICMP alone is not a substitute for an HTTPS test.

## Add restrictions only after baseline validation

Verify that the CNI actually enforces NetworkPolicy before relying on it. Design a policy for the test workload that permits DNS to the actual resolver and permits required destinations. Inspect CoreDNS labels and any NodeLocal DNS configuration first.

Standard NetworkPolicy operates on selectors, IPs, and ports rather than domain-name allowlists. Allowing TCP 443 everywhere does not restrict traffic to one API. Policies are additive, so another policy can permit traffic. Domain-based controls may require a proxy or firewall. See [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

Compare one permitted and one denied destination before and after the change. Record manifests, timestamps, commands, and outputs. Keep evidence before removing a test restriction.

## Diagnostic evidence

| Symptom | Next area to inspect |
| --- | --- |
| Exec Forbidden | Kubernetes authorization; command did not execute |
| DNS failure | Resolver configuration, DNS health, UDP/TCP 53 reachability |
| DNS succeeds but HTTPS times out | Effective routes, NAT, security groups, ACLs, Pod policies |
| TLS failure | Destination name, certificates, clock, intermediary |
| HTTP 401 or 403 | Responder identity and application authorization |
| One node or zone differs | Node subnet and effective network path |
| Image cannot be pulled | Pod events, node ECR permissions, image reference, node connectivity |

VPC Flow Logs, if enabled, can add ACCEPT/REJECT evidence. ACCEPT does not establish application success. Record scope and a testable hypothesis before selecting a fix.

## Recovery and closure

Remove only the temporary client and exercise-owned policies. Keep lasting network changes in Terraform. Run Decommission at session end and verify remaining resources, especially NAT and Elastic IPs. Preserve the intentionally persistent state backend.

Success requires recorded DNS and HTTPS results from a representative client, documented routing, and evidence of the intended allowed/denied behavior if restrictions were added.

## Future public access

For inbound access, a future design could use AWS Load Balancer Controller and an ALB Ingress, or an NLB-backed Service. Review controller IAM, subnet discovery, security groups, listeners, health checks, and target configuration. HTTPS adds certificates and usually DNS. An ALB endpoint is an AWS-managed DNS name rather than a fixed IP to bookmark. This is a separate exercise from egress.

## Review questions

Why does NAT not expose ClusterIP to a Mac? What does a successful DNS lookup leave untested? How could an unrepresentative client produce misleading results? What evidence demonstrates actual NetworkPolicy enforcement?
