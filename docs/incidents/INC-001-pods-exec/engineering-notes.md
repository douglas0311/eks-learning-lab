# INC 001 Diagnostic exec authorization

## Context

Investigator: Douglas García Jiménez. October 1, 2026. An unexpected authorization problem interrupted the Lab 04 network investigation. This was not an intentionally injected fault.

## Evidence and reasoning

I attempted `nslookup` and `nc` through `kubectl exec` on two application Pods. Different commands and different Pods produced the same rejection for the same user. The error identified the exact denied action:

```text
User "arn:aws:iam::<account-id>:user/day7-cli-user" cannot create resource
"pods/exec" in API group "" in the namespace "simple-test"
```

The account identifier is generalized here; the denied verb, resource, user name, and namespace are retained.

My initial notes said DNS was not passing. I corrected that interpretation: the DNS command had not run. The common failure happened while requesting command execution, before network testing began.

I asked how to check the user's permissions without another user to compare. Review guidance introduced the direct authorization check:

```bash
kubectl auth can-i create pods/exec -n simple-test
# Observed: no
kubectl auth can-i get pods -n simple-test
# Observed: yes
```

These results supported the error message. Successful read access did not imply permission to execute a command inside a container. The check is for `pods/exec`, not `pods/execute`, and the verb `create` starts an exec request rather than creating a new Pod.

## Hypothesis and conclusion

The diagnostic identity lacked authorization to create `pods/exec` requests in `simple-test`. Repeating the test with another Pod helped show a common failure, but the explicit Forbidden message and authorization check were the strongest evidence.

IAM authenticates the AWS identity and controls AWS API actions. Access to Kubernetes objects is evaluated through EKS access policies and Kubernetes RBAC. A network change was not justified by this failure.

## Remediation and current status

I proposed granting the missing permission, validating it, and only then resuming DNS, TCP, and HTTP tests. The maintainer published a namespace-scoped Role and RoleBinding, a manual repair workflow, and persistent Terraform configuration in commit `5747d7e`.

The cluster was decommissioned before the retained notes recorded a successful exec test. Provision now declares the permission for future clusters. The correction is implemented, but operator validation is still pending in this record.

## Learning record

I developed the hypothesis from repeated failures and the error text. Assistance clarified the IAM/Kubernetes authorization distinction and supplied `kubectl auth can-i`. I learned to separate a broken diagnostic prerequisite from the application's incident.

[Root cause analysis](rca.md)
