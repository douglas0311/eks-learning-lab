# Lab 06 — Start and cleanup

## Close the previous session

Preserve the Lab 05.2 response and notes. Run **SRE labs (current: 06)** with scenario `lab-05.2` and operation `cleanup`, then **Terraform Decommission**. No cluster is needed overnight to prepare Lab 06. All lifecycle operations are run by Douglas.

## Start a fresh session from latest main

1. Read the [storage refreshment](../labs/lab-06/concept-refresh.md) and keep the [command guide](../labs/lab-06/command-guide.md) available.
2. Run **Terraform Provision**. This now prepares the EBS CSI add-on and its dedicated IAM role in addition to the existing cluster components. Wait for success.
3. Run **Deploy simple-test**. Its existing ECR image is reused for the small storage worker; no new image build or repository is required for the worker.
4. Run **Configure SRE observability** and wait for success.
5. Refresh local access:

   ```bash
   aws eks update-kubeconfig \
     --region us-east-1 \
     --name eks-learning-lab-lab-eks \
     --profile default
   kubectl -n simple-test get pods
   ```

6. Run **SRE labs (current: 06)** with scenario `lab-06` and operation `activate`, using `main`. Wait for green before investigation.
7. Read the [problem statement](../labs/lab-06/README.md) and begin your [engineering notes](../labs/lab-06/engineering-notes.md).

If reusing an existing cluster, clean up the prior scenario and run Terraform Provision from latest main to install the new prerequisites. Skip the initial Deploy simple-test job when the application already exists; it intentionally refuses an existing deployment.

## What activation prepares

The workflow creates one isolated worker Deployment in the existing `simple-test` namespace, a dedicated non-default StorageClass, and one encrypted 1 GiB gp3 claim. This creates a real EBS volume and incurs storage charges while it exists. The worker is separate from the existing web application and does not match its Service selector. It has no HTTP endpoint.

Before injecting the scenario, activation writes a disposable marker, replaces the worker Pod with seeding disabled, and reads the original marker from the same PV. It then introduces and checks the exercise symptom. If baseline setup fails, do not interpret the failed workflow as a successfully activated lab.

A recovery record is written before resources are created. If activation is cancelled or fails, run **cleanup** before retrying. Do not rerun activate over partially created resources.

## Workflow operations

| Operation | Behavior |
| --- | --- |
| activate | Establishes persistent storage baseline, then introduces and checks the scenario |
| check | Checks healthy workload operation and the original stored marker; does not repair |
| restore | Applies the saved correction, waits for readiness, and reads the original marker without reseeding |
| cleanup | Deletes the worker first, then its claim; verifies PV and tagged EBS volume removal before discarding recovery data |

Use **restore** after reviewing the hypothesis. The local operator has diagnostic permissions; a Forbidden response to a patch is not a reason to broaden access for the exercise.

After recovery, save relevant outputs. Run **cleanup**, then **Terraform Decommission**. Decommission also invokes Lab 06 cleanup before removing the CSI driver, IAM role, or nodes.

If cleanup fails, stop and inspect the first error. Keep the CSI controller available. Do not remove finalizers, force-delete volumes, or destroy the cluster manually. The workflow retains recovery data when it cannot verify deletion. If the cluster was already removed manually, automatic Kubernetes cleanup cannot recover its records; AWS volume inspection is a separate recovery task.

## Preparation and permission evidence

Local unit tests and workflow linting cover the preparation; they do not replace AWS acceptance testing. IAM simulation on October 7, 2026 allowed the workflow role's add-on create/read/update/delete operations and `ec2:DescribeVolumes`. The managed CSI policy ARN was confirmed to exist. Simulation is not a guarantee against every runtime policy or service condition.

Terraform validation passed without apply. No cluster provisioning, lab activation, restore, or teardown was run by the assistant. Tomorrow's workflow executions are the live acceptance tests.

[Storage implementation notes](../storage-prerequisites.md) explain prerequisite ownership without revealing the scenario.

Older per-lab workflow definitions are [archived](../../archive/workflows/README.md). The single lab workflow keeps recovery and review available through the scenario selector; Lab 06 is selected by default.
