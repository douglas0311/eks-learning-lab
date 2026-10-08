# Lab 07 — Start and recovery

## Close Lab 06

Save the marker-read evidence. Run Lab 06 `cleanup` followed by Terraform
Decommission if ending the session. Decommission also invokes storage cleanup
before removing the CSI controller. Wait for success; do not remove finalizers or
manually delete infrastructure around an unresolved cleanup failure.

## Next session

1. Read the [concept refresh](../labs/lab-07/concept-refresh.md) and keep the
   [command companion](../labs/lab-07/command-guide.md) open.
2. Start a new **Terraform Provision** run from latest `main`, leave `enable_monitoring` unchecked, and wait for success. Metrics Server remains installed.
3. Run **Deploy simple-test** and wait for success. If reusing an existing healthy
   application, skip this initial-deployment-only workflow.
4. Skip **Configure SRE observability** for this exercise. Use HPA status and resource metrics through kubectl.
5. Refresh local access:

   ```bash
   aws eks update-kubeconfig --region us-east-1 \
     --name eks-learning-lab-lab-eks --profile default
   kubectl -n simple-test get pods
   ```

6. Run **SRE labs (current: 07)**, scenario `lab-07`, operation `activate`, from
   `main`. Wait for green before treating the scenario as successfully introduced.
7. Read the [incident statement](../labs/lab-07/README.md) and investigate.

Activation verifies application readiness/HTTP and healthy HPA evaluation before
introducing one controlled workload change. It then verifies the expected symptom.
It does not create a load generator, external endpoint, or additional AWS resource.
The application HPA stays bounded at two to four replicas. Avoid stress testing
unless a separate bounded test has been agreed.

## Operations

| Operation | Behavior |
| --- | --- |
| activate | Checks healthy baseline, saves recovery information, introduces and verifies the exercise |
| check | Verifies ready application Pods, local HTTP, and usable HPA CPU evaluation; does not repair |
| restore | Restores saved workload settings and verifies HTTP plus HPA evaluation |
| cleanup | Restores workload settings and verifies readiness/HTTP before removing recovery data; skips waiting for HPA metrics during teardown |

Use restore after reviewing the hypothesis. A failed check while the fault is
active is expected. A failed activation may mean a prerequisite or admission
policy issue; do not call it a successful lab. After cancellation/failure, restore
or cleanup before activating again. Recovery information is kept on failure.

Recovery checks resource identities and refuses replaced or unexpectedly modified
workloads. Operators retain diagnostic access; do not broaden permissions merely
to bypass a Forbidden patch. Douglas runs all lifecycle operations.

After saving evidence, run cleanup and Terraform Decommission. Teardown includes
Lab 07 cleanup. No additional node autoscaler or load-test infrastructure is installed.

## Validation status

Prepared and checked locally. Live activation, restoration, and teardown remain
acceptance tests for Douglas's next session. Healthy metric evaluation alone is
not proof of successful scaling under sustained load.
