# CI/CD Pipeline Documentation

## Overview

This repository uses GitHub Actions for continuous integration and deployment of Terraform infrastructure. The pipeline enforces security scanning, quality gates, and multi-environment deployment strategies.

## Workflows

### 1. Terraform CI (Pull Request Validation)

**Trigger:** Pull requests to main branch
**File:** `.github/workflows/terraform-ci.yml`

**Jobs:**
1. **terraform-validation**
   - Terraform format check
   - Terraform init and validate
   - TFLint static analysis
   - PR comment with results

2. **security-scanning**
   - Checkov (IaC security)
   - tfsec (Terraform security)
   - Semgrep (pattern analysis)

3. **terraform-plan**
   - Generate Terraform plan
   - Comment plan on PR

**Quality Gates:**
- All validation checks must pass
- Zero critical security issues
- Terraform plan must complete successfully

### 2. Security Scanning (Continuous Monitoring)

**Trigger:** Push to main/develop, PRs, weekly schedule
**File:** `.github/workflows/security-scan.yml`

**Jobs:**
1. **secret-detection**
   - TruffleHog for secret scanning
   - Prevents credential leakage

2. **infrastructure-security**
   - Checkov with SARIF output
   - tfsec vulnerability scanning
   - Results uploaded to GitHub Security

3. **dependency-scanning**
   - Trivy filesystem scanning
   - Dependency vulnerability detection

4. **compliance-check**
   - NIST 800-53 compliance validation
   - CIS AWS Foundations Benchmark

### 3. Terraform CD (Deployment)

**Trigger:** Push to main, manual workflow dispatch
**File:** `.github/workflows/terraform-cd.yml`

**Environments:**
1. **Development**
   - Auto-deploy on main branch push
   - No manual approval required
   - AWS role: `AWS_DEV_DEPLOY_ROLE_ARN`

2. **Staging**
   - Requires dev deployment success
   - Auto-deploy after dev
   - AWS role: `AWS_STAGING_DEPLOY_ROLE_ARN`

3. **Production**
   - Manual workflow dispatch only
   - Requires staging deployment success
   - Manual approval via GitHub environment
   - AWS role: `AWS_PROD_DEPLOY_ROLE_ARN`

## AWS IAM Roles

Each environment requires an IAM role for OIDC authentication:

```hcl
# Example trust policy for GitHub Actions
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:ORG/REPO:*"
        }
      }
    }
  ]
}
```

## Required Secrets

Configure in GitHub repository settings:

- `AWS_DEV_DEPLOY_ROLE_ARN`: Development deployment role ARN
- `AWS_STAGING_DEPLOY_ROLE_ARN`: Staging deployment role ARN
- `AWS_PROD_DEPLOY_ROLE_ARN`: Production deployment role ARN

## Branch Protection Rules

**Main Branch:**
- Require pull request reviews (minimum 2)
- Require status checks to pass:
  - Terraform Validation
  - Security Scanning
  - Terraform Plan
- Require conversation resolution
- Include administrators in restrictions

## Security Features

1. **Multi-Layer Scanning**
   - Checkov: Infrastructure as Code security
   - tfsec: Terraform-specific vulnerabilities
   - Semgrep: Custom security patterns
   - TruffleHog: Secret detection
   - Trivy: Dependency vulnerabilities

2. **Compliance Validation**
   - NIST 800-53 controls
   - CIS AWS Foundations Benchmark
   - Automated compliance reporting

3. **OIDC Authentication**
   - No long-lived credentials
   - Temporary session tokens
   - Role-based access control

## Quality Gates

**Pull Request Gates:**
- ✅ Terraform format check
- ✅ Terraform validation
- ✅ Security scan (zero critical issues)
- ✅ Terraform plan generation

**Deployment Gates:**
- ✅ All PR gates passed
- ✅ Main branch only
- ✅ Environment-specific approval (prod only)
- ✅ Successful upstream environment deployment

## Deployment Process

### Automatic Deployment (Dev/Staging)
```bash
# 1. Create feature branch
git checkout -b feature/my-infrastructure-change

# 2. Make changes and commit
git add terraform/
git commit -m "feat: add new VPC configuration"

# 3. Push and create PR
git push origin feature/my-infrastructure-change

# 4. Merge PR to main
# → Triggers automatic deployment to dev
# → After dev success, deploys to staging
```

### Manual Deployment (Production)
```bash
# Via GitHub UI:
# 1. Navigate to Actions → Terraform CD
# 2. Click "Run workflow"
# 3. Select "prod" environment
# 4. Approve deployment via environment protection
```

## Monitoring and Alerts

**GitHub Security Tab:**
- Security scan results (SARIF format)
- Dependency vulnerabilities
- Secret scanning alerts

**Workflow Status:**
- Commit status checks
- PR comments with validation results
- Deployment summaries in job summaries

## Rollback Procedures

### Rollback via Git Revert
```bash
# 1. Identify problematic commit
git log --oneline

# 2. Revert the commit
git revert <commit-hash>

# 3. Push to main
git push origin main
# → Triggers automatic deployment with reverted state
```

### Manual Rollback
```bash
# 1. Checkout previous working state
git checkout <previous-commit>

# 2. Create rollback branch
git checkout -b rollback/revert-to-<commit-hash>

# 3. Push and create PR
git push origin rollback/revert-to-<commit-hash>

# 4. Merge PR for automated rollback deployment
```

## Troubleshooting

### Pipeline Failures

**Terraform Validation Failed:**
```bash
# Run locally
cd terraform/
terraform fmt -recursive
terraform validate
```

**Security Scan Failed:**
```bash
# Run Checkov locally
checkov -d terraform/

# Run tfsec locally
tfsec terraform/
```

**Plan Failed:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Run plan locally
cd terraform/
terraform init
terraform plan
```

### Common Issues

1. **OIDC Authentication Failure**
   - Verify IAM role trust policy
   - Check repository name in condition
   - Confirm role ARN in secrets

2. **Security Scan Failures**
   - Review Checkov/tfsec output
   - Suppress false positives with inline comments
   - Fix actual vulnerabilities before merge

3. **Plan Failures**
   - Check Terraform syntax
   - Verify AWS permissions
   - Review state file consistency

## Best Practices

1. **Small, Incremental Changes**
   - Keep PRs focused and small
   - Test changes in dev first
   - Review security scan results

2. **Security First**
   - Never commit secrets
   - Fix security issues before merge
   - Use least privilege IAM roles

3. **Documentation**
   - Update docs with infrastructure changes
   - Document deployment procedures
   - Maintain runbooks for incidents

4. **Testing**
   - Test in dev environment first
   - Validate in staging before prod
   - Monitor deployments closely

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
- [NIST 800-53 Controls](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)
