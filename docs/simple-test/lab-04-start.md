# Lab 04 Internal connectivity activation

Investigate access to simple-test from inside the cluster using Kubernetes state, observability, and client tests. The exercise creates no application Ingress, external load balancer, or public DNS. Its root cause is left for the investigator.

## Start from a healthy environment

Run each workflow from `main` and wait for its result:

1. **Terraform Provision** creates the cluster and diagnostic permissions.
2. **Deploy simple-test** installs the application. If it already exists, inspect the previous run and recover appropriately rather than repeating initial installation blindly.
3. **Configure SRE observability** loads and verifies the dashboard and rules.
4. Refresh kubeconfig, record the healthy dashboard, and validate diagnostic access:

```bash
aws eks update-kubeconfig --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default
kubectl auth can-i create pods --subresource=exec -n simple-test
kubectl -n simple-test get pods
# Use a current Pod name for this access check.
kubectl -n simple-test exec <pod-name> -- id
```

If exec is denied, follow [diagnostic access](diagnostic-access.md). Do not call that a DNS failure: the network command has not run.

5. Run **Run SRE lab 04 → operation: activate**. It is separate from Update simple-test and Run SRE lab 03.
6. Green means initial connectivity and the subsequent incident symptom were verified. It does not mean the application is accessible normally.
7. Begin with the [problem statement](../labs/lab-04/README.md).

## Workflow operations

| Operation | Purpose | Meaning of success |
| --- | --- | --- |
| activate | Start once from the healthy environment | Scenario change and symptom verified |
| check | Test internal access during investigation | Internal DNS and HTTP test passed |
| restore | Recover after preserving evidence | Saved configuration, rollout, and internal HTTP verified |

`check` does not patch the application, but creates and removes a temporary client Pod. The client uses the existing application image and distinct labels. A client scheduling, image-pull, or authorization failure does not independently establish an application HTTP failure.

Use this workflow's restore operation, not baseline. The latter recovers labs 01–02. Active-exercise guards prevent mixing scenarios.

## Evidence and monitoring

```bash
kubectl -n monitoring port-forward service/kube-prometheus-stack-grafana 3000:80
```

Visit `http://localhost:3000/d/sre-simple-test`. Credentials and metric context are in the [observability guide](lab-03-start.md). Use a time range covering before and after activation. Not every failure changes every panel, and this dashboard is not a continuous HTTP availability check.

Record the client, target, timestamp, command, exit status, output, and interpretation. Establish a hypothesis before changing configuration. Avoid reading `lab04.py` during the investigation.

## Interrupted runs and teardown

The workflow saves recovery information before changing the scenario. If activation or recovery is cancelled, preserve the run URL and use restore rather than activating again over an existing record. Recovery keeps the record until checks pass. Missing recovery data or replaced resource identities cause it to stop rather than modifying unrelated resources.

Temporary clients have execution deadlines. Subsequent operations clean up exercise-owned leftover clients. The workflow does not delete application Pods or change nodes for this exercise.

Save evidence before Terraform Decommission; monitoring history is ephemeral. Full teardown does not require restoring first. A prior activation succeeded after a validation-script fix; the selector mismatch and HTTP recovery are documented in the Lab 04 RCA. The separate unexpected exec-permission incident is documented in [INC-001](../incidents/INC-001-pods-exec/rca.md).
