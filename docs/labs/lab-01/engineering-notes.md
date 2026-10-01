# Lab 01 Engineering notes

## Context

Investigator: Douglas García Jiménez. Controlled Kubernetes exercise, September 28, 2026. Following an application update, one new `simple-test` Pod entered CrashLoopBackOff while two older Pods remained ready.

## Investigation sequence

I inspected the failing Pod and found repeated container restarts. The events showed kubelet backing off after failures. That established the symptom, but did not explain why NGINX exited.

```bash
kubectl -n simple-test describe pod simple-test-5bc986579f-v7mf5
kubectl -n simple-test logs simple-test-5bc986579f-v7mf5 --previous
```

The retained previous-container log contained:

```text
2026/09/28 21:21:09 [emerg] 1#1: open() "/etc/nginx/lab.conf" failed (2: No such file or directory)
```

The log excerpt does not state its timezone. I compared the failing Pod with a running Pod. The failing Pod's startup arguments included `-c /etc/nginx/lab.conf`; the healthy Pod had no equivalent argument override. The recorded image digests were the same.

| Observation | Failing revision | Healthy revision |
| --- | --- | --- |
| ReplicaSet | simple-test-5bc986579f | simple-test-6c7b59b9f8 |
| NGINX configuration argument | /etc/nginx/lab.conf | No override shown |
| Container behavior | Repeated startup failure | Running and Ready |
| Image digest comparison | Same as healthy Pod | Same as failing Pod |

## Hypothesis and refinement

My hypothesis was that the recent update changed NGINX startup configuration to reference a missing file. The comparison tied the startup error to a concrete difference between healthy and failing revisions.

The precise mechanism is that the container starts, NGINX cannot open the requested configuration, and the process exits. Kubelet restarts it and backs off after repeated failures. CrashLoopBackOff describes that retry behavior, not the original cause.

A Pod phase of Running does not contradict a container waiting in CrashLoopBackOff. The `READY` column also matters. Changing the Deployment's Pod template creates a new revision and typically a new ReplicaSet; the ReplicaSet itself did not choose the bad arguments.

## Recovery proposal and evidence boundary

I proposed returning to the previous working configuration and asking why the new argument was introduced without the required file. Because both revisions used the same image digest, rolling back the configuration is the directly supported correction; changing only the image is not justified by this evidence.

With two desired replicas and the recorded RollingUpdate settings of 25% surge and 25% unavailable, the rounded allowances are one extra Pod and zero unavailable Pods. The third Pod was rollout capacity, not a permanent third replica requirement.

The retained notes establish the cause but do not contain a completed post-recovery HTTP check for this session. Do not claim a measured outage or recovery duration.

## Learning record

I received guidance interpreting the startup log. I independently chose to compare the healthy and failing Pod descriptions and connected the argument difference to the error. The reusable technique is to compare equivalent workloads after isolating the failing component.

[Root cause analysis](rca.md)
