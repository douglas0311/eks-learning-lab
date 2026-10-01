# INC 001 Root cause analysis

**Status:** authorization cause confirmed; correction published; post-fix operator validation pending in the source notes.

## Summary and impact

The lab operator could inspect Pods but could not execute commands inside them. This blocked in-container DNS and TCP diagnostics during Lab 04. It did not demonstrate that application traffic was failing because of permissions.

## Cause

The diagnostic access configuration omitted `create` on the core API subresource `pods/exec` in `simple-test`. Kubernetes returned Forbidden, and `kubectl auth can-i` returned `no` for exec while returning `yes` for reading Pods. The commands therefore never ran in the containers.

## Correction

Commit `5747d7e` adds a Role scoped to `simple-test` and a RoleBinding for the lab operator. It does not grant cluster administration. Terraform prepares the permission for new clusters; the manual access workflow repairs an existing cluster without deploying the application.

Exec can modify processes or files inside a container, so it is a deliberate diagnostic capability rather than read-only access.

## Verification required to close

1. Confirm `kubectl auth can-i create pods/exec -n simple-test` returns `yes` using the operator's own credentials.
2. Execute `id` inside a current application Pod.
3. Resume DNS, TCP, and HTTP tests and record their actual outputs.
4. Keep application connectivity findings in Lab 04, separate from this access incident.

Terraform and workflow syntax were validated when the correction was prepared. Those checks do not replace live authorization and exec validation.

## Prevention

The automation maintainer added persistent RBAC to the provisioning configuration. The operator should verify diagnostic capabilities before future fault activation. The next investigation should record both permitted and denied operations without interpreting a Forbidden response as a DNS or network result.

[Investigation evidence](engineering-notes.md) · [Access playbook](../../simple-test/diagnostic-access.md)
