# Application deployment playbook

Build and run the `simple-test` NGINX application on EKS through GitHub Actions. Work through the stages deliberately; local preparation does not create AWS resources. The repository's public name and AWS resource names are separate: the configured cluster remains `eks-learning-lab-lab-eks` in `us-east-1`.

## Files and ownership

| Path | Purpose |
| --- | --- |
| `application/simple-test/` | HTML, NGINX configuration, Dockerfile |
| `kubernetes/simple-test/` | Workload manifests and access definitions |
| `simple-test-access.tf` | Terraform-managed namespace, EKS entry, deployer RBAC |
| `operator-exec-access.tf` | Operator exec permission for diagnostics |
| `iam/simple-test-deploy-policy.json` | AWS permissions for image publishing and EKS discovery |
| `.github/workflows/deploy-simple-test.yml` | Initial build, test, publish, and deployment |
| `.github/workflows/update-simple-test.yml` | Controlled updates and baseline recovery for labs 01–02 |

Run commands from your repository checkout. Check identity and cluster status before deployment:

```bash
aws sts get-caller-identity --profile default
aws eks describe-cluster --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default \
  --query 'cluster.{Name:name,Status:status,Version:version}'
```

## One-time ECR preparation

```bash
aws ecr describe-repositories --repository-names simple-test \
  --region us-east-1 --profile default
```

Only `RepositoryNotFoundException` establishes that the repository is missing. Resolve authorization or authentication failures before proceeding. If it is absent and this is the intended account:

```bash
aws ecr create-repository --repository-name simple-test \
  --image-tag-mutability IMMUTABLE \
  --encryption-configuration encryptionType=AES256 \
  --region us-east-1 --profile default
```

ECR and the deployment IAM role were prepared in earlier sessions and persist across cluster teardown. These creation commands are reference steps for a new environment. Image tags include the commit, workflow run, and attempt; the workload uses an image digest. ECR storage can incur charges after EKS is destroyed, and this initial design does not configure image expiry.

## One-time deployment role preparation

Inspect `iam/simple-test-trust.json` before using it. Its customized OIDC subject must match the current repository identity and `main` branch; a repository rename requires a coordinated trust-policy update. Do not substitute a generic subject example.

```bash
aws iam create-role --role-name GitHubActionsSimpleTestRole \
  --assume-role-policy-document file://iam/simple-test-trust.json \
  --description "GitHub Actions role for simple-test deployment" \
  --profile default
aws iam put-role-policy --role-name GitHubActionsSimpleTestRole \
  --policy-name SimpleTestDeployment \
  --policy-document file://iam/simple-test-deploy-policy.json \
  --profile default
```

Inspect an existing role instead of recreating it. The role can publish to the designated ECR repository and describe this cluster; it does not create ECR, EKS, or IAM roles. `--profile default` selects local credentials. The workflow authenticates with OIDC.

The existing Provision role also needs its bootstrap policy. This was applied during initial setup:

```bash
aws iam put-role-policy --role-name TerraformSRELabGitHubActionsRole \
  --policy-name TerraformSimpleTestAccess \
  --policy-document file://iam/simple-test-bootstrap-policy.json \
  --profile default
```

## Cluster preparation

Terraform Provision creates the app deployer's EKS access entry, `simple-test` namespace, Role, and RoleBinding. It reads the deployer rules from `kubernetes/simple-test/rbac.yaml`. Terraform also declares the operator's separate exec access. The application Deployment, Service, and HPA are managed by the application workflow.

Run Provision and inspect its plan and result before deploying. Do not manually recreate Terraform-managed resources. A repair applied outside Terraform may require import before another Provision; see [diagnostic access](diagnostic-access.md).

```bash
aws eks update-kubeconfig --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default
kubectl get namespace simple-test
kubectl -n simple-test get role,rolebinding
kubectl auth can-i create pods/exec -n simple-test
```

Metrics Server must function for CPU-based HPA calculations. Successful AWS authentication alone does not establish Kubernetes authorization.

## Optional local container check

With Docker running:

```bash
docker build --platform linux/amd64 -t simple-test:local application/simple-test
docker run --rm -d --name simple-test-local \
  --read-only --tmpfs /tmp:rw,size=33554432,mode=1777 \
  --cap-drop ALL --security-opt no-new-privileges \
  --sysctl net.ipv4.ip_unprivileged_port_start=0 \
  --memory 64m --cpus 0.1 \
  -p 127.0.0.1:8080:80 simple-test:local
curl --fail http://localhost:8080/healthz
curl --fail http://localhost:8080/
docker stop simple-test-local
```

An ARM Mac needs emulation for this AMD64 image. NGINX listens on port 80; port 8080 belongs to the local host.

## Review and publish changes

```bash
git status --short
git diff --cached --name-only
```

Stage only reviewed files with explicit paths, inspect `git diff --cached`, then commit and push. A commit includes all staged files. Avoid `git add .` in a checkout containing unrelated experiments. A manual workflow must exist on the default branch to appear in Actions; the configured OIDC trust authorizes `main`.

## Initial deployment

Choose **Actions → Deploy simple-test → Run workflow → main**. The workflow checks the account, cluster, immutable ECR repository, Kubernetes permissions, and metrics API. It builds and tests the image, publishes it, validates manifests against the API, applies them, waits for rollout and HPA activation, and tests HTTP through port-forward.

The initial workflow stops if the Deployment already exists. After a cancelled run, inspect what was created before choosing a recovery path. The separate Update workflow handles an existing application; baseline only restores the fields owned by labs 01–02. Use the matching restore workflow for an active lab 03 or 04.

Resources and published images are retained after a failure for diagnosis; there is no automatic rollback. The shared workflow concurrency group serializes these jobs with Terraform lifecycle jobs, but does not lock out independent manual commands.

## Validation and access

```bash
kubectl -n simple-test get deployment,pods,service,hpa
kubectl -n simple-test top pods
kubectl -n simple-test describe hpa simple-test
```

An authorized identity can open a tunnel:

```bash
kubectl auth can-i create pods/portforward -n simple-test
kubectl -n simple-test port-forward service/simple-test 8080:80
```

Use `http://localhost:8080` while the tunnel is open. The operator's exec permission does not itself grant app port-forward permission. The workflow's tunnel tests one selected Pod and does not validate the complete normal ClusterIP traffic path.

For an internal test, the operator can execute tools already present in an application Pod after verifying exec access. A dedicated temporary client needs separate permission to create Pods and an approved image it can pull; do not assume those permissions were granted with exec. Use the lab 04 `check` operation when appropriate. It creates and removes its own client with the workflow identity.

A healthy HPA may remain at two replicas under low load. Four is the configured maximum, not the expected constant count.

## Troubleshooting and teardown

```bash
kubectl -n simple-test get events --sort-by=.lastTimestamp
kubectl -n simple-test describe deployment simple-test
kubectl -n simple-test logs deployment/simple-test --tail=100
kubectl -n simple-test describe hpa simple-test
```

Investigate image references and node ECR access for ImagePullBackOff, scheduler events for Pending, Metrics Server and requests for missing HPA metrics, and identity plus Kubernetes authorization for Forbidden.

An administrator can remove only the workload with `kubectl delete -k kubernetes/simple-test`; the current kustomization contains the Deployment, Service, and HPA. It leaves Terraform's namespace and RBAC. The diagnostic operator is not granted workload deletion.

For full teardown, use Terraform Decommission and confirm success. It removes the managed infrastructure and app namespace. The manually prepared ECR repository, IAM roles, and persistent S3 state backend are separate lifecycle concerns. Retain evidence before destroying ephemeral monitoring data.

## Review questions

1. Does permission to publish an ECR image imply permission to create a Deployment?
2. Which port belongs to NGINX and which belongs to the Mac tunnel?
3. What does a successful tunnel check prove, and what does it leave untested?
