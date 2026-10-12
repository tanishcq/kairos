# Kubernetes (local, kind)

Runs all of Kairos on a local [kind](https://kind.sigs.k8s.io/) cluster: Kubernetes v1.36.4,
one node, entry point http://localhost:8090.

```text
browser -> localhost:8090 -> kind node :80 -> Envoy Gateway -> frontend (Nginx)
        -> /api/* -> hobby-service | session-service | user-service -> postgres
```

## Files

| File                   | What it creates                                                       |
|------------------------|-----------------------------------------------------------------------|
| `kind-config.yaml`     | The cluster (node image pinned by digest; host ports 8090 and 8443)   |
| `namespace.yaml`       | Namespace `kairos`                                                    |
| `postgres.yaml`        | Postgres StatefulSet with a 1 GiB PersistentVolumeClaim + headless Service |
| `hobby-service.yaml`, `session-service.yaml`, `user-service.yaml` | Deployment + Service each (port 8000) |
| `frontend.yaml`        | Nginx Deployment + Service (port 80)                                  |
| `gateway.yaml`         | EnvoyProxy (bind to node port 80), GatewayClass, Gateway, HTTPRoute -> frontend |

The Secret `kairos-env` is **not** in Git: it is created from the root `.env`
(`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET`).

## Create everything (from the repo root)

```bash
kind create cluster --config k8s/kind-config.yaml
kubectl apply -f k8s/namespace.yaml
kubectl config set-context --current --namespace=kairos
kubectl create secret generic kairos-env --from-env-file=.env

kubectl apply -f k8s/postgres.yaml
kubectl rollout status statefulset/postgres
kubectl apply -f k8s/hobby-service.yaml -f k8s/session-service.yaml \
  -f k8s/user-service.yaml -f k8s/frontend.yaml

helm install eg oci://docker.io/envoyproxy/gateway-helm --version v1.9.2 \
  -n envoy-gateway-system --create-namespace --wait
kubectl apply -f k8s/gateway.yaml
kubectl wait --for=condition=Programmed gateway/kairos
```

Then open http://localhost:8090.

## Useful commands

```bash
kubectl get pods                          # everything in namespace kairos
kubectl logs deploy/user-service          # logs of one service
kubectl rollout restart deploy/hobby-service
kubectl port-forward svc/user-service 18002:8000   # reach one service directly
kind delete cluster --name kairos         # remove everything (data included)
```

## Notes

- Images come from GHCR, pinned to `sha-<commit>` tags (never `latest`).
- Pods run as non-root with a read-only root filesystem, no Linux capabilities and the
  default seccomp profile. Postgres is the exception (the official image starts as root).
- Backends have a 5 s `preStop` sleep so rollouts don't drop requests (measured: 9 of 351
  requests got 502 during a restart without it, 0 of 714 with it).
- Envoy Gateway v1.9 supports Kubernetes v1.33-v1.36, hence the pinned node image.
- Secrets in Kubernetes are base64-encoded, not encrypted. Fine for a local cluster.
