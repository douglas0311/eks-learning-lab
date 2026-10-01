# Lab 02 Activation guide

This guide starts the exercise without revealing its cause. Provision and initial deployment establish the healthy environment; **Update simple-test → lab-02** activates the scenario.

## Workflow sequence

1. Run **Terraform Provision** on `main` and wait for success.
2. Run **Deploy simple-test** on `main` when the app is absent. Use a new Run workflow, not a rerun of an older revision.
3. Refresh local access and record the healthy state:

```bash
aws sts get-caller-identity --profile default
aws eks update-kubeconfig --region us-east-1 \
  --name eks-learning-lab-lab-eks --profile default
kubectl -n simple-test get deployment,pods,service,hpa
```

4. Open **Update simple-test → Run workflow → main → configuration: lab-02**.
5. Confirm the configuration patch step succeeds. The later rollout check may time out as part of the exercise. An authentication, authorization, or patch failure is not successful scenario activation.
6. Record the run URL and investigate current state before concluding impact. Request the problem statement without the solution if working with a reviewer.

## Investigation

Record timestamps, scope, evidence, hypotheses, and a proposed recovery check. Do not assume the previous exercise's cause applies here. Avoid reading the scenario patch or completed RCA before investigating.

## Recovery

After preserving evidence, run **Update simple-test → baseline**. This is a workflow option, not a Kubernetes command. It restores the startup arguments and resource settings owned by labs 01–02 while preserving the image; it is not a universal rollback.

Wait for rollout and HTTP checks to pass and inspect replicas. Restore a healthy starting point before repeating the exercise. Use the dedicated restore workflow for lab 03 or 04 if either is active.

## Teardown and evidence status

Terraform Decommission can close the environment even when the app is failing. Confirm the result; failure may leave resources. ECR and the persistent S3 backend survive the cluster lifecycle.

This exercise was investigated in EKS. The [engineering notes](../labs/lab-02/engineering-notes.md) and [RCA](../labs/lab-02/rca.md) record the evidence and recovery limits; both contain the solution.
