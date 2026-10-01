# Lab 01 Root cause analysis

**Status:** cause supported by logs and configuration comparison; recovery verification not retained for this session.

## Summary and impact

A controlled update supplied NGINX with a configuration path that was not present in the container. The new revision repeatedly exited and the rollout could not complete. Two older application Pods remained ready. End-to-end service availability was not measured in the retained evidence.

## Cause and evidence

The failing revision supplied `-c /etc/nginx/lab.conf`. NGINX logged `No such file or directory` for that same path. Healthy and failing Pods used the same image digest but differed in startup arguments and ReplicaSet revision.

The sequence was configuration override → NGINX startup failure → container exit → repeated restart backoff → unavailable new revision. The restart policy was responding to the failure, not causing the missing file.

## Remediation

Proposed mitigation: restore the known working startup configuration using the lab's `baseline` option. If a custom configuration is genuinely needed later, supply it in the image or an appropriate mounted configuration and test startup before rollout.

Verification should include successful rollout, expected ready replicas, no continuing startup failures, and HTTP response. Those checks are a recovery checklist, not results claimed for this session.

## Follow-up

The automation maintainer should test the effective startup command and configuration together. The investigator should retain post-recovery evidence alongside the pre-change logs. Neither action is recorded as completed by these notes.

[Investigation evidence](engineering-notes.md)
