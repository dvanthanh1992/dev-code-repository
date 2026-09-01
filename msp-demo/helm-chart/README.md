# msp-demo Helm chart

This chart preserves the original values flow:

```text
strategy: canary | blueGreen
canary.*
blueGreen.*
ingress.host
ingress.tls.*
previewIngress.*
certificate.issuerRef.*
```

Additional resources:

- Argo Rollout with real Pod labels.
- Active Service and conditional preview Service.
- Active/preview Ingress and Certificate resources.
- Namespace-scoped topology-reader RBAC.
- Redis StatefulSet, headless Service, AOF, PVC retention.
- Optional Vault-backed ExternalSecret.

Install:

```bash
helm upgrade --install msp-demo . \
  --namespace msp-demo \
  --create-namespace
```

Canary v2:

```bash
helm upgrade msp-demo . \
  --namespace msp-demo \
  --reuse-values \
  --set image.tag=green \
  --set app.version=v2 \
  --set app.color=green \
  --set app.commit=demo-v2
```

Blue/Green:

```bash
helm upgrade msp-demo . \
  --namespace msp-demo \
  --reuse-values \
  --set strategy=blueGreen
```
