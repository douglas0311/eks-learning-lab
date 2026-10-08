# Lab 03 Observability and activation

> Workflow navigation update: use **SRE labs (current: 07)** and select the scenario named in this guide. The old per-lab workflow names below are historical; see the [archive and operation mapping](../../archive/workflows/README.md).


This controlled exercise concerns node scheduling. It does not simulate a real kubelet outage or physical memory pressure. Investigate Kubernetes state and metrics before opening the scenario code.

Provision installs the monitoring stack. **Configure SRE observability** adds and verifies this lab's dashboard and alert rules; it does not install a second Prometheus or Grafana.

## Start the session

1. Run **Terraform Provision** on `main` and wait for success.
2. Run **Deploy simple-test** when the application does not exist. If a cancelled run already created it, inspect state and use the appropriate recovery procedure.
3. Run **Configure SRE observability**. It verifies live metric series, six loaded alert rules, and nine dashboard panels.
4. Open Grafana, observe healthy behavior, and save a timestamped screenshot.
5. Run **Run SRE lab 03 → operation: activate** on `main`. Lab 03 is not an option in Update simple-test.
6. A green activation means the scenario and expected symptom were verified. If activation fails, retain the run URL rather than assuming it completed.

## Recovery options

| Workflow option | Purpose |
| --- | --- |
| Update simple-test / baseline | Recover labs 01–02 |
| Run SRE lab 03 / restore | Recover the exercise-owned node change and saved application template |
| Terraform Decommission | Remove the managed environment, even with an active exercise |

Use restore for this exercise. Recovery retains its checkpoint until rollout and HTTP checks pass. If interrupted, retry restore. If no checkpoint exists, the workflow stops rather than guessing. Restore an active exercise before starting another one.

The scenario uses the existing Terraform administrative role. The diagnostic operator does not receive node modification permission. Monitoring port-forward access is declared separately from application exec access.

## Grafana and Prometheus access

Refresh kubeconfig after each Provision:

```bash
aws eks update-kubeconfig --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default
kubectl -n monitoring port-forward service/kube-prometheus-stack-grafana 3000:80
```

Keep the tunnel open and visit `http://localhost:3000`. Retrieve credentials locally without copying them into reports or screenshots:

```bash
kubectl -n monitoring get secret kube-prometheus-stack-grafana \
  -o jsonpath='{.data.admin-user}' | base64 --decode
kubectl -n monitoring get secret kube-prometheus-stack-grafana \
  -o jsonpath='{.data.admin-password}' | base64 --decode
```

Open **SRE Lab — simple-test and nodes**, choose the stack's Prometheus datasource, and use the last hour with a 30-second refresh. Record the selected time range and timezone with screenshots.

For Prometheus, open another terminal:

```bash
kubectl -n monitoring port-forward service/kube-prometheus-stack-prometheus 9090:9090
```

Visit `http://localhost:9090` and inspect Alerts. Rules require a sustained condition for their configured duration in addition to evaluation timing. No external email or Slack notification is configured.

## Reading the dashboard

The panels cover desired, available, and updated replicas; Pod phases; restarts; CPU and memory usage, requests, and limits; node Ready; scheduling-disabled status; node pressure; and allocatable CPU. A never-started container can lack usage metrics while its requests and Pod state are visible.

Match each metric to a question. Low CPU use does not establish sufficient schedulable capacity. Ready and SchedulingDisabled are different properties. A memory limit line is not measured memory usage. Pod phase is not an HTTP transaction status.

The dashboard does not continuously measure application HTTP, request latency, or centralized application logs. Use client tests and `kubectl logs` for those questions. The deployment workflow's tunnel checks do not cover the complete normal Service path.

## Close the session

Save screenshots, queries, and timestamps before Decommission. Prometheus and Grafana storage is ephemeral in this lab, so the history disappears with teardown. Re-run Configure SRE observability after the next Provision and deployment. Restore is not required before full Decommission.

This exercise and monitoring configuration have been used in EKS. See the [engineering notes](../labs/lab-03/engineering-notes.md) and [RCA](../labs/lab-03/rca.md) for the completed investigation; they disclose the cause.
