# Kubernetes Deployment for Project Aria

Deploy Project Aria on Minikube in under 2 minutes.

### 1. Start Minikube & Enable Ingress
```bash
minikube start --cpus=4 --memory=6144
minikube addons enable ingress