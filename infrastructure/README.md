# Infrastructure

| Path | Contents |
| --- | --- |
| [containers/compose.yaml](containers/compose.yaml) | PostgreSQL 17, migration, API and worker services |
| [kubernetes/base](kubernetes/base) | Namespace, deployments, probes, network policies, state volume |
| [kubernetes/overlays/kind](kubernetes/overlays/kind) | Test PostgreSQL and credentials for Kind |
| [supabase](supabase/) | Owner-isolated account migration |

```sh
scripts/deployment/compose.sh up --build --wait
scripts/deployment/kind_smoke.sh
```

[Deployment](../docs/operations/DEPLOYMENT.md)
