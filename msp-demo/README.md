# ArgoCD Rollouts Pod Traffic Demo

A simple demo application for testing and demonstrating **Argo CD / GitOps deployment workflows** on Kubernetes.

## Purpose

This application is designed to demonstrate:

* Argo CD application deployment
* GitOps synchronization
* Kubernetes rolling updates
* Replica scaling
* Pod version visualization
* Traffic routing between application versions
* Service and Ingress traffic flow
* Deployment status and pod health

## Architecture

```text
Client
  │
  ▼
Ingress
  │
  ▼
Service
  │
  ├──► Pod v1
  ├──► Pod v1
  ├──► Pod v2
  └──► Pod v2
```

The web interface provides a simple visualization of the current Kubernetes deployment, including desired replicas, running pods, application versions, and observed traffic.

## Use Case

Useful for demos, labs, and testing Argo CD deployment behavior without requiring a complex application.

Typical workflow:

```text
Git Change
    ↓
Argo CD Sync
    ↓
Kubernetes Deployment
    ↓
Rolling Update
    ↓
Traffic → New Pods
```
