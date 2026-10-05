# Lab 05 — Concept refresh

Read this before activation. Allow about 10 minutes. The purpose is to recall the architecture and vocabulary, not to identify this exercise's fault. No diagnostic commands or scenario-specific configuration values are included.

## Two different flows

**Configuration and reconciliation:** You declare an Ingress in the Kubernetes API. The AWS Load Balancer Controller observes that declaration and uses AWS APIs to reconcile the required load-balancing resources. Reconciliation means repeatedly working to bring actual state into agreement with desired state; it is not necessarily instantaneous.

**Application traffic:** A client resolves the load balancer's DNS name and sends an HTTP request to its listener. Listener rules select a target group, which forwards the request to a registered target. In this lab's IP target mode, targets are Pod IP addresses. The controller configures this path; it does not proxy each HTTP request.

```text
Configuration:
Kubernetes API: Ingress + Service + workload information
                         |
                  AWS Load Balancer Controller
                         |
                      AWS APIs
                         |
               ALB, listeners, target groups

Application request (IP target mode):
Client → ALB listener → matching rule → target group → Pod IP → application
```

The Service still defines the backend relationship in Kubernetes. With IP targets, traffic does not have to traverse the Service ClusterIP or a node's NodePort. Keep the configuration relationship separate from the actual packet path.

## Components to recognize

| Term | Meaning | Important distinction |
| --- | --- | --- |
| Pod | Kubernetes unit containing one or more containers with a shared network namespace. | Running describes Pod phase; Ready describes readiness. Neither alone proves access from a client. |
| Deployment | Controller that manages application rollout and replica state through ReplicaSets. | It manages workloads, not the AWS load balancer. |
| Service | Stable Kubernetes abstraction for reaching a set of application backends. A ClusterIP Service has a virtual cluster address. | An existing Service object does not establish successful HTTP delivery. |
| Labels and selector | Labels describe objects; a selector identifies objects matching specified label criteria. | Selection is a configuration relationship, not an HTTP health check. |
| EndpointSlice | Object describing backend addresses, ports, and conditions associated with a Service. | It is Kubernetes backend discovery data, not an ALB target group. |
| Ingress | Kubernetes declaration of HTTP/HTTPS routing to Services, commonly using host and path rules. | The object itself is neither a proxy process nor an AWS load balancer. |
| IngressClass | Identifies the controller implementation associated with an Ingress. | Multiple controller implementations can exist; an Ingress needs an appropriate controller. |
| AWS Load Balancer Controller | A Kubernetes controller that translates supported declarations into AWS load-balancing resources and maintains them. | Its health and permissions are distinct from the application's health and permissions. |
| ALB | AWS Application Load Balancer; an HTTP/HTTPS entry point. | Its existence does not prove that a target can serve the application. |
| Listener and listener rule | A listener accepts a protocol/port; rules determine how matching requests are handled. | Accepting a TCP connection is different from obtaining the expected HTTP response. |
| Target group | AWS collection of registered destinations and health-check settings used for forwarding. | Registered targets and healthy targets are different states. |
| IP versus instance targets | IP mode registers Pod IPs; instance mode typically forwards through a node's NodePort. | Interpret the traffic path according to the selected target mode. This lab uses IP mode. |

## Names, ports, and reachability

**DNS name:** Resolves to an address; it does not confirm that a listener, route, or application is healthy. The Kubernetes Service DNS name and the ALB DNS name refer to different entry points. CoreDNS handles cluster service discovery; an ALB receives an AWS DNS name.

**Search suffix:** A resolver suffix used to expand short names. A namespace search suffix is not itself the full DNS name of each Service.

**Ports:** A listener port accepts client traffic; a Service port is the Service-facing interface; a Service targetPort identifies the application destination and may be numeric or named; containerPort documents a container port but does not start a listening process. These fields have different roles and are not required to use the same number throughout an architecture.

**Internal versus internet-facing:** An internal ALB uses private addresses and requires a client with suitable VPC connectivity. Internet-facing describes the load balancer's exposure, not necessarily whether its targets use public addresses. The lab uses internal access.

**VPC, subnet, Availability Zone:** The VPC is the AWS network boundary; subnets are address ranges within one Availability Zone. ALB placement depends on suitable subnets in multiple zones. Subnet discovery tags help the controller identify eligible subnets.

**Security group:** Stateful AWS traffic rules applied to network interfaces/resources. Network access controls are separate from permission to call an AWS API.

## Configuration and permissions

| Term | What to remember |
| --- | --- |
| Annotations | Key/value metadata interpreted by a controller for implementation-specific settings. They are different from Pod-selection labels. |
| IAM / IRSA | AWS authorization and a mechanism for assigning an IAM role to a Kubernetes service account. The controller needs its own AWS permissions to manage resources. |
| Kubernetes RBAC | Authorization for Kubernetes API operations. An operator's read or exec access does not grant AWS resource-management access. |
| Desired versus observed state | The declaration states intent; status and controller observations describe progress. Acceptance by the API does not mean reconciliation completed. |
| Finalizer | A deletion coordination mechanism: the object remains pending deletion until required controller cleanup completes. It is especially relevant to external AWS resources. |

## Signals and their limits

| Signal | What it can tell you | What it does not establish by itself |
| --- | --- | --- |
| Pod Ready | Kubernetes readiness criteria are satisfied. | That the complete client request path works. |
| Controller logs / Events | Reconciliation actions, errors, and resource context. | That every message is relevant to this incident; correlate object identity and time. |
| Ingress status address | An address has been published for the Ingress. | That targets are healthy or the expected response is served. |
| ALB target health | Result of the configured load-balancer health checks. | That every URL, host rule, or user transaction works. |
| DNS response | Result for the exact queried name. | TCP connectivity or HTTP success. |
| Successful TCP connection | A connection was established to that destination and port. | The correct application content. |
| HTTP status and body | Outcome of that particular request, from that source, at that time. | Every replica, route, or client path was exercised. |
| Infrastructure dashboard | Resource usage and whichever conditions its queries measure. | End-to-end application availability unless explicitly measured. |

A readiness probe, a liveness probe, and an ALB health check serve different purposes. Readiness influences eligibility for normal Service traffic; liveness can trigger container restarts; the ALB independently evaluates its registered targets using its configured check.

## Self-check before opening the incident

Try explaining these in your own words. They are vocabulary questions, not clues to the scenario:

1. Which component declares routing intent, which reconciles it, and which forwards the request?
2. How is an EndpointSlice different from an ALB target group?
3. Why can an application respond to localhost while a client request still fails?
4. What does an internal ALB require of the client's network location?
5. How do controller AWS permissions differ from your kubectl permissions?
6. Why should controller-managed resources be cleaned up before removing the controller?

You do not need to memorize every command. Use this reference to recall the components, then let the evidence determine your investigation.

## References

- [AWS Load Balancer Controller v2.8: how it works](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/how-it-works/)
- [AWS Load Balancer Controller v2.8: Ingress annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/)
- [Kubernetes Service concepts](https://kubernetes.io/docs/concepts/services-networking/service/)

[Start guide](../../simple-test/lab-05-start.md) · [Problem statement](README.md)
