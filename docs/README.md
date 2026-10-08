# Engineering documentation

This portfolio records hands-on AWS and Kubernetes work by Douglas García Jiménez. Investigation notes preserve the reasoning, including hypotheses that changed after new evidence. Root cause analyses distinguish confirmed causes from proposed remediation and verified recovery.

## Start here

- [Application deployment playbook](simple-test/playbook.md)
- [How Kubernetes runs the application](simple-test/kubernetes-explained.md)
- [Observability and local access](simple-test/lab-03-start.md)
- [Diagnostic permissions](simple-test/diagnostic-access.md)
- [EKS egress design playbook](networking/egress-playbook.md)
- [Progressive SRE curriculum](curriculum.md)

## Investigation portfolio

| Case | Engineering notes | Root cause analysis | Evidence status |
| --- | --- | --- | --- |
| Lab 01 — Container startup | [Notes](labs/lab-01/engineering-notes.md) | [RCA](labs/lab-01/rca.md) | Cause supported; recovery not recorded in the retained notes |
| Lab 02 — CPU scheduling | [Notes](labs/lab-02/engineering-notes.md) | [RCA](labs/lab-02/rca.md) | Cause supported; two healthy application Pods recorded after recovery |
| Lab 03 — Node scheduling | [Notes](labs/lab-03/engineering-notes.md) | [RCA](labs/lab-03/rca.md) | Cause supported; workload and dashboard HTTP recovery documented |
| Lab 04 — Internal connectivity | [Engineering notes](labs/lab-04/engineering-notes.md) | [RCA](labs/lab-04/rca.md) | Selector mismatch identified; HTTP recovery documented |
| Lab 05 — Ingress delivery | [Engineering notes](labs/lab-05/engineering-notes.md) | [RCA](labs/lab-05/rca.md) | Port mismatch diagnosed; separate IAM blocker documented |
| Lab 05.1 — Request routing | [Notes](labs/lab-05-1/engineering-notes.md) | [RCA](labs/lab-05-1/rca.md) | Original request returned HTTP 200 after correction |
| Lab 05.2 — Entry-point regression | [Notes](labs/lab-05-2/engineering-notes.md) | [RCA](labs/lab-05-2/rca.md) | HTTP 200 and 648 bytes received after restore |
| Lab 06 — Persistent storage | [Notes](labs/lab-06/engineering-notes.md) | Pending investigation | Prepared; live validation pending |
| INC-001 — Diagnostic exec denied | [Notes](incidents/INC-001-pods-exec/engineering-notes.md) | [RCA](incidents/INC-001-pods-exec/rca.md) | Cause confirmed; fix published; operator validation pending in source notes |

Read each lab's README for a spoiler-free entry point. Completed RCAs disclose solutions; the open lab does not.

## Documentation conventions

Each completed lab contains a README, engineering notes, and an RCA. Notes explain observations and decisions; the RCA summarizes the failure mechanism, impact, remediation, and evidence of recovery. Use the [engineering notes template](templates/engineering-notes.md) and [RCA template](templates/rca.md) for new investigations.

The source is Douglas's Engineering notes document, reviewed on October 1, 2026, together with the session record and versioned automation. Duplicate passages were consolidated. Commands were corrected without converting intended tests into claimed results. Account identifiers are generalized in new incident excerpts. Original notes remain unchanged in Google Docs.

Times retain their recorded timezone when available. A timestamp without a timezone is identified as such; no incident duration, availability percentage, or customer impact is inferred from an incomplete record. These are controlled lab exercises, not production incident claims.

## Project records

- [Historical Terraform state reconciliation](history/terraform-state-reconciliation.md)
- [Repository naming and migration](repository-naming.md)
- [Bedrock work status](bedrock/README.md)

## Word copies for OneNote

These English exports mirror the application guides. Markdown remains the editable source of truth.

- [Application deployment playbook](exports/simple-test-playbook.docx)
- [Kubernetes walkthrough](exports/simple-test-kubernetes-explained.docx)
- [EKS egress playbook](exports/eks-egress-playbook.docx)

[Lab 05.2 — completed iteration](labs/lab-05-2/README.md): recovered; [refreshment](labs/lab-05-2/concept-refresh.md) and [start guide](simple-test/lab-05-2-start.md).

Labs 05 and 05.1 were updated from Douglas's OneNote pages on October 6, 2026. The corresponding pages were organized in English. Lab 05.1 recovery output is attributed to the conversation, separately from the original OneNote observations.

[Lab 06 start guide](simple-test/lab-06-start.md) · [Storage refreshment](labs/lab-06/concept-refresh.md). Lab 05.2 was organized from OneNote and the conversation on October 7, 2026.

## Current lab tools

Use **SRE labs (current: 06)** in Actions; `lab-06` is selected by default. Earlier scenario workflows are [archived](../archive/workflows/README.md) and their operations remain available through the same selector. For Lab 06, keep the [command guide and output interpretation](labs/lab-06/command-guide.md) next to the concept refresh.
