# Kaniko Multi-Architecture Workflows Guide

## Overview

This guide covers building multi-architecture (ARM64 + AMD64) container images using the dual-architecture Kaniko builder infrastructure on Talos Kubernetes. The infrastructure enables parallel native builds on architecture-specific runners, producing optimized multi-arch container images for GHCR.

### Purpose of Multi-Architecture Builds

Multi-architecture container images provide:
- **Native Performance**: Images run at full speed on both ARM64 and AMD64 hosts without emulation overhead
- **Platform Compatibility**: Single image tag works across diverse infrastructure (Apple Silicon, AWS Graviton, x86 servers)
- **Simplified Deployment**: `docker pull ghcr.io/org/image:latest` automatically selects the correct architecture
- **Future-Proofing**: Support for ARM64 adoption while maintaining x86 compatibility

### Benefits of Parallel Architecture Builds

- **Speed**: ARM64 and AMD64 builds run simultaneously, not sequentially
- **Efficiency**: Each architecture builds natively without cross-compilation or emulation
- **Resource Utilization**: Leverages separate runner pools (ARM64: 1-3 runners, AMD64: 1-5 runners)
- **Cost Optimization**: Native builds complete 2-10x faster than emulated builds

### Architecture Compatibility Matrix

| Build Architecture | Target Platforms | Use Cases |
|-------------------|------------------|-----------|
| ARM64 only | `linux/arm64` | AWS Graviton, Apple Silicon, Raspberry Pi |
| AMD64 only | `linux/amd64` | Traditional x86 servers, most cloud VMs |
| Multi-arch (ARM64 + AMD64) | `linux/arm64`, `linux/amd64` | Universal compatibility, cloud-agnostic deployments |

## Quick Start Examples

### Single-Architecture ARM64 Build

```yaml
name: Build ARM64 Image
on: push

jobs:
  build-arm64:
    runs-on: [self-hosted, linux, arm64, kaniko-build]

    steps:
      - uses: actions/checkout@v4

      - name: Build ARM64 Image
        run: |
          /kaniko/executor \
            --context . \
            --dockerfile Dockerfile \
            --destination ghcr.io/${{ github.repository }}:${{ github.sha }}-arm64 \
            --custom-platform linux/arm64
```

### Single-Architecture AMD64 Build

```yaml
name: Build AMD64 Image
on: push

jobs:
  build-amd64:
    runs-on: [self-hosted, linux, amd64, kaniko-build]

    steps:
      - uses: actions/checkout@v4

      - name: Build AMD64 Image
        run: |
          /kaniko/executor \
            --context . \
            --dockerfile Dockerfile \
            --destination ghcr.io/${{ github.repository }}:${{ github.sha }}-amd64 \
            --custom-platform linux/amd64
```

### Parallel Multi-Architecture Build

```yaml
name: Build Multi-Arch Image
on: push

jobs:
  build:
    strategy:
      matrix:
        arch: [arm64, amd64]

    runs-on: [self-hosted, linux, ${{ matrix.arch }}, kaniko-build]

    steps:
      - uses: actions/checkout@v4

      - name: Build ${{ matrix.arch }} Image
        run: |
          /kaniko/executor \
            --context . \
            --dockerfile Dockerfile \
            --destination ghcr.io/${{ github.repository }}:${{ github.sha }}-${{ matrix.arch }} \
            --custom-platform linux/${{ matrix.arch }}
```

### Multi-Architecture Manifest Creation

```yaml
name: Build and Push Multi-Arch Image
on: push

jobs:
  build:
    strategy:
      matrix:
        arch: [arm64, amd64]
    runs-on: [self-hosted, linux, ${{ matrix.arch }}, kaniko-build]

    steps:
      - uses: actions/checkout@v4

      - name: Build ${{ matrix.arch }} Image
        run: |
          /kaniko/executor \
            --context . \
            --dockerfile Dockerfile \
            --destination ghcr.io/${{ github.repository }}:${{ github.sha }}-${{ matrix.arch }} \
            --custom-platform linux/${{ matrix.arch }}

  manifest:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Create Multi-Arch Manifest
        run: |
          docker manifest create ghcr.io/${{ github.repository }}:${{ github.sha }} \
            ghcr.io/${{ github.repository }}:${{ github.sha }}-arm64 \
            ghcr.io/${{ github.repository }}:${{ github.sha }}-amd64

          docker manifest push ghcr.io/${{ github.repository }}:${{ github.sha }}
```

## Parallel Build Strategy

### GitHub Actions Matrix Strategy

The matrix strategy enables parallel execution of jobs with different parameters. For multi-arch builds:

```yaml
strategy:
  matrix:
    arch: [arm64, amd64]
  fail-fast: false  # Continue building other architectures if one fails
  max-parallel: 2    # Build both architectures simultaneously
```

**How it works**:
1. GitHub Actions spawns 2 parallel jobs (one per architecture)
2. Each job requests a runner with architecture-specific labels
3. Kubernetes autoscaler provisions runners on appropriate nodes
4. Builds execute simultaneously on native hardware

### Running ARM64 and AMD64 Builds Concurrently

**Runner Selection by Architecture**:
```yaml
runs-on: [self-hosted, linux, ${{ matrix.arch }}, kaniko-build]
```

This dynamically selects:
- ARM64 job: Runs on runners with `[self-hosted, linux, arm64, kaniko-build]` labels
- AMD64 job: Runs on runners with `[self-hosted, linux, amd64, kaniko-build]` labels

**Runner Pool Auto-Scaling**:
- **ARM64 Pool**: Scales 1-3 runners on nodes `apple`, `cherry`, `pecan`
- **AMD64 Pool**: Scales 1-5 runners on nodes `barrel`, `bushel`, `cobalt`
- **Scale-Up Threshold**: 75% busy triggers new runner
- **Scale-Up Time**: ~60 seconds to provision new runner

### Combining Artifacts into Multi-Arch Manifest

After parallel builds complete, combine into a single multi-arch image:

```yaml
manifest:
  needs: build  # Wait for all matrix jobs to complete
  runs-on: ubuntu-latest

  steps:
    - name: Create Multi-Arch Manifest
      run: |
        docker manifest create ghcr.io/org/image:latest \
          ghcr.io/org/image:latest-arm64 \
          ghcr.io/org/image:latest-amd64

        docker manifest push ghcr.io/org/image:latest
```

**Manifest Behavior**:
- Docker/containerd automatically selects the correct architecture when pulling
- `docker pull ghcr.io/org/image:latest` on ARM64 host → gets ARM64 image
- `docker pull ghcr.io/org/image:latest` on AMD64 host → gets AMD64 image

### Best Practices for Build Cache Sharing

**Option 1: Per-Architecture Cache (Current)**
```bash
/kaniko/executor \
  --cache=true \
  --cache-repo=ghcr.io/org/image/cache-${{ matrix.arch }} \
  --destination ghcr.io/org/image:${{ github.sha }}-${{ matrix.arch }}
```

**Benefits**: Architecture-specific cache layers, no cross-contamination

**Option 2: Shared Base Layer Cache (Future)**
```bash
/kaniko/executor \
  --cache=true \
  --cache-repo=ghcr.io/org/image/cache \
  --destination ghcr.io/org/image:${{ github.sha }}-${{ matrix.arch }}
```

**Benefits**: Shared base layers (OS packages) reduce storage, architecture-specific layers cached separately

**Cache Invalidation Strategy**:
- Cache expires after 7 days of inactivity
- New base image versions invalidate dependent layers
- Manual cache clear: Delete cache repository tags in GHCR

## Runner Selection

### How to Target Specific Architecture Runners

Use label-based runner selection in the `runs-on` field:

**ARM64 Runners**:
```yaml
runs-on: [self-hosted, linux, arm64, kaniko-build]
```

**AMD64 Runners**:
```yaml
runs-on: [self-hosted, linux, amd64, kaniko-build]
```

**Dynamic Selection (Matrix)**:
```yaml
runs-on: [self-hosted, linux, ${{ matrix.arch }}, kaniko-build]
```

### Label-Based Runner Selection

**Available Label Sets**:

| Label Set | Runner Pool | Nodes | Max Runners |
|-----------|-------------|-------|-------------|
| `[self-hosted, linux, arm64, kaniko-build]` | ARM64 Kaniko | apple, cherry, pecan | 3 |
| `[self-hosted, linux, amd64, kaniko-build]` | AMD64 Kaniko | barrel, bushel, cobalt | 5 |

**Label Meanings**:
- `self-hosted`: Custom runner (not GitHub-hosted)
- `linux`: Operating system
- `arm64`/`amd64`: CPU architecture
- `kaniko-build`: Runner has Kaniko executor installed
- `talos`: Talos Kubernetes cluster
- `homelab`: Physical homelab infrastructure
- `native-build`: Native architecture builds (no emulation)

### Workflow Syntax for runs-on

**Single Architecture**:
```yaml
jobs:
  build:
    runs-on: [self-hosted, linux, arm64, kaniko-build]
```

**Matrix-Based Multi-Architecture**:
```yaml
jobs:
  build:
    strategy:
      matrix:
        arch: [arm64, amd64]
    runs-on: [self-hosted, linux, ${{ matrix.arch }}, kaniko-build]
```

**Fallback to GitHub-Hosted (for manifest creation)**:
```yaml
jobs:
  manifest:
    runs-on: ubuntu-latest  # Use GitHub-hosted runner for manifest creation
```

## Kaniko Build Examples

### Basic Kaniko Executor Command

```bash
/kaniko/executor \
  --context . \
  --dockerfile Dockerfile \
  --destination ghcr.io/org/image:tag \
  --custom-platform linux/arm64
```

**Parameters**:
- `--context`: Build context directory (`.` for repo root)
- `--dockerfile`: Path to Dockerfile (default: `./Dockerfile`)
- `--destination`: Target registry and tag
- `--custom-platform`: Target platform (required for accurate manifest metadata)

### GHCR Authentication

**Credentials are auto-mounted** into Kaniko runners at `/kaniko/.docker/config.json`:

```yaml
env:
  - name: DOCKER_CONFIG
    value: /kaniko/.docker

volumeMounts:
  - name: kaniko-secret
    mountPath: /kaniko/.docker
    readOnly: true

volumes:
  - name: kaniko-secret
    secret:
      secretName: ghcr-pull-secret
      items:
        - key: .dockerconfigjson
          path: config.json
```

**No workflow configuration required** - authentication is automatic.

**Verify credentials** (for debugging):
```bash
- name: Verify Credentials
  run: cat /kaniko/.docker/config.json
```

### Custom Platform Specification

**Always specify `--custom-platform`** to ensure correct manifest metadata:

```bash
# ARM64 Build
/kaniko/executor \
  --custom-platform linux/arm64 \
  --destination ghcr.io/org/image:arm64

# AMD64 Build
/kaniko/executor \
  --custom-platform linux/amd64 \
  --destination ghcr.io/org/image:amd64
```

**Without `--custom-platform`**: Kaniko detects runner architecture automatically, but manifest metadata may be incorrect.

### Build Caching Strategies

**Option 1: Registry-Based Cache (Recommended)**:
```bash
/kaniko/executor \
  --cache=true \
  --cache-repo=ghcr.io/org/image/cache \
  --destination ghcr.io/org/image:tag
```

**Option 2: Local Cache (Ephemeral)**:
```bash
/kaniko/executor \
  --cache=true \
  --cache-dir=/kaniko/cache \
  --destination ghcr.io/org/image:tag
```

**Cache Performance**:
- First build (cold cache): 10-15 minutes
- Cached build (warm cache): 1-3 minutes
- Cache hit ratio: 70-90% for typical application builds

### Multi-Stage Builds

Multi-stage Dockerfiles work natively with Kaniko:

```dockerfile
# Stage 1: Build
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /app/server

# Stage 2: Runtime
FROM alpine:3.19
COPY --from=builder /app/server /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/server"]
```

**Kaniko automatically optimizes**:
- Intermediate stages cached separately
- Only final stage pushed to registry (unless `--cache=true`)
- Cross-stage dependencies tracked

## Multi-Arch Manifest Creation

### Using docker manifest create

**Step 1: Build Architecture-Specific Images**:
```bash
# Already completed by parallel Kaniko builds
# ghcr.io/org/image:sha-arm64
# ghcr.io/org/image:sha-amd64
```

**Step 2: Create Manifest List**:
```bash
docker manifest create ghcr.io/org/image:latest \
  ghcr.io/org/image:sha-arm64 \
  ghcr.io/org/image:sha-amd64
```

**Step 3: Annotate Platforms** (optional, usually auto-detected):
```bash
docker manifest annotate ghcr.io/org/image:latest \
  ghcr.io/org/image:sha-arm64 \
  --os linux --arch arm64

docker manifest annotate ghcr.io/org/image:latest \
  ghcr.io/org/image:sha-amd64 \
  --os linux --arch amd64
```

**Step 4: Push Manifest**:
```bash
docker manifest push ghcr.io/org/image:latest
```

### Using docker buildx imagetools

**Alternative method** (requires Docker Buildx):

```bash
docker buildx imagetools create \
  --tag ghcr.io/org/image:latest \
  ghcr.io/org/image:sha-arm64 \
  ghcr.io/org/image:sha-amd64
```

**Benefits**:
- Single command (no separate annotate step)
- Automatically detects platform metadata from source images
- Preferred for CI/CD automation

### Manifest Inspection and Validation

**Inspect manifest**:
```bash
docker manifest inspect ghcr.io/org/image:latest
```

**Expected output**:
```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
  "manifests": [
    {
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "digest": "sha256:abc123...",
      "size": 1234,
      "platform": {
        "architecture": "arm64",
        "os": "linux"
      }
    },
    {
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "digest": "sha256:def456...",
      "size": 1235,
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      }
    }
  ]
}
```

**Validation checks**:
- Both architectures present in manifest
- Correct platform metadata (`linux/arm64`, `linux/amd64`)
- Unique digests for each architecture
- Manifest list media type correct

### Pushing Manifests to GHCR

**Authentication required**:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

**Push manifest**:
```bash
docker manifest push ghcr.io/org/image:latest
```

**Push additional tags** (e.g., version tags):
```bash
docker manifest create ghcr.io/org/image:v1.2.3 \
  ghcr.io/org/image:sha-arm64 \
  ghcr.io/org/image:sha-amd64

docker manifest push ghcr.io/org/image:v1.2.3
```

## Complete Workflow Example

```yaml
name: Build and Push Multi-Arch Image

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    name: Build ${{ matrix.arch }} Image
    strategy:
      matrix:
        arch: [arm64, amd64]
      fail-fast: false
      max-parallel: 2

    runs-on: [self-hosted, linux, ${{ matrix.arch }}, kaniko-build]

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set Image Tag
        id: meta
        run: |
          echo "tag=${{ github.sha }}-${{ matrix.arch }}" >> $GITHUB_OUTPUT
          echo "cache_tag=cache-${{ matrix.arch }}" >> $GITHUB_OUTPUT

      - name: Build ${{ matrix.arch }} Image with Kaniko
        run: |
          /kaniko/executor \
            --context . \
            --dockerfile Dockerfile \
            --destination ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.tag }} \
            --custom-platform linux/${{ matrix.arch }} \
            --cache=true \
            --cache-repo=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/${{ steps.meta.outputs.cache_tag }} \
            --compressed-caching=false \
            --snapshot-mode=redo \
            --use-new-run

      - name: Verify Image
        run: |
          echo "Image pushed: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.tag }}"

  manifest:
    name: Create Multi-Arch Manifest
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    permissions:
      contents: read
      packages: write

    steps:
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Create Multi-Arch Manifest
        run: |
          docker buildx imagetools create \
            --tag ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest \
            --tag ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-arm64 \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-amd64

      - name: Inspect Manifest
        run: |
          docker buildx imagetools inspect ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

      - name: Verify Multi-Arch Support
        run: |
          manifest=$(docker manifest inspect ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest)

          if echo "$manifest" | grep -q '"architecture": "arm64"'; then
            echo "✓ ARM64 image present"
          else
            echo "✗ ARM64 image missing" && exit 1
          fi

          if echo "$manifest" | grep -q '"architecture": "amd64"'; then
            echo "✓ AMD64 image present"
          else
            echo "✗ AMD64 image missing" && exit 1
          fi

          echo "Multi-arch manifest validation passed!"
```

## Troubleshooting

### Runner Not Available

**Symptoms**:
- Workflow stuck in "Queued" state
- Message: "Waiting for a runner to pick up this job"

**Diagnosis**:
```bash
# Check runner availability
kubectl get pods -n actions-runner-system -l app.kubernetes.io/part-of=github-cicd

# Check autoscaler status
kubectl get hra -n actions-runner-system

# Check node resources
kubectl top nodes
```

**Common Causes**:
1. **No runners in pool**: Autoscaler hasn't scaled up yet (wait 60 seconds)
2. **All runners busy**: Increase `maxReplicas` in autoscaler
3. **Node resource exhaustion**: Add more worker nodes or reduce resource requests
4. **Wrong labels**: Verify `runs-on` labels match available runners

**Resolution**:
```bash
# Manually scale up (temporary)
kubectl scale runnerdeployment thomaswimprine-kaniko-builders-arm64 --replicas=3 -n actions-runner-system

# Increase max replicas (permanent)
kubectl patch hra thomaswimprine-kaniko-builders-arm64-autoscaler \
  -n actions-runner-system \
  --type merge \
  -p '{"spec":{"maxReplicas":5}}'
```

### Authentication Failures

**Symptoms**:
- Kaniko error: "UNAUTHORIZED: authentication required"
- Kaniko error: "DENIED: permission denied"

**Diagnosis**:
```bash
# Verify secret exists
kubectl get secret ghcr-pull-secret -n actions-runner-system

# Check secret content
kubectl get secret ghcr-pull-secret -n actions-runner-system -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq

# Verify RBAC permissions
kubectl auth can-i get secret/ghcr-pull-secret \
  --as=system:serviceaccount:actions-runner-system:kaniko-builder-arm64 \
  -n actions-runner-system
```

**Common Causes**:
1. **Expired GitHub PAT**: Token expired (90-day lifetime)
2. **Insufficient PAT scopes**: Missing `write:packages` or `read:packages`
3. **RBAC misconfiguration**: ServiceAccount can't access secret
4. **Wrong secret format**: Not `kubernetes.io/dockerconfigjson` type

**Resolution**:
```bash
# Rotate GitHub PAT
kubectl delete secret ghcr-pull-secret -n actions-runner-system

kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<GITHUB_USERNAME> \
  --docker-password=<NEW_GITHUB_PAT> \
  --namespace=actions-runner-system

# Restart runners to pick up new secret
kubectl rollout restart runnerdeployment thomaswimprine-kaniko-builders-arm64 -n actions-runner-system
kubectl rollout restart runnerdeployment thomaswimprine-kaniko-builders-amd64 -n actions-runner-system
```

### Platform Mismatch Errors

**Symptoms**:
- Warning: "platform mismatch: image is linux/arm64 but requested linux/amd64"
- Multi-arch manifest contains duplicate architectures

**Diagnosis**:
```bash
# Inspect image manifest
docker manifest inspect ghcr.io/org/image:tag-arm64

# Check platform metadata
docker buildx imagetools inspect ghcr.io/org/image:tag-arm64
```

**Common Causes**:
1. **Missing `--custom-platform`**: Kaniko auto-detected wrong platform
2. **Wrong runner architecture**: Build ran on wrong runner (label mismatch)
3. **Cross-compilation artifacts**: Base image built for different architecture

**Resolution**:
```bash
# Always specify --custom-platform in Kaniko
/kaniko/executor \
  --custom-platform linux/${{ matrix.arch }} \
  --destination ghcr.io/org/image:${{ github.sha }}-${{ matrix.arch }}

# Verify runner labels are correct
kubectl get runnerdeployment thomaswimprine-kaniko-builders-arm64 \
  -n actions-runner-system \
  -o jsonpath='{.spec.template.spec.labels}'
```

### Manifest Creation Failures

**Symptoms**:
- Error: "manifest list does not exist"
- Error: "no such manifest: ghcr.io/org/image:tag"

**Diagnosis**:
```bash
# Verify source images exist
docker manifest inspect ghcr.io/org/image:sha-arm64
docker manifest inspect ghcr.io/org/image:sha-amd64

# Check GHCR authentication
docker login ghcr.io
```

**Common Causes**:
1. **Source images not pushed**: Build job failed or incomplete
2. **Authentication required**: Not logged into GHCR
3. **Network issues**: Intermittent registry connectivity
4. **Typo in image tags**: Source image names don't match

**Resolution**:
```bash
# Verify all source images present
for arch in arm64 amd64; do
  echo "Checking $arch image..."
  docker manifest inspect ghcr.io/org/image:${{ github.sha }}-$arch || echo "Missing $arch image!"
done

# Re-authenticate to GHCR
echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin

# Retry manifest creation
docker buildx imagetools create \
  --tag ghcr.io/org/image:latest \
  ghcr.io/org/image:${{ github.sha }}-arm64 \
  ghcr.io/org/image:${{ github.sha }}-amd64
```

## Additional Resources

- **Kaniko Documentation**: https://github.com/GoogleContainerTools/kaniko
- **Docker Manifest Spec**: https://docs.docker.com/engine/reference/commandline/manifest/
- **GHCR Documentation**: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- **Kaniko Builder Guide**: `kubernetes/github-cicd/KANIKO-BUILDER-GUIDE.md`
- **Example Workflow**: `.github/workflows/example-multi-arch-build.yml`

## Support

- **GitHub Issues**: https://github.com/ThomasWimprine/AWS_Infrastructure/issues
- **PRP Documentation**: `prp/active/004-b-002-amd64-kaniko-builder-20251024.md`
