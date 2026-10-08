# Historical SRE workflow definitions

These YAML files are preserved outside `.github/workflows` as historical references. GitHub does not execute workflow definitions from this folder. Their old copies remain in Git history; past Actions runs are not deleted.

## Current entry point

Use **SRE labs (current: 07)** in Actions, on `main`. The default scenario is `lab-07`. Select an older scenario in the same form for recovery or review; there is no need to copy archived YAML back into the active workflow directory.

| Scenario | Available operations |
| --- | --- |
| lab-07 | activate, restore, check, cleanup |
| lab-06 | activate, restore, check, cleanup |
| lab-05 / lab-05.1 / lab-05.2 | activate, restore, check, cleanup |
| lab-04 | activate, restore, check |
| lab-03 | activate, restore |

Unsupported combinations fail validation before AWS authentication. Dispatch uses fixed script paths, preserves the Lab 05 variant, and shares the existing concurrency group with Terraform. It does not run labs automatically.

Earlier playbooks and incident records may use the old workflow names. Their current equivalent is this single workflow with the matching scenario and operation. Historical records are not rewritten to imply that this menu existed at the time.

Provision, application deployment, observability, S3 operations, and Decommission remain separate workflows. Decommission's direct cleanup calls and the underlying recovery scripts remain available.

GitHub may still display historical workflow runs; this archive does not erase run history. Active definitions are kept only in `.github/workflows`. GitHub does not support workflow subdirectories as an Actions folder hierarchy: [official documentation](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#creating-a-reusable-workflow).
