# Lab 07 — Autoscaling investigation

**Status:** prepared; live activation and investigation pending.

## Incident statement

After a workload change, the application remains available, but its autoscaling
status is no longer healthy. Determine whether the HPA can evaluate the workload,
which dependency or configuration explains the symptom, and how to verify recovery.
Do not assume that an unchanged replica count is itself a failure.

## Expected behavior

The application responds to HTTP. Its HPA can obtain the configured measurement
and evaluate desired replicas within its configured bounds. Actual growth requires
sufficient demand; this exercise does not generate load automatically.

## Investigation contract

Identify the affected object, capture conditions and events, distinguish observations
from assumptions, and propose the smallest supported correction. A successful HTTP
response does not validate scaling, and a resource-usage sample does not explain a
controller decision by itself. Ask for a hint when a term or boundary is unfamiliar.

Read [concept refresh](concept-refresh.md), use the [command companion](command-guide.md),
and follow the [start guide](../../simple-test/lab-07-start.md). Keep implementation
scripts closed during investigation if you want to avoid spoilers.

Record findings in [engineering notes](engineering-notes.md). There is no completed RCA yet.
