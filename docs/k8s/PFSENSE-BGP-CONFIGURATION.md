# pfSense BGP Configuration Guide for Cilium VIP Management

## Overview

This guide configures pfSense as a BGP peer for Cilium LoadBalancer VIP management. pfSense will receive /32 route advertisements from Kubernetes worker nodes and provide routing for VIP traffic.

**Architecture:**
- **pfSense Router**: AS 65001 (BGP router)
- **Kubernetes Workers**: AS 64513 (6 workers)
- **VIP Pools**: 192.168.100-103.0/24 + 192.168.200.0/24 (5 pools)
- **BGP Timers**: 3s keepalive, 9s hold time
- **Authentication**: MD5 password authentication

---

## Prerequisites

1. pfSense with FRR package installed
2. LAN IP: 192.168.100.1
3. Network access to all 6 worker nodes
4. MD5 password chosen for BGP authentication

---

## Installation Steps

### Step 1: Install FRR Package

1. Navigate to **System → Package Manager → Available Packages**
2. Search for **"FRR"**
3. Click **Install** on the FRR package
4. Wait for installation to complete

---

### Step 2: Enable FRR BGP

1. Navigate to **Services → FRR → Global Settings**
2. Check **Enable FRR**
3. Check **Enable BGP**
4. Click **Save**

---

### Step 3: Configure BGP Global Settings

1. Navigate to **Services → FRR → BGP**
2. Configure the following:

   **General Settings:**
   - **Enable**: ✓ (checked)
   - **BGP AS Number**: `65001`
   - **Router ID**: `192.168.100.1` (pfSense LAN IP)

   **Advanced Options:**
   - **BGP Timers**:
     - Keepalive: `3`
     - Holdtime: `9`
   - **Graceful Restart**: ✓ Enabled

3. Click **Save**

---

### Step 4: Configure BGP Neighbors (Worker Nodes)

Add each worker node as a BGP neighbor. Repeat this for all 6 workers.

#### Worker Node IPs (from your cluster)
- apple: `192.168.100.201`
- blueberry: `192.168.100.202`
- cherry: `192.168.100.203`
- lemon: `192.168.100.204`
- pecan: `192.168.100.205`
- rubharb: `192.168.100.206`

**For EACH worker, create a neighbor:**

1. Navigate to **Services → FRR → BGP → Neighbors**
2. Click **Add**

   **Neighbor Configuration:**
   - **Name/Description**: `Worker-apple` (change per node)
   - **Peer IP**: `192.168.100.201` (change per node)
   - **Remote AS**: `64513`
   - **Update Source**: `192.168.100.1` (pfSense LAN IP)

   **Timers:**
   - **Keepalive**: `3`
   - **Holdtime**: `9`

   **Authentication:**
   - **Password**: Enter the same MD5 password used in Kubernetes secret
     - ⚠️ **IMPORTANT**: This MUST match the password in `cilium-bgp-auth` secret

   **Advanced Options:**
   - **eBGP Multihop**: `1` (direct connection)
   - **Next Hop Self**: ✓ (optional, for route redistribution)

3. Click **Save**
4. **Repeat for all 6 workers**

---

### Step 5: Configure Route Acceptance

1. Navigate to **Services → FRR → BGP → Advanced**
2. Add the following configuration to accept VIP routes:

```
# Accept routes from worker nodes (AS 64513)
bgp neighbor 64513 route-map ACCEPT_VIP in

# Define route-map to accept VIP pools
route-map ACCEPT_VIP permit 10
 match ip address prefix-list VIP_POOLS

# Define VIP pool prefixes
ip prefix-list VIP_POOLS seq 10 permit 192.168.100.0/24 ge 32
ip prefix-list VIP_POOLS seq 20 permit 192.168.101.0/24 ge 32
ip prefix-list VIP_POOLS seq 30 permit 192.168.102.0/24 ge 32
ip prefix-list VIP_POOLS seq 40 permit 192.168.103.0/24 ge 32
ip prefix-list VIP_POOLS seq 50 permit 192.168.200.0/24 ge 32
```

**Explanation:**
- `ge 32`: Accept only /32 routes (specific VIPs)
- `permit 192.168.100.0/24 ge 32`: Accept any /32 within 192.168.100.0/24 range

3. Click **Save**

---

### Step 6: Apply Configuration

1. Navigate to **Services → FRR → Global Settings**
2. Click **Apply Changes**
3. Wait for FRR to reload (5-10 seconds)

---

## Verification Steps

### Check BGP Sessions

1. Navigate to **Diagnostics → Command Prompt**
2. Run the following commands:

```bash
# Show BGP summary
vtysh -c "show bgp summary"

# Expected output: 6 neighbors in "Established" state
```

**Expected Output:**
```
Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
192.168.100.201 4 64513      12      12        0    0    0 00:00:30            0
192.168.100.202 4 64513      12      12        0    0    0 00:00:30            0
192.168.100.203 4 64513      12      12        0    0    0 00:00:30            0
192.168.100.204 4 64513      12      12        0    0    0 00:00:30            0
192.168.100.205 4 64513      12      12        0    0    0 00:00:30            0
192.168.100.206 4 64513      12      12        0    0    0 00:00:30            0
```

### Check Received Routes

```bash
# Show BGP routes
vtysh -c "show bgp ipv4 unicast"

# Show routes learned from specific neighbor
vtysh -c "show bgp neighbor 192.168.100.201 routes"
```

**Expected Output:** (when LoadBalancer services are created)
```
   Network          Next Hop            Metric LocPrf Weight Path
*> 192.168.200.10/32 192.168.100.201          0             0 64513 i
*> 192.168.103.10/32 192.168.100.202          0             0 64513 i
```

### Test VIP Reachability

```bash
# Ping a VIP (once LoadBalancer service is created)
ping -c 4 192.168.200.10
```

---

## Troubleshooting

### BGP Sessions Not Establishing

**Symptom:** Neighbors show "Active" or "Connect" instead of "Established"

**Checks:**
1. Verify MD5 password matches on both sides
   ```bash
   vtysh -c "show running-config" | grep password
   ```

2. Check network connectivity
   ```bash
   ping 192.168.100.201  # Test each worker IP
   ```

3. Check firewall rules (LAN interface should allow BGP port 179)
   ```
   Navigate to: Firewall → Rules → LAN
   Ensure rule exists: Allow TCP 179 from worker IPs
   ```

4. View BGP debug logs
   ```bash
   vtysh -c "debug bgp updates"
   vtysh -c "debug bgp neighbor-events"
   ```

### No Routes Received

**Symptom:** BGP sessions established but no routes in table

**Checks:**
1. Verify Kubernetes LoadBalancer services exist
   ```bash
   kubectl get svc --all-namespaces -o wide | grep LoadBalancer
   ```

2. Check Cilium BGP advertisement
   ```bash
   kubectl exec -n kube-system <cilium-pod> -- cilium bgp routes
   ```

3. Verify route-map configuration
   ```bash
   vtysh -c "show route-map ACCEPT_VIP"
   ```

### Routes Received But Not in Routing Table

**Symptom:** Routes show in BGP table but not in `show ip route`

**Checks:**
1. Verify route-map allows routes
   ```bash
   vtysh -c "show ip bgp 192.168.200.10/32"
   ```

2. Check if routes are being filtered
   ```bash
   vtysh -c "show ip prefix-list VIP_POOLS"
   ```

---

## Security Considerations

1. **MD5 Authentication**: Always use MD5 authentication for BGP sessions
   - Never use cleartext or no authentication in production

2. **Firewall Rules**: Restrict BGP access to worker nodes only
   ```
   Firewall → Rules → LAN
   Add rule: Allow TCP 179 from 192.168.100.201-206 only
   ```

3. **Route Filtering**: Only accept VIP pool routes (/32 prefixes)
   - Never accept default routes or broad prefixes from workers

4. **BGP Community Tags**: Use communities for route tracking
   - Cilium advertises routes with community `64513:100`
   - Can be used for additional filtering or policy

---

## Integration with Kubernetes

After pfSense is configured, apply Cilium BGP configuration:

```bash
# Apply BGP configuration
kubectl apply -f kubernetes/cilium/bgp-config.yaml

# Apply VIP pools
kubectl apply -f kubernetes/cilium/vip-pools.yaml

# Run validation tests
./tests/infrastructure/bgp-validation.sh --verbose
```

---

## Example: Creating a LoadBalancer Service

Test the BGP setup with a simple service:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test-nginx
  namespace: default
  labels:
    io.cilium/lb-pool: mgmt
    advertise: bgp
spec:
  type: LoadBalancer
  loadBalancerIP: 192.168.200.10  # From mgmt pool
  ports:
    - port: 80
      targetPort: 80
      protocol: TCP
  selector:
    app: nginx
---
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  containers:
    - name: nginx
      image: nginx:alpine
      ports:
        - containerPort: 80
```

Apply and verify:
```bash
kubectl apply -f test-nginx.yaml

# Check VIP assignment
kubectl get svc test-nginx

# Verify BGP advertisement from pfSense
vtysh -c "show bgp ipv4 unicast 192.168.200.10/32"

# Test connectivity
curl http://192.168.200.10
```

---

## Monitoring and Maintenance

### Regular Health Checks

```bash
# Check BGP session status
vtysh -c "show bgp summary"

# Check route count
vtysh -c "show bgp ipv4 unicast summary"

# View BGP neighbors detail
vtysh -c "show bgp neighbors"
```

### Log Monitoring

```bash
# View BGP logs
cat /var/log/frr/bgpd.log

# Real-time log monitoring
tail -f /var/log/frr/bgpd.log
```

### Performance Metrics

- **Session Uptime**: Should remain stable (hours/days)
- **Routes Received**: Should match number of LoadBalancer services
- **Prefix Count**: One /32 per LoadBalancer service
- **Updates**: Should be minimal after initial convergence

---

## References

- [FRR BGP Documentation](https://docs.frrouting.org/en/latest/bgp.html)
- [Cilium BGP Control Plane](https://docs.cilium.io/en/stable/network/bgp-control-plane/)
- [pfSense FRR Package](https://docs.netgate.com/pfsense/en/latest/packages/frr.html)

---

## Support

For issues:
1. Check pfSense FRR logs: `/var/log/frr/bgpd.log`
2. Check Cilium BGP status: `kubectl exec -n kube-system <cilium-pod> -- cilium bgp peers`
3. Run validation script: `./tests/infrastructure/bgp-validation.sh --verbose`
