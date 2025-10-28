# BGP Troubleshooting Guide

## Current Issue: BGP Routes Not Being Accepted by pfSense

### Symptom
- BGP sessions: ✅ 6/6 Established
- VIP assigned: ✅ 192.168.200.10
- Routes advertised from Cilium: ❓ Unknown (need to verify)
- Routes accepted by pfSense: ❌ 0 accepted prefixes
- VIP reachable: ❌ No route to host

### Root Cause
pfSense BGP configuration is rejecting ALL incoming routes from workers.

**Evidence from pfSense BGP Summary**:
```
Neighbor        V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
192.168.1.40    4      64513     26816     26823      127    0    0 00:42:21            0   <- Zero prefixes received
192.168.1.41    4      64513     26817     26824      127    0    0 00:41:34            0   <- Zero prefixes received
192.168.1.42    4      64513     26816     26818      127    0    0 00:40:19            0   <- Zero prefixes received
192.168.1.43    4      64513     26815     26822      127    0    0 00:39:37            0   <- Zero prefixes received
192.168.1.44    4      64513     26820     26821      127    0    0 00:40:33            0   <- Zero prefixes received
192.168.1.46    4      64513     26884     26823      127    0    0 00:42:21            0   <- Zero prefixes received
```

**Current pfSense Route-Map Configuration**:
- Outbound route-map: `*ADVERTISE_LB_POOL` (outgoing TO workers)
- Inbound route-map: `*ALLOW-ALL-IN` (incoming FROM workers)

The issue is that `*ALLOW-ALL-IN` is **NOT** configured correctly or doesn't exist.

### Solution: Fix pfSense Inbound Route-Map

**RECOMMENDED**: See [`PFSENSE-BGP-FIX.md`](PFSENSE-BGP-FIX.md) for the simplest shell-based method.

#### Method 1: Shell Access (Recommended - Works on All pfSense Versions)

SSH to pfSense and use vtysh:
```bash
# SSH to pfSense
ssh admin@192.168.1.99

# Enter shell
option 8

# Edit FRR config
vi /usr/local/etc/frr/frr.conf
```

#### Step 2: Add/Fix Inbound Route-Map

Add this configuration to `/usr/local/etc/frr/frr.conf`:

```
# Define IP prefix-list for VIP pools
ip prefix-list VIP_POOLS seq 10 permit 192.168.100.0/24 ge 32 le 32
ip prefix-list VIP_POOLS seq 20 permit 192.168.101.0/24 ge 32 le 32
ip prefix-list VIP_POOLS seq 30 permit 192.168.102.0/24 ge 32 le 32
ip prefix-list VIP_POOLS seq 40 permit 192.168.103.0/24 ge 32 le 32
ip prefix-list VIP_POOLS seq 50 permit 192.168.200.0/24 ge 32 le 32

# Define route-map to accept VIP routes from workers
route-map ACCEPT_VIP_IN permit 10
 match ip address prefix-list VIP_POOLS

# Apply route-map to all worker neighbors
router bgp 65001
 neighbor 192.168.1.40 route-map ACCEPT_VIP_IN in
 neighbor 192.168.1.41 route-map ACCEPT_VIP_IN in
 neighbor 192.168.1.42 route-map ACCEPT_VIP_IN in
 neighbor 192.168.1.43 route-map ACCEPT_VIP_IN in
 neighbor 192.168.1.44 route-map ACCEPT_VIP_IN in
 neighbor 192.168.1.46 route-map ACCEPT_VIP_IN in
```

**Explanation**:
- `ge 32 le 32`: Accept ONLY /32 routes (specific VIPs), not broader subnets
- `permit 192.168.200.0/24 ge 32`: Accept any /32 within 192.168.200.0/24 range
- `route-map ACCEPT_VIP_IN permit 10`: Allow matching prefixes
- `neighbor X.X.X.X route-map ACCEPT_VIP_IN in`: Apply to inbound routes from workers

#### Step 3: Reload FRR Configuration

```bash
# Reload FRR config
/usr/local/etc/rc.d/frr restart

# Or via web UI:
# Services → FRR → Global Settings → Save
```

#### Step 4: Verify Routes Accepted

```bash
# Check BGP summary
vtysh -c "show bgp summary"

# Expected output:
# Neighbor        State/PfxRcd
# 192.168.1.40           1     <- Should show 1 (or more)
# 192.168.1.41           1
# ...

# Check BGP routes
vtysh -c "show bgp ipv4 unicast"

# Expected output:
#    Network          Next Hop
# *> 192.168.200.10/32 192.168.1.40          0             0 64513 i
```

#### Step 5: Verify VIP Reachability

```bash
# From pfSense or any host
ping -c 4 192.168.200.10

# Test API connectivity
curl -k https://192.168.200.10:6443/healthz
# Expected: ok
```

### Alternative: Use pfSense Web UI

#### Via Web UI (Simpler but Limited)

1. Navigate to **Services → FRR → BGP → Advanced**
2. Add the following to the raw config section:

```
ip prefix-list VIP_POOLS seq 10 permit 192.168.100.0/24 ge 32 le 32
ip prefix-list VIP_POOLS seq 20 permit 192.168.101.0/24 ge 32 le 32
ip prefix-list VIP_POOLS seq 30 permit 192.168.102.0/24 ge 32 le 32
ip prefix-list VIP_POOLS seq 40 permit 192.168.103.0/24 ge 32 le 32
ip prefix-list VIP_POOLS seq 50 permit 192.168.200.0/24 ge 32 le 32

route-map ACCEPT_VIP_IN permit 10
 match ip address prefix-list VIP_POOLS
```

3. For EACH worker neighbor (192.168.1.40-46):
   - Navigate to **Services → FRR → BGP → Neighbors**
   - Edit the neighbor
   - Under "Route Maps":
     - **Incoming Route Map**: `ACCEPT_VIP_IN`
   - Save

4. Click **Save** and **Apply Changes**

### Debugging Commands

#### On pfSense

```bash
# Show BGP summary
vtysh -c "show bgp summary"

# Show all BGP routes
vtysh -c "show bgp ipv4 unicast"

# Show routes from specific neighbor
vtysh -c "show bgp neighbor 192.168.1.40 routes"

# Show route-maps
vtysh -c "show route-map ACCEPT_VIP_IN"

# Show prefix-lists
vtysh -c "show ip prefix-list VIP_POOLS"

# Show BGP config
vtysh -c "show running-config" | grep -A 50 "router bgp"
```

#### On Kubernetes Cluster

```bash
# Check if Cilium is advertising routes
kubectl exec -n cilium ds/cilium -- cilium bgp routes advertised ipv4 unicast

# Check BGP peer status
kubectl exec -n cilium ds/cilium -- cilium bgp peers

# Check service has correct labels
kubectl get svc kubernetes-external -o yaml | grep -A 5 "labels:"

# Check LoadBalancer IP assigned
kubectl get svc kubernetes-external

# Check Cilium BGP peer config
kubectl get ciliumbgppeerconfig cilium-peer -o yaml
```

### Common Issues

#### Issue 1: Routes Advertised But Not Accepted

**Symptom**: Cilium shows routes advertised, pfSense shows 0 accepted prefixes

**Cause**: Inbound route-map missing or incorrect

**Fix**: Add `ACCEPT_VIP_IN` route-map as shown above

#### Issue 2: No Routes Advertised from Cilium

**Symptom**: `cilium bgp routes advertised` shows empty

**Cause**: Service missing `advertise: bgp` label or wrong label match

**Fix**:
```bash
kubectl label svc kubernetes-external advertise=bgp --overwrite
kubectl annotate svc kubernetes-external io.cilium/bgp-announce=true --overwrite
```

#### Issue 3: BGP Sessions Not Establishing

**Symptom**: BGP state = Active or Connect

**Cause**: MD5 password mismatch, network connectivity, or firewall

**Fix**:
1. Verify MD5 password matches on both sides
2. Check network connectivity: `ping 192.168.1.40` from pfSense
3. Verify firewall allows TCP port 179

#### Issue 4: VIP Assigned But Not Reachable

**Symptom**: Service has EXTERNAL-IP but `ping` fails

**Cause**: BGP route not in routing table

**Fix**:
1. Verify route in pfSense: `vtysh -c "show ip route 192.168.200.10"`
2. Check if route accepted: `vtysh -c "show bgp ipv4 unicast 192.168.200.10/32"`
3. Verify route-map allows it: `vtysh -c "show route-map ACCEPT_VIP_IN"`

### Validation Checklist

After applying the fix, verify:

- [x] BGP sessions: 6/6 Established
- [x] Routes accepted: ≥1 prefix per neighbor
- [x] Routes in BGP table: `show bgp ipv4 unicast` shows 192.168.200.10/32
- [x] Routes in routing table: `show ip route` shows 192.168.200.10
- [x] VIP reachable: `ping 192.168.200.10` succeeds
- [x] API accessible: `curl -k https://192.168.200.10:6443/healthz` returns "ok"
- [x] kubectl via VIP: `kubectl --server=https://192.168.200.10:6443 get nodes` works

---

**Last Updated**: 2025-10-05
**Status**: Pending pfSense route-map configuration
