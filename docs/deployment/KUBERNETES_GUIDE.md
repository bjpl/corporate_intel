# Kubernetes Deployment Guide

Complete guide for deploying Corporate Intel to Kubernetes using Helm and Kustomize.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Deployment Methods](#deployment-methods)
4. [Environment Configuration](#environment-configuration)
5. [Scaling and High Availability](#scaling-and-high-availability)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

```bash
# kubectl (v1.28+)
kubectl version --client

# Helm (v3.13+)
helm version

# kustomize (v5.0+)
kustomize version

# AWS CLI (if using EKS)
aws --version
```

### Cluster Requirements

- Kubernetes 1.28+ cluster
- Minimum 3 worker nodes
- 16GB RAM per node
- 100GB storage per node
- Network policies support
- LoadBalancer service support

## Infrastructure Setup

### 1. Create Namespace

```bash
# Create production namespace
kubectl create namespace production

# Label namespace for network policies
kubectl label namespace production name=production tier=production
```

### 2. Install Required Operators

```bash
# Cert Manager (SSL/TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# External Secrets Operator (Vault integration)
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace

# Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace
```

## Deployment Methods

### Method 1: Helm Deployment (Recommended)

#### Staging Deployment

```bash
# Add Helm repository
helm repo add corporate-intel ./helm/corporate-intel

# Install/Upgrade staging
helm upgrade --install corporate-intel-staging ./helm/corporate-intel \
  --namespace staging \
  --create-namespace \
  --values ./helm/corporate-intel/values-staging.yaml \
  --set image.tag=staging-$(git rev-parse --short HEAD) \
  --wait \
  --timeout 10m
```

#### Production Deployment

```bash
# Production deployment with all checks
helm upgrade --install corporate-intel ./helm/corporate-intel \
  --namespace production \
  --values ./helm/corporate-intel/values-production.yaml \
  --set image.tag=v1.0.0 \
  --wait \
  --timeout 10m \
  --atomic \
  --cleanup-on-fail

# Verify deployment
kubectl rollout status deployment/prod-corporate-intel-api -n production
```

### Method 2: Kustomize Deployment

#### Base Deployment

```bash
# Build and apply base manifests
kubectl apply -k k8s/base/
```

#### Environment-Specific Deployment

```bash
# Staging
kubectl apply -k k8s/overlays/staging/

# Production
kubectl apply -k k8s/overlays/production/
```

### Method 3: Automated Scripts

```bash
# Staging deployment
./scripts/deploy-staging.sh staging-$(git rev-parse --short HEAD)

# Production deployment (with safety checks)
./scripts/deploy-production.sh v1.0.0
```

## Environment Configuration

### Staging Environment

**Configuration:**
- 2 replicas minimum
- 10 replicas maximum (HPA)
- CPU: 200m-500m
- Memory: 384Mi-1Gi
- Debug mode enabled
- Aggressive autoscaling

**Access:**
- API: https://staging-api.corporate-intel.example.com
- Metrics: https://staging-metrics.corporate-intel.internal

### Production Environment

**Configuration:**
- 5 replicas minimum
- 50 replicas maximum (HPA)
- CPU: 500m-2000m
- Memory: 1Gi-4Gi
- Debug mode disabled
- Conservative autoscaling
- Multi-zone pod anti-affinity

**Access:**
- API: https://api.corporate-intel.com
- Metrics: https://metrics.corporate-intel.internal (VPN only)

## Secrets Management

### Using Vault

```bash
# Initialize Vault
./scripts/vault-init.sh

# Configure Kubernetes auth
vault write auth/kubernetes/config \
    kubernetes_host="https://kubernetes.default.svc:443"

# Create role for application
vault write auth/kubernetes/role/corporate-intel \
    bound_service_account_names=corporate-intel-api \
    bound_service_account_namespaces=production \
    policies=corporate-intel \
    ttl=1h
```

### Using External Secrets Operator

```yaml
# ExternalSecret manifest (already in k8s/base/secret.yaml)
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: corporate-intel-vault-secrets
spec:
  refreshInterval: 15m
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: corporate-intel-secrets
```

## Scaling and High Availability

### Horizontal Pod Autoscaling (HPA)

```bash
# View HPA status
kubectl get hpa -n production

# Configure custom metrics
kubectl apply -f k8s/base/hpa.yaml

# Manual scaling
kubectl scale deployment/prod-corporate-intel-api --replicas=10 -n production
```

### Vertical Pod Autoscaling (VPA)

```bash
# Install VPA
git clone https://github.com/kubernetes/autoscaler.git
./autoscaler/vertical-pod-autoscaler/hack/vpa-up.sh

# Apply VPA configuration
kubectl apply -f k8s/base/hpa.yaml  # Contains VPA manifest
```

### Pod Disruption Budget

```bash
# Ensure minimum availability during updates
kubectl apply -f k8s/base/pdb.yaml

# View PDB status
kubectl get pdb -n production
```

## Network Policies

```bash
# Apply network security policies
kubectl apply -f k8s/base/networkpolicy.yaml

# Test connectivity
kubectl run test-pod --image=curlimages/curl -n production -it --rm -- \
  curl http://prod-corporate-intel-api:80/health
```

## Monitoring Integration

### Prometheus

```bash
# Verify Prometheus is scraping metrics
kubectl port-forward -n monitoring svc/prometheus-server 9090:80

# Visit: http://localhost:9090/targets
```

### Grafana

```bash
# Access Grafana
kubectl port-forward -n monitoring svc/grafana 3000:80

# Login: admin / (get password)
kubectl get secret -n monitoring grafana -o jsonpath="{.data.admin-password}" | base64 -d
```

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods -n production

# View pod logs
kubectl logs -f <pod-name> -n production

# Describe pod for events
kubectl describe pod <pod-name> -n production
```

#### 2. Health Check Failures

```bash
# Test health endpoint
kubectl run debug --image=curlimages/curl -n production -it --rm -- \
  curl -v http://prod-corporate-intel-api:80/health

# Check liveness/readiness probes
kubectl describe pod <pod-name> -n production | grep -A 10 Liveness
```

#### 3. Network Connectivity Issues

```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox -n production -- nslookup postgres-service

# Check network policies
kubectl get networkpolicies -n production
kubectl describe networkpolicy <policy-name> -n production
```

#### 4. Image Pull Errors

```bash
# Check image pull secrets
kubectl get secrets -n production

# Verify image exists
docker manifest inspect corporate-intel:v1.0.0

# Create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=<username> \
  --docker-password=<token> \
  -n production
```

### Debug Commands

```bash
# Get all resources
kubectl get all -n production

# View events
kubectl get events -n production --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n production
kubectl top nodes

# Access pod shell
kubectl exec -it <pod-name> -n production -- /bin/sh

# View cluster info
kubectl cluster-info
kubectl get nodes -o wide
```

## Rollback Procedures

### Helm Rollback

```bash
# List releases
helm list -n production

# View release history
helm history corporate-intel -n production

# Rollback to previous version
helm rollback corporate-intel -n production

# Rollback to specific revision
helm rollback corporate-intel 3 -n production
```

### Kubectl Rollback

```bash
# View rollout history
kubectl rollout history deployment/prod-corporate-intel-api -n production

# Rollback deployment
kubectl rollout undo deployment/prod-corporate-intel-api -n production

# Rollback to specific revision
kubectl rollout undo deployment/prod-corporate-intel-api --to-revision=2 -n production
```

## Best Practices

1. **Always use production values file for production deployments**
2. **Create database backups before deployments**
3. **Use `--atomic` flag with Helm for automatic rollback on failure**
4. **Monitor deployments in real-time using Grafana dashboards**
5. **Test in staging before promoting to production**
6. **Use blue-green or canary deployments for zero-downtime updates**
7. **Implement proper resource requests and limits**
8. **Enable pod disruption budgets for HA**
9. **Use network policies for security**
10. **Regularly update Kubernetes and Helm charts**

## Additional Resources

- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [External Secrets Operator](https://external-secrets.io/)
