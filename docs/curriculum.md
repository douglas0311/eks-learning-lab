# Progressive SRE curriculum

Douglas investigates symptoms, collects evidence, forms hypotheses, and proposes recovery. The assistant prepares controlled scenarios and reviews the reasoning. Hints are incremental; the learner receives a problem statement rather than a hidden solution.

The original scenario list defines a learning sequence, not a statistical claim about production or interview frequency.

| Stage | Topic | Current coverage |
| --- | --- | --- |
| 01 | Container startup and restart failures | Missing startup configuration investigated; OOMKilled remains a future variant |
| 02 | Pending Pods and resource requests | Oversized CPU request investigated and workload recovered |
| 03 | Node health and scheduling | Scheduling eligibility investigated; actual NotReady and pressure remain future variants |
| 04 | Internal Service connectivity | Selector mismatch diagnosed; HTTP recovery documented |
| 05 | Ingress controller and load balancer creation | Lab 05 port mismatch and IAM blocker diagnosed; 05.1 request recovery documented; 05.2 backend protocol mismatch diagnosed and request recovered |
| 06 | Persistent volumes and mounting | Missing PVC reference diagnosed; original persistent marker read after recovery |
| 07 | Autoscaling expectations and failures | Prepared; live activation and investigation pending |
| 08 | Kubernetes API connectivity and access | Planned; authorization prerequisite already encountered |
| 09 | Workload AWS IAM and IRSA access | Planned |
| 10 | Resource waste and cost investigation | Planned |

## Preparation

Start with a verified healthy application, persistent Terraform state, working diagnostic access, and a recovery path. Introduce one controlled fault and confirm its symptom. Distinguish scenario behavior from automation failures. A failed workflow is not automatically proof of successful fault injection.

Infrastructure needed for ingress, storage, or node autoscaling is added when the relevant exercise needs it. API-access scenarios must preserve an administrative recovery path. Cost exercises use bounded resources or historical evidence.

## Concept refresh before each lab

Provide a short, spoiler-free review of the relevant components, their relationships, terminology, and what common signals do and do not establish. Include end-of-scenario conceptual review questions and a command companion that explains each command's purpose, expected observations, and interpretation limits. Commands provide diagnostic tools, not a mandatory sequence or the injected solution. Keep the refresh separate from the incident statement, implementation, and diagnostic hints; it must not identify the injected fault or prescribe a troubleshooting sequence. This supports recall without replacing the learner's investigation.

The refresh and command companion remain available before and during investigation.
Douglas answers the conceptual questions **after completing the scenario**, using
his evidence where applicable; they are not an entrance quiz. Their purpose is to
consolidate understanding, not test memorized commands. Douglas reported that this
support helped him recognize storage components and investigate Lab 06 independently.

## Agreed variants and gradual independence

Agreement recorded October 8, 2026:

- Keep the prepared Lab 07 as the next exercise. Add variants in subsequent iterations without replacing the remaining curriculum topics.
- Revisit networking with an unfamiliar variant. Douglas sketches the request path and identifies tested and untested boundaries; do not announce the failing boundary.
- Before selecting a diagnostic command, explain the question it answers. Separate observations, interpretations, and unknowns in the notes.
- Before applying a correction, define the functional recovery test. Let Douglas propose it before providing guidance.
- Introduce irrelevant but plausible signals once individual-fault investigations are consistent. Combine related faults only after the foundational sequence and demonstrated readiness; do not increase every difficulty dimension at once.
- Add an explicitly announced time-boxed exercise after the diagnostic method is established. Preserve access to reference material and a recovery path; speed alone is not the score.
- Close selected labs with a five-minute interview-style explanation of impact, evidence, cause, recovery, and uncertainty, followed by questions.

Reduce procedural hints gradually while retaining conceptual references. Evaluate
transfer to unfamiliar scenarios, test selection, evidence quality, recovery
validation, and the kind of assistance needed. A correct guess or elapsed time is
not sufficient evidence of independence. These exercises cannot fully reproduce
production consequences or coordination with real teams.

## Evidence and progression

Each investigation should explain scope, relevant observations, a testable hypothesis, contradictory evidence, recovery, and remaining uncertainty. Record assistance as a guiding question, command help, conceptual clarification, or guided resolution rather than treating a percentage as an objective skill score.

A wrong initial hypothesis is useful when subsequent evidence corrects it. Repeat a topic when needed. Combining faults after stage ten depends on demonstrated investigation quality, not merely completing a count of sessions.

## Session closure

Preserve logs, screenshots, queries, and timestamps before destroying ephemeral infrastructure. Douglas runs the lifecycle and scenario workflows. No scheduled automatic activation or teardown is implied by the curriculum. After evidence review, prepare the next scenario and retain a spoiler-free guide.

[Engineering portfolio](README.md) · [Investigation templates](templates/engineering-notes.md)
