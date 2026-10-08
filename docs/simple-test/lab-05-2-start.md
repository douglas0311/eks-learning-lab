# Lab 05.2 — Start, investigate, and clean up

> Workflow navigation update: use **SRE labs (current: 07)** and select the scenario named in this guide. The old per-lab workflow names below are historical; see the [archive and operation mapping](../../archive/workflows/README.md).


## Preparation for tomorrow

Read the [refreshment](../labs/lab-05-2/concept-refresh.md). It includes lessons from Labs 05 and 05.1 and the evidence habits to apply. The [problem statement](../labs/lab-05-2/README.md) defines the request to reproduce without revealing the cause.

All operations below are run by Douglas. Preparing these files does not activate a lab or schedule an overnight job.

## Finish an existing session

If a Lab 05/05.1 Ingress or recovery record remains, run **Run SRE lab 05.1 → cleanup** and wait for success. Then run **Terraform Decommission** when ending today's environment. Decommission includes the same Ingress cleanup guard, so it can also handle a retained Lab 05 family record before destroying the cluster.

Do not remove finalizers to force deletion. Cleanup must finish while the controller is available. No need to keep the cluster overnight for this preparation.

## Start a fresh environment

Use the latest `main` for every workflow:

1. **Terraform Provision** — wait for success.
2. **Deploy simple-test** — wait for success; this initial-deployment job does not update an existing application.
3. **Configure SRE observability** — wait for success.
4. Refresh your local kubeconfig:

   ```bash
   aws eks update-kubeconfig \
     --region us-east-1 \
     --name eks-learning-lab-lab-eks \
     --profile default
   kubectl -n simple-test get pods
   ```

5. **Run SRE lab 05.2 → activate** — wait for green.
6. Begin the investigation using the request contract in the problem statement.

If reusing a healthy existing environment, skip provisioning and the initial application deployment. Clean up the previous Lab 05 family scenario before activating 05.2. A cancelled or failed activation retains recovery data; use cleanup before retrying activation.

Activation verifies internal application HTTP and a successful page response through the ALB before changing the scenario. It then checks the intended symptom and rechecks internal application HTTP. If a check fails, save the run URL; a red workflow is not confirmation that the exercise is ready. ALB creation and reconciliation can take several minutes.

## Obtain the current request target

```bash
ALB_HOST=$(kubectl -n simple-test get ingress simple-test-lab05 \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
printf 'ALB hostname: %s\n' "$ALB_HOST"
kubectl -n simple-test get pods
POD='replace-with-a-current-pod-name'
```

Do not use a hostname or Pod name from yesterday. If the hostname is empty, inspect the activation result before testing an empty URL. From the selected Pod:

```bash
kubectl -n simple-test exec "$POD" -- \
  curl -i --connect-timeout 5 --max-time 15 "http://${ALB_HOST}/"
```

Keep the full response and command in the [engineering notes](../labs/lab-05-2/engineering-notes.md).

## Recovery and closure

- **check:** validates healthy internal and ALB application HTTP; failure is expected while the fault persists. It does not inject or repair the fault.
- **restore:** applies the saved scenario's correction and validates application HTTP. Use after collecting evidence and reviewing the hypothesis.
- **cleanup:** deletes only the owned exercise Ingress, waits for controller finalizers, and removes the recovery record. It does not destroy the cluster.
- **Terraform Decommission:** destroys the infrastructure after the cleanup guard succeeds.

All Lab 05 variants share the same Ingress and recovery record; only one can be active. Restore uses the saved variant even if selected through another Lab 05 family workflow. The existing Decommission cleanup supports this iteration.

The preparation was checked offline. Tomorrow's activation, recovery, and cleanup are the live acceptance tests; no successful AWS run is claimed in advance.
