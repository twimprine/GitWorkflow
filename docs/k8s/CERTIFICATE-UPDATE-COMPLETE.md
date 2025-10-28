# API Server Certificate Update - COMPLETED ✅

**Date**: 2025-10-05
**Status**: SUCCESS
**Duration**: ~5 minutes (including API server restarts)

## Problem Solved

The Kubernetes API server certificate didn't include the management VIP (192.168.200.10) in its Subject Alternative Names (SAN), causing TLS validation errors when accessing the cluster via the LoadBalancer VIP.

**Before**:
```bash
kubectl get nodes
# Error: x509: certificate is valid for [...] not 192.168.200.10

# Required workaround:
kubectl --insecure-skip-tls-verify get nodes
```

**After**:
```bash
kubectl get nodes
# Works perfectly! No TLS errors
```

## Changes Applied

### Configuration Updated

**File**: `talos/controlplane.yaml`

```yaml
apiServer:
  certSANs:
    - 192.168.1.21      # tin control plane
    - 192.168.1.23      # nickel control plane
    - 192.168.1.25      # lead control plane
    - 192.168.100.103   # Legacy cluster IP
    - 192.168.200.10    # Management VIP (NEW)
    - k8s-api.local     # DNS name (NEW)
```

### Deployment Steps Executed

1. ✅ Applied updated `controlplane.yaml` to all 3 control plane nodes
2. ✅ Restarted kubelet on each control plane node sequentially:
   - lead (192.168.1.25)
   - nickel (192.168.1.23)
   - tin (192.168.1.21)
3. ✅ Verified all API server pods restarted successfully
4. ✅ Tested kubectl access via VIP - working perfectly
5. ✅ Verified BGP routes still being advertised

## Validation Results

### ✅ kubectl Works Without Insecure Flag
```bash
$ kubectl get nodes
NAME        STATUS   ROLES           AGE     VERSION
apple       Ready    <none>          107m    v1.32.3
blueberry   Ready    <none>          111m    v1.32.3
cherry      Ready    <none>          107m    v1.32.3
lead        Ready    control-plane   4h1m    v1.32.3
lemon       Ready    <none>          107m    v1.32.3
nickel      Ready    control-plane   4h1m    v1.32.3
pecan       Ready    <none>          107m    v1.32.3
rubharb     Ready    <none>          107m    v1.32.3
tin         Ready    control-plane   3h57m   v1.32.3
```

### ✅ LoadBalancer VIP Active
```bash
$ kubectl get svc kubernetes-external
NAME                  TYPE           EXTERNAL-IP      PORT(S)
kubernetes-external   LoadBalancer   192.168.200.10   6443:31652/TCP
```

### ✅ BGP Route Advertisement Active
```bash
$ kubectl exec -n cilium ds/cilium -- cilium bgp routes advertised ipv4 unicast
VRouter   Peer           Prefix              NextHop        Age
64513     192.168.1.99   192.168.200.10/32   192.168.1.40   9m9s
```

### ✅ Cluster Health Maintained
- All 9 nodes: Ready
- All 3 control plane nodes: Healthy
- Zero downtime during update
- BGP sessions: Maintained throughout

## Current Status

**Management VIP**: `192.168.200.10` - Fully functional
**DNS Name**: `k8s-api.local` - Ready for DNS configuration
**TLS Certificate**: Valid for VIP and DNS name
**Cluster Access**: Working perfectly via VIP

## Benefits Achieved

1. **✅ No More TLS Warnings**: kubectl works cleanly via VIP
2. **✅ High Availability**: Can replace any control plane node without reconfiguring kubectl
3. **✅ Professional Setup**: Clean certificate validation matches production standards
4. **✅ Ready for DNS**: Can add friendly DNS name (k8s-api.local) anytime
5. **✅ Version Controlled**: All changes committed to repository for reproducibility

## Optional Next Step: DNS Configuration

You can now add a DNS record for `k8s-api.local → 192.168.200.10`:

### Option 1: pfSense DNS Resolver (Recommended)
1. Navigate to **Services → DNS Resolver** (or DNS Forwarder)
2. Add Host Override:
   - Host: `k8s-api`
   - Domain: `local`
   - IP Address: `192.168.200.10`
   - Description: `Kubernetes API LoadBalancer VIP`
3. Save and Apply

Then update kubeconfig:
```bash
kubectl config set-cluster homelab-test --server=https://k8s-api.local:6443
kubectl get nodes  # Works via friendly DNS name!
```

### Option 2: Local /etc/hosts (Per Machine)
```bash
echo "192.168.200.10 k8s-api.local" | sudo tee -a /etc/hosts
kubectl config set-cluster homelab-test --server=https://k8s-api.local:6443
```

## Reproducibility

All changes are now version controlled:
- `talos/controlplane.yaml` - Updated with VIP in certSANs
- `docs/UPDATE-API-CERT.md` - Complete documentation
- `scripts/update-api-cert.sh` - Automation script (updated)

If you rebuild the cluster from scratch:
1. The updated `controlplane.yaml` will include the VIP in certificates automatically
2. No manual certificate fix needed
3. 100% reproducible from git repository

## Summary

**Problem**: TLS certificate validation failures when accessing API via VIP
**Solution**: Added VIP to API server certificate SANs in Talos configuration
**Result**: ✅ kubectl works perfectly via VIP (192.168.200.10)
**Impact**: Zero downtime, all cluster functionality maintained
**Status**: COMPLETE - Cluster fully operational with validated TLS certificates

---

🎉 **Kubernetes API is now accessible via highly-available VIP with proper TLS validation!**
