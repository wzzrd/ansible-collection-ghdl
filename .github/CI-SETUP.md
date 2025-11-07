# CI/CD Pipeline Setup Guide

This document explains how to set up and use the CI/CD pipeline for this Ansible collection on both GitHub Actions and Gitea with act_runner.

## Pipeline Overview

The pipeline runs three types of tests:

1. **Linting** - ansible-lint for code quality (installed via pipx)
2. **Unit Tests** - pytest for filter plugin tests
3. **Integration Tests** - Molecule tests for roles (currently starship)

After all tests pass on the main branch, it automatically tags releases based on the version in `galaxy.yml`.

### Why node:18-bookworm Container?

The **lint** and **pytest** jobs run inside a `node:18-bookworm` container. This approach:

- ✅ Works on both x86_64 and ARM64 architectures (no setup-python issues)
- ✅ Provides a consistent environment on GitHub Actions and Gitea act_runner
- ✅ Includes Python 3.11 pre-installed
- ✅ Allows installing pipx via apt (native package manager)
- ✅ Matches your proven `lint_and_merge.yml` pattern

**Note:** The **molecule** job does NOT use a container because it needs to manage containers itself (for testing). It runs directly on the ubuntu-latest runner and installs dependencies via apt.

### Why pipx?

The workflow uses **pipx** instead of pip to install ansible-core and ansible-lint. This approach:

- ✅ Creates isolated environments for each tool (no dependency conflicts)
- ✅ Installed via apt (native Debian package)
- ✅ Uses `pipx inject` to add ansible-lint to the ansible-core environment
- ✅ More reliable than pip for system-wide tool installation

### Version Configuration

All tool versions are configurable via repository variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANSIBLE_CORE_VERSION` | `2.16.13` | ansible-core version |
| `ANSIBLE_LINT_VERSION` | `24.9.2` | ansible-lint version |
| `PYTHON_VERSION` | `3.11` | Python interpreter version |
| `CI_CONTAINER_ENGINE` | `podman` | Container engine (podman/docker) |

To override, set these as repository or organization variables in GitHub/Gitea.

### Job Architecture Summary

| Job | Runs In | Python Setup | Why? |
|-----|---------|--------------|------|
| **lint** | `node:18-bookworm` container | Pre-installed (3.11) | Consistent across architectures, avoids setup-python issues |
| **pytest** | `node:18-bookworm` container | Pre-installed (3.11) | Same benefits as lint job |
| **molecule** | `ubuntu-latest` runner | Installed via apt | Needs to manage containers, can't run in container |
| **tag-release** | `ubuntu-latest` runner | Not needed | Only runs shell commands |

### Ansible Galaxy Server Configuration

The workflow supports custom Ansible Galaxy servers (useful for private/enterprise Galaxy instances). Configure via repository variables/secrets:

**Variables:**
- `ANSIBLE_GALAXY_SERVER_LIST` - Comma-separated list of server names
- `ANSIBLE_GALAXY_SERVER_RH_CERTIFIED_URL` - Red Hat Certified server URL
- `ANSIBLE_GALAXY_SERVER_VALIDATED_URL` - Validated content server URL
- `ANSIBLE_GALAXY_SERVER_UPSTREAM_URL` - Upstream server URL
- `ANSIBLE_GALAXY_SERVER_COMMUNITY_URL` - Community server URL
- `ANSIBLE_GALAXY_SERVER_LOCAL_URL` - Local/private server URL

**Secrets:**
- `ANSIBLE_GALAXY_SERVER_RH_CERTIFIED_TOKEN` - Auth token for RH Certified
- `ANSIBLE_GALAXY_SERVER_VALIDATED_TOKEN` - Auth token for Validated
- `ANSIBLE_GALAXY_SERVER_UPSTREAM_TOKEN` - Auth token for Upstream
- `ANSIBLE_GALAXY_SERVER_COMMUNITY_TOKEN` - Auth token for Community
- `ANSIBLE_GALAXY_SERVER_LOCAL_TOKEN` - Auth token for Local

If these are not set, the workflow uses the default public Ansible Galaxy server.

## Container Engine Support

The pipeline is designed to work with both **Podman** and **Docker**, with automatic detection and configuration.

### Default Behavior

- **GitHub Actions**: Uses Podman (installed if needed)
- **Gitea act_runner**: Auto-detects available engine (Podman preferred, Docker fallback)

### How It Works

1. The workflow checks for the `CI_CONTAINER_ENGINE` variable (Gitea organization/repository variable)
2. If not set or set to `auto`, it detects which engine is available
3. For GitHub Actions, it installs Podman if selected
4. For Gitea, it uses whatever is available on the runner

## GitHub Actions Setup

No additional configuration needed! The pipeline will:

1. Install Podman on Ubuntu runners
2. Configure the Podman socket for rootless operation
3. Run all tests with Podman

## Gitea Setup

### Option 1: Use Podman on Gitea (Recommended)

If your Gitea act_runner has Podman installed:

1. Set a repository or organization variable:
   - Name: `CI_CONTAINER_ENGINE`
   - Value: `podman`

2. Ensure your runner has:
   ```bash
   # Install podman
   sudo apt-get install podman

   # Enable podman socket for the runner user
   systemctl --user enable --now podman.socket
   ```

### Option 2: Use Docker on Gitea

If your Gitea act_runner uses Docker:

1. Set a repository or organization variable:
   - Name: `CI_CONTAINER_ENGINE`
   - Value: `docker`

2. Ensure the runner has Docker installed and the runner user has permissions:
   ```bash
   sudo usermod -aG docker <runner-user>
   ```

### Option 3: Auto-detect (Default)

Don't set the `CI_CONTAINER_ENGINE` variable, and the pipeline will:

1. Check if `podman` command exists → use Podman
2. Otherwise check if `docker` command exists → use Docker
3. Fail if neither is available

## Testing Locally

### Option 1: Using Container (Recommended - Matches CI)

```bash
# Pull the container image
docker pull node:18-bookworm
# or
podman pull node:18-bookworm

# Run tests in container
docker run -it --rm -v $(pwd):/workspace -w /workspace node:18-bookworm bash

# Inside container:
apt update && apt -y install pipx git
export PIPX_HOME=/root/.local/pipx
pipx install ansible-core==2.16.13
pipx inject --include-apps ansible-core ansible-lint==24.9.2
ansible-lint -v
```

### Option 2: Native Installation

```bash
# Install pipx via apt (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install pipx
pipx ensurepath

# Or via pip (macOS/other)
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install ansible-core
pipx install ansible-core==2.16.13

# Install ansible-lint
pipx inject --include-apps ansible-core ansible-lint==24.9.2

# Install molecule for integration tests
pipx inject ansible-core molecule
pipx inject ansible-core "molecule-plugins[podman]"

# Install pytest dependencies
pip3 install -r tests/requirements.txt

# Install container engine (for molecule tests)
sudo apt-get install podman  # Debian/Ubuntu
# or
brew install podman           # macOS
# or use docker
```

### Run Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Molecule Tests

```bash
cd roles/starship
molecule test

# Or with specific driver
molecule test --driver-name podman
molecule test --driver-name docker
```

### Run Linting

```bash
# Run ansible-lint on entire collection
ansible-lint -v

# Run on specific files
ansible-lint roles/starship/tasks/main.yml
```

Configuration is in `.ansible-lint` at the repository root.

## Troubleshooting

### Python setup fails with ARM64 architecture error

**Issue**: `actions/setup-python@v5` fails with "Version '3.11' with architecture 'arm64' was not found"

**Solution**: ✅ Fixed! The workflow now uses `node:18-bookworm` container which includes Python and works on all architectures. No `setup-python` action needed.

### Ansible-lint fails in container

**Issue**: ansible-lint can't find files or has permission issues

**Solution**:
```bash
# Ensure checkout happened before running in container
# The workflow uses container: image: node:18-bookworm at job level
# Checkout action runs inside the container automatically

# If running manually, mount the workspace:
docker run -v $(pwd):/workspace -w /workspace node:18-bookworm bash
```

### pipx command not found in container

**Issue**: `pipx: command not found` in the container

**Solution**:
```bash
# Install pipx via apt (included in workflow)
apt update && apt -y install pipx

# Set PIPX_HOME for consistent location
export PIPX_HOME=/root/.local/pipx
```

### pip install fails with externally-managed-environment

**Issue**: `error: externally-managed-environment` when using pip in Debian bookworm

**Solution**: The workflow uses `--break-system-packages` flag:
```bash
pip3 install -r tests/requirements.txt --break-system-packages
```

Or use pipx for isolated installations:
```bash
pipx install package-name
```

### Container can't be pulled

**Issue**: `docker pull node:18-bookworm` fails

**Solution**:
1. Check internet connectivity
2. For Gitea act_runner, ensure Docker/Podman has access to Docker Hub
3. Or configure a local registry mirror

### Podman socket issues on GitHub Actions

If you see connection errors to the Podman socket:

- The workflow automatically starts the socket with `systemctl --user enable --now podman.socket`
- It sets `DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock`

### Molecule can't find container engine

Error: `Failed to create container`

**Solution**: Check that:
1. Container engine (Podman/Docker) is installed
2. The user running the tests has permissions
3. For Podman: the socket is running (`systemctl --user status podman.socket`)

### Gitea runner doesn't have Podman

Error: `Neither podman nor docker found`

**Solution**: Either:
1. Install Podman on the runner
2. Install Docker on the runner
3. Set `CI_CONTAINER_ENGINE=docker` if Docker is available

### Different behavior on GitHub vs Gitea

The workflow detects the platform:

- GitHub: Identified by `github.server_url` not containing 'gitea'
- Gitea: Identified by `github.server_url` containing 'gitea'

On GitHub, it will install Podman. On Gitea, it assumes the engine is already available.

## Adding More Roles to Test

To add a new role to the Molecule test matrix:

1. Create molecule tests for your role:
   ```bash
   cd roles/your-role
   molecule init scenario -d podman
   ```

2. Update `.github/workflows/tests-and-tag.yml`:
   ```yaml
   strategy:
     matrix:
       role:
         - starship
         - your-role  # Add here
   ```

## Environment Variables Reference

### User-Configurable Variables

Set these in your GitHub/Gitea repository or organization settings:

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANSIBLE_CORE_VERSION` | ansible-core version to install | `2.16.13` |
| `ANSIBLE_LINT_VERSION` | ansible-lint version to install | `24.9.2` |
| `PYTHON_VERSION` | Python interpreter version | `3.11` |
| `CI_CONTAINER_ENGINE` | Container engine (podman/docker/auto) | `podman` |
| `ANSIBLE_GALAXY_SERVER_LIST` | Custom Galaxy servers (comma-separated) | _(empty)_ |
| `ANSIBLE_GALAXY_SERVER_*_URL` | URLs for custom Galaxy servers | _(empty)_ |

### User-Configurable Secrets

Set these in your GitHub/Gitea secrets:

| Secret | Purpose |
|--------|---------|
| `ANSIBLE_GALAXY_SERVER_*_TOKEN` | Authentication tokens for custom Galaxy servers |

### Workflow-Managed Variables

These are set automatically by the workflow:

| Variable | Purpose | Set By |
|----------|---------|--------|
| `DOCKER_HOST` | Podman socket path | Workflow (when using Podman) |
| `PYTHONPATH` | Python module search path | Workflow (pytest job) |
| `ANSIBLE_FORCE_COLOR` | Enable colored output | Workflow (molecule job) |
| `PY_COLORS` | Enable Python colored output | Workflow (molecule job) |

## GitHub Actions vs Gitea act_runner Compatibility

This workflow is designed to be fully compatible with both:

- Uses standard GitHub Actions syntax (act_runner supports this)
- Avoids GitHub-specific features not in act_runner
- Uses conditional logic to handle platform differences
- Environment variables work the same way in both

### Known Limitations

1. The `actions/cache@v5` for pip works better on GitHub than Gitea
2. Some GitHub Actions might not have Gitea equivalents (but all actions used here do)
3. Secrets and variables are configured differently in each platform's UI

## Performance Optimizations

The workflow includes several optimizations:

1. **Pip caching**: Speeds up Python dependency installation
2. **Parallel jobs**: Lint, pytest, and molecule run concurrently
3. **Matrix strategy**: Can easily scale to test multiple roles
4. **Fail-fast: false**: All role tests run even if one fails (for visibility)
5. **Minimal fact gathering**: Molecule tests only gather required facts

## Release Process

When you want to release a new version:

1. Update the `version:` field in `galaxy.yml`
2. Commit and push to the `main` branch
3. The workflow will:
   - Run all tests
   - Create a git tag (e.g., `v1.1.0`)
   - Trigger the release workflow
4. The release workflow publishes to Ansible Galaxy

Tags are only created on the `main` branch to prevent accidental releases from feature branches.
