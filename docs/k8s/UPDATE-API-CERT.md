# Updating Kubernetes API Server Certificate for VIP

## Problem
The Kubernetes API server certificate doesn't include the management VIP (192.168.200.10) in its Subject Alternative Names (SAN), causing TLS validation errors when accessing via the VIP.

## Solution
Update the Talos control plane configuration to include the VIP and DNS name in the API server certificate SANs.

## Changes Made

Updated `talos/controlplane.yaml`:
```yaml
apiServer:
  certSANs:
    - 192.168.1.21      # banana control plane
    - 192.168.1.23      # watermelon control plane
    - 192.168.1.25      # raspberry control plane
    - 192.168.100.103   # Legacy cluster IP
    - 192.168.200.10    # Management VIP for Kubernetes API LoadBalancer
    - k8s-api.local     # Optional DNS name for management VIP
```

## Apply the Configuration

### Step 1: Decrypt Secrets (if needed)
```bash
cd talos
./decrypt-secrets.sh
```

### Step 2: Apply Configuration to Control Plane Nodes

Apply to each control plane node:

```bash
# Apply to raspberry (192.168.1.25)
talosctl apply-config --nodes 192.168.1.25 \
  --file controlplane.yaml \
  --mode no-reboot

# Apply to banana (192.168.1.21)
talosctl apply-config --nodes 192.168.1.21 \
  --file controlplane.yaml \
  --mode no-reboot

# Apply to watermelon (192.168.1.23)
talosctl apply-config --nodes 192.168.1.23 \
  --file controlplane.yaml \
  --mode no-reboot
```

### Step 3: Restart API Server on Each Node

The API server needs to be restarted to regenerate the certificate:

```bash
# Restart on raspberry
talosctl service kube-apiserver restart --nodes 192.168.1.25

# Wait 30 seconds for it to come back up
sleep 30

# Restart on banana
talosctl service kube-apiserver restart --nodes 192.168.1.21

# Wait 30 seconds
sleep 30

# Restart on watermelon
talosctl service kube-apiserver restart --nodes 192.168.1.23
```

**Important**: Restart one at a time to maintain cluster availability.

### Step 4: Verify Certificate

Check that the new certificate includes the VIP:

```bash
# Get the certificate from the VIP
echo | openssl s_client -showcerts -connect 192.168.200.10:6443 2>/dev/null | \
  openssl x509 -inform pem -noout -text | \
  grep -A 10 "Subject Alternative Name"

# Expected output should include:
# DNS:k8s-api.local
# IP Address:192.168.200.10
```

### Step 5: Test kubectl via VIP

```bash
# Should now work WITHOUT --insecure-skip-tls-verify
kubectl get nodes

# Or explicitly via VIP
kubectl --server=https://192.168.200.10:6443 get nodes
```

### Step 6: Update kubeconfig (if needed)

If your kubeconfig still uses an individual control plane IP, update it:

```bash
kubectl config set-cluster homelab-test --server=https://192.168.200.10:6443
```

## DNS Configuration (Optional)

Add DNS record for `k8s-api.local` pointing to 192.168.200.10:

### Option 1: /etc/hosts (Local Only)
```bash
echo "192.168.200.10 k8s-api.local" | sudo tee -a /etc/hosts
```

### Option 2: pfSense DNS Forwarder/Resolver
1. Navigate to **Services → DNS Resolver** (or DNS Forwarder)
2. Add Host Override:
   - Host: `k8s-api`
   - Domain: `local`
   - IP Address: `192.168.200.10`
   - Description: `Kubernetes API LoadBalancer VIP`
3. Save and Apply

### Option 3: Update kubeconfig to use DNS
```bash
kubectl config set-cluster homelab-test --server=https://k8s-api.local:6443
```

## Rollback (if needed)

If something goes wrong:

```bash
# Revert controlplane.yaml to previous version
git checkout HEAD~1 talos/controlplane.yaml

# Apply previous config
talosctl apply-config --nodes 192.168.1.21,192.168.1.23,192.168.1.25 \
  --file controlplane.yaml \
  --mode no-reboot

# Restart API servers
talosctl service kube-apiserver restart --nodes 192.168.1.25
sleep 30
talosctl service kube-apiserver restart --nodes 192.168.1.21
sleep 30
talosctl service kube-apiserver restart --nodes 192.168.1.23
```

## Expected Outcome

After applying this configuration:
- ✅ kubectl works via VIP without TLS errors
- ✅ kubectl works via DNS name (if configured)
- ✅ API server certificate includes all control plane IPs and the VIP
- ✅ No need for --insecure-skip-tls-verify flag
- ✅ Control plane remains highly available during update

## Troubleshooting

### Certificate not updated after restart

Check API server logs:
```bash
talosctl logs --nodes 192.168.1.25 kube-apiserver
```

### API server won't start

Check service status:
```bash
talosctl service kube-apiserver status --nodes 192.168.1.25
```

Verify configuration was applied:
```bash
talosctl get machineconfig --nodes 192.168.1.25
```

### Cluster becomes unavailable

Ensure you're restarting API servers one at a time with adequate wait time between restarts. The cluster needs at least 2 of 3 control plane nodes available for quorum.

---

**Last Updated**: 2025-10-05
**Status**: Configuration ready for deployment
**Impact**: Low - API server restart required but maintains cluster availability
