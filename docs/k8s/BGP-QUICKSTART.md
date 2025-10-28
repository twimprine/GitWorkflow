# BGP VIP Management - Quick Start Guide

**5-Minute Setup Guide for Cilium BGP LoadBalancer Integration**

---

## Prerequisites ✓

- Kubernetes cluster with Cilium CNI (v1.16.5)
- pfSense router at 192.168.100.1
- kubectl configured
- SOPS installed

---

## Step 1: Create BGP Secret (2 minutes)

```bash
# Generate strong password
BGP_PASSWORD=$(openssl rand -base64 32)
echo "Save this password: $BGP_PASSWORD"

# Create and encrypt secret
cd /home/thomas/Repositories/AWS_Environment
cat > /tmp/bgp-secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: cilium-bgp-auth
  namespace: kube-system
type: Opaque
stringData:
  password: "$BGP_PASSWORD"
EOF

# Encrypt with SOPS
sops --encrypt /tmp/bgp-secret.yaml > kubernetes/cilium/bgp-secret.enc.yaml

# Apply to cluster
sops --decrypt kubernetes/cilium/bgp-secret.enc.yaml | kubectl apply -f -

# Clean up
rm /tmp/bgp-secret.yaml
```

---

## Step 2: Deploy BGP Configuration (30 seconds)

```bash
# Apply BGP peering policy
kubectl apply -f kubernetes/cilium/bgp-config.yaml

# Apply VIP pools
kubectl apply -f kubernetes/cilium/vip-pools.yaml

# Verify
kubectl get ciliumbgppeeringpolicy -n kube-system
kubectl get ciliumloadbalancerippool -n kube-system
```

---

## Step 3: Configure pfSense (3 minutes)

### Quick Commands via pfSense Shell

```bash
# Install FRR (if not already installed)
pkg install -y frr8

# Configure FRR
cat > /usr/local/etc/frr/frr.conf <<EOF
frr version 8.5
frr defaults traditional
!
router bgp 65001
 bgp router-id 192.168.100.1
 timers bgp 3 9
 neighbor 192.168.100.201 remote-as 64513
 neighbor 192.168.100.201 password $BGP_PASSWORD
 neighbor 192.168.100.202 remote-as 64513
 neighbor 192.168.100.202 password $BGP_PASSWORD
 neighbor 192.168.100.203 remote-as 64513
 neighbor 192.168.100.203 password $BGP_PASSWORD
 neighbor 192.168.100.204 remote-as 64513
 neighbor 192.168.100.204 password $BGP_PASSWORD
 neighbor 192.168.100.205 remote-as 64513
 neighbor 192.168.100.205 password $BGP_PASSWORD
 neighbor 192.168.100.206 remote-as 64513
 neighbor 192.168.100.206 password $BGP_PASSWORD
!
ip prefix-list VIP_POOLS seq 10 permit 192.168.100.0/24 ge 32
ip prefix-list VIP_POOLS seq 20 permit 192.168.101.0/24 ge 32
ip prefix-list VIP_POOLS seq 30 permit 192.168.102.0/24 ge 32
ip prefix-list VIP_POOLS seq 40 permit 192.168.103.0/24 ge 32
!
route-map ACCEPT_VIP permit 10
 match ip address prefix-list VIP_POOLS
!
EOF

# Enable and restart FRR
service frr enable
service frr restart
```

**OR** use the pfSense WebGUI (recommended):
1. System → Package Manager → Install "FRR"
2. Services → FRR → Global Settings → Enable FRR + BGP
3. Services → FRR → BGP → Configure AS 65001, Router ID 192.168.100.1
4. Services → FRR → BGP → Neighbors → Add 6 neighbors (see full guide)

---

## Step 4: Validate (30 seconds)

```bash
# Run validation script
./tests/infrastructure/bgp-validation.sh --verbose

# Check BGP sessions from pfSense
vtysh -c "show bgp summary"
# Expected: 6 neighbors "Established"
```

---

## Step 5: Test with LoadBalancer Service (1 minute)

```bash
# Create test service
kubectl create deployment nginx-test --image=nginx:alpine
kubectl expose deployment nginx-test \
  --type=LoadBalancer \
  --port=80 \
  --labels=io.cilium/lb-pool=mgmt,advertise=bgp \
  --load-balancer-ip=192.168.200.20

# Verify VIP assigned
kubectl get svc nginx-test
# Expected: EXTERNAL-IP = 192.168.200.20

# Test connectivity
curl http://192.168.200.20
# Expected: Nginx welcome page

# Clean up
kubectl delete svc nginx-test
kubectl delete deployment nginx-test
```

---

## VIP Pool Usage

Assign services to pools using labels:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  labels:
    io.cilium/lb-pool: mgmt  # Choose: mgmt, default, dev, test, prod
    advertise: bgp           # Required for BGP advertisement
spec:
  type: LoadBalancer
  loadBalancerIP: 192.168.200.10  # Optional: request specific IP
  # ... rest of service spec
```

---

## Troubleshooting

### BGP sessions not establishing?

```bash
# Check Cilium logs
kubectl logs -n kube-system -l k8s-app=cilium | grep -i bgp

# Check pfSense logs
tail -f /var/log/frr/bgpd.log

# Verify password matches
kubectl get secret -n kube-system cilium-bgp-auth -o jsonpath='{.data.password}' | base64 -d
```

### VIP not assigned?

```bash
# Verify pool exists
kubectl get ciliumloadbalancerippool -n kube-system

# Check pool has available IPs
kubectl describe ciliumloadbalancerippool -n kube-system dev-pool

# Verify service has correct labels
kubectl get svc <service-name> -o yaml | grep -A5 labels
```

---

## Full Documentation

- **Deployment Guide**: `docs/BGP-DEPLOYMENT-GUIDE.md`
- **pfSense Configuration**: `docs/PFSENSE-BGP-CONFIGURATION.md`
- **Implementation Report**: `BGP-VIP-IMPLEMENTATION-REPORT.md`
- **Validation Tests**: `tests/infrastructure/bgp-validation.sh`

---

## Success Criteria

✅ 6 BGP sessions established
✅ 5 VIP pools created (mgmt, default, dev, test, prod)
✅ LoadBalancer services get VIPs automatically
✅ VIPs reachable from network
✅ Validation script passes all tests

---

**Total Setup Time: ~7 minutes**

*Last Updated: 2025-10-05*
