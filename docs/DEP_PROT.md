# Dependency Management Protocol

## Overview
This document outlines the dependency management strategy for the Mycosoft MAS project, ensuring reproducible builds, conflict-free dependencies, and automated updates.

## Core Principles

1. **Immutable, Isolated Builds**
   - All dependencies are pinned to specific versions
   - Build environments are reproducible
   - Rollbacks are possible at any time

2. **Semantic Versioning**
   - Direct dependencies are pinned
   - Minor version updates are allowed after passing tests
   - Major version updates require explicit approval

3. **Automated Conflict Detection**
   - CI pipeline checks for dependency conflicts
   - Security vulnerabilities are automatically detected
   - SBOM (Software Bill of Materials) is maintained

4. **Zero-Downtime Updates**
   - Blue/green deployment strategy
   - Rolling updates for containerized services
   - Automated testing before deployment

## Workflow

### Development
1. Add new dependencies to `requirements.in` or `pyproject.toml`
2. Run `pip-compile` to generate `requirements.txt`
3. Run `poetry lock` to update Poetry lock file
4. Test changes locally with `tox`

### CI/CD
1. GitHub Actions automatically:
   - Runs tests across Python versions
   - Checks for dependency conflicts
   - Performs security audits
   - Updates SBOM
   - Commits dependency updates

### Deployment
1. Container images are built from pinned dependencies
2. Rolling updates are performed in Kubernetes
3. Health checks ensure service availability

## Version Control

### Python Version Support
- Currently supported: 3.9, 3.10, 3.11
- EOL (End of Life) versions are dropped after 6 months of EOL date

### Dependency Updates
- Minor version updates: Automated through Dependabot
- Major version updates: Require PR review and approval
- Security updates: Automatically applied if tests pass

## Tools

### Primary Tools
- Poetry: Primary dependency management
- pip-tools: For pip-based requirements
- tox: Multi-environment testing
- pip-audit: Security scanning
- pipdeptree: Conflict detection

### CI/CD Tools
- GitHub Actions: CI/CD pipeline
- Dependabot: Automated updates
- CodeQL: Security scanning
- cyclonedx-py: SBOM generation

## Governance

### Approval Process
1. Minor updates: Automated if tests pass
2. Major updates: Requires team review
3. Security updates: Automated with rollback capability

### Documentation
- All dependency decisions are documented in this file
- Changelog is automatically generated from commit messages
- SBOM is maintained and updated automatically

## Emergency Procedures

### Rollback Process
1. Revert dependency changes in version control
2. Rebuild and redeploy affected services
3. Verify system health

### Security Incidents
1. Immediate security updates are applied
2. Affected services are redeployed
3. Incident is documented and reviewed

## Maintenance

### Regular Tasks
- Weekly dependency updates
- Monthly security audits
- Quarterly major version reviews
- Annual Python version review

### Monitoring
- Dependency conflicts are monitored
- Security vulnerabilities are tracked
- Update success rates are measured 