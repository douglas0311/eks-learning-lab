# Optional monitoring for lab sessions

Terraform Provision has an `enable_monitoring` checkbox, unchecked by default.
Choose the stack according to the evidence needed by the exercise.

| Configuration | Installed components |
| --- | --- |
| Unchecked | Metrics Server, AWS Load Balancer Controller, EBS CSI, and core cluster networking remain available |
| Checked | Also installs Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics, Kubecost and its supporting namespaces/IAM |

For Lab 07, leave it unchecked and skip **Configure SRE observability**. HPA resource
metrics are provided by Metrics Server. Use Kubernetes HPA conditions, events,
resource measurements and workload configuration for this first investigation.

For sessions needing historical before/after graphs, check it during Provision,
then run **Configure SRE observability** to install the lab dashboards and alerts.
Older lab guides that reference Grafana assume this option is enabled. The dashboard
workflow does not install the underlying monitoring stack.

## Existing environments and teardown

Changing the checkbox from checked to unchecked and applying Terraform removes the
optional stack and its monitoring data according to its storage configuration.
Save evidence first. This setting is not just a request to skip dashboard setup.
No live change occurs until Douglas runs Provision. Start a new run on current
`main`; re-running an old workflow uses the old commit.

Terraform moved blocks preserve existing resource addresses when the stack remains
enabled. Decommission destroys tracked infrastructure regardless of whether the
optional stack was enabled. The variable defaults to false for local Terraform
commands; pass `-var='enable_monitoring=true'` when maintaining an enabled session.

The node count remains three. Disabling monitoring frees pod slots and resources;
it does not by itself reduce the number of billable EC2 instances. Node capacity
can be reviewed separately with measured workload needs.

Offline mocked Terraform plans cover enabled and disabled module configurations.
They do not establish successful live chart installation or removal.
