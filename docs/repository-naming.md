# Repository naming and migration

The selected portfolio name is **aws-cloud-engineering-lab**. It reflects infrastructure automation, Kubernetes operations, observability, and future AWS application work.

Repository identity and infrastructure identity are separate. Renaming the GitHub repository must not change Terraform's `project_name`, backend bucket or state key, existing EKS cluster name, ECR repository, or resource tags. A global search-and-replace could cause unwanted infrastructure changes.

## Migration requirements

The current GitHub OIDC subject includes the repository name, owner ID, repository ID, and main branch. Three IAM roles trust that subject: TerraformSRELabGitHubActionsRole, GitHubActionsSimpleTestRole, and GitHubActionsS3LabRole.

Wait until lifecycle and application runs are complete before the rename. Back up and inspect the live trust documents, update only the exact intended repository subjects while preserving audience and branch restrictions, rename the repository, and update the local remote and documentation links. Update committed trust configuration as well as live IAM; do not rely on GitHub redirects to make an old OIDC subject valid.

Verify repository ID, default branch, remote URL, and live trust conditions afterwards. A static trust review is not proof of a successful subsequent OIDC exchange; the next user-run workflow provides that evidence. Retain a recovery path if the rename or any trust update fails.

The name change is intentionally separate from running infrastructure operations. See [GitHub repository rename guidance](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository).
