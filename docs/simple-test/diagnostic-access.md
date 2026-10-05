# Diagnostic exec access

The lab operator can read cluster resources through the existing EKS access policy.
Executing a command inside a container additionally requires `create` on `pods/exec`.
The `lab-operator-exec` Role and RoleBinding grant only that additional permission,
only in `simple-test`, to the configured lab user. Exec can change files or processes
inside a container; use it deliberately for diagnostics.

New clusters receive this binding through Terraform Provision. For the running lab
created before this addition, run **Configure SRE diagnostic access** from `main`.
The workflow applies only the two RBAC objects and checks authorization by impersonating
the named user. It does not deploy the application or activate/restore an exercise.

Then validate from your own terminal:

```bash
kubectl auth can-i create pods --subresource=exec -n simple-test
kubectl -n simple-test exec <pod-name> -- id
```

The first command should return `yes`. The second should return the container's
identity. These checks establish access, not DNS or HTTP health. Resume connectivity
tests afterwards; missing tools in an image are a separate issue.

The manual workflow does not update Terraform state. For this existing cluster,
if you run Provision again before Decommission, import these two objects into the
same remote Terraform state first (using an authorized Terraform execution context):

```bash
terraform import kubernetes_role_v1.lab_operator_exec simple-test/lab-operator-exec
terraform import kubernetes_role_binding_v1.lab_operator_exec simple-test/lab-operator-exec
```

After the usual Decommission and fresh Provision, no import is necessary: namespace
deletion removes the temporary RBAC objects, and Terraform creates and tracks them.
