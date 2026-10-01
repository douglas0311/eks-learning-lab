# Lab 01 Container startup investigation

A new application revision fails to become ready after an update. Investigate its impact and identify why the new container cannot remain running.

Activate with **Update simple-test → configuration: lab-01** after the healthy initial deployment. Confirm the patch step succeeded; a later rollout timeout can be the expected symptom. Authentication or patch failure does not establish successful activation. Preserve evidence before restoring with **Update simple-test → baseline**.

- [Engineering notes](engineering-notes.md) — investigation and learning record; contains the diagnosis.
- [RCA](rca.md) — confirmed cause and recovery limitations; contains the solution.
- [Application playbook](../../simple-test/playbook.md) — prerequisites and healthy deployment.
