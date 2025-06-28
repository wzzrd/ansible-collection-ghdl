# wzzrd.ghdl

An Ansible role for downloading and installing binary releases from GitHub repositories. This role automatically detects your system architecture, downloads the appropriate binary from GitHub releases, and installs it to your system.

## Features

- **Cross-platform support**: Automatically detects Linux x86_64, aarch64, and Darwin ARM64 architectures
- **Flexible binary matching**: Uses configurable matchers to find the right binary for your system
- **Archive handling**: Supports multiple archive formats (zip, tar, tar.gz, tgz, tar.bz2, tar.xz, bz2)
- **Version flexibility**: Download latest release or specify a particular version
- **GitHub API integration**: Uses GitHub's API for reliable release information
- **Clean installation**: Handles extraction, installation, and cleanup automatically

## Requirements

- Ansible 2.9 or higher
- GitHub Personal Access Token (PAT) for API access
- Internet connectivity to GitHub

## Role Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `downloader_organization` | GitHub organization name | `"hashicorp"` |
| `downloader_project` | GitHub project/repository name | `"terraform"` |
| `downloader_github_token` | GitHub Personal Access Token | `"ghp_xxxxxxxxxxxx"` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `downloader_version` | `undefined` | Specific version to download (e.g., "v1.0.0"). If undefined, downloads latest release |
| `downloader_install_dir` | `/usr/local/bin` | Directory to install the binary |
| `downloader_binary_name` | `{{ downloader_project }}` | Name for the installed binary |
| `downloader_binary_owner` | `root` | Owner of the installed binary |
| `downloader_binary_group` | `root` | Group of the installed binary |
| `downloader_debug` | `false` | Enable debug output |

### Architecture Matchers

The role includes predefined matchers for different architectures:

**Linux x86_64:**
- `x86_64-unknown-linux-musl`
- `x86_64-unknown-linux-gnu`
- `linux_amd64`
- `x86_64-linux`
- `linux-amd64`
- `linux_amd64`

**Linux aarch64:**
- `aarch64-unknown-linux-musl`
- `aarch64-unknown-linux-gnu`
- `linux_arm64`
- `aarch64-linux`
- `linux-arm64`
- `linux_arm64`

**Darwin ARM64:**
- Currently empty (can be extended as needed)

## Functional tests

This role is semi-regularly tested with the following organizations / projects:

- "restic/restic/restic"
- "bootandy/dust/"
- "lsd-rs/lsd/"
- "starship/starship/"
- "direnv/direnv/"
- "twpayne/chezmoi/"
- "creativeprojects/resticprofile/"
- "ajeetdsouza/zoxide/"
- "atuinsh/atuin/"
- "jqlang/jq/"

## GitHub Personal Access Token

**Important**: This role requires a GitHub Personal Access Token (PAT) to function properly. The GitHub API limits unauthenticated requests to 60 per hour, which may not be sufficient for larger deployments.

### Creating a GitHub PAT

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token"
3. Select appropriate scopes (for public repositories, no additional scopes are needed)
4. Copy the generated token

### Setting the Token

You can set the token in several ways:

**Via group_vars or host_vars:**
```yaml
downloader_github_token: "ghp_your_token_here"
```

**Via ansible-vault (recommended):**
```yaml
# In group_vars/all/vault.yml (encrypted)
vault_github_token: "ghp_your_token_here"

# In group_vars/all/vars.yml
downloader_github_token: "{{ vault_github_token }}"
```

**Via environment variable:**
```bash
export GITHUB_TOKEN="ghp_your_token_here"
# Then reference in playbook:
downloader_github_token: "{{ ansible_env.GITHUB_TOKEN }}"
```

## Example Playbook

### Basic Usage

```yaml
---
- hosts: servers
  become: yes
  roles:
    - role: wzzrd.ghdl
      vars:
        downloader_organization: "hashicorp"
        downloader_project: "terraform"
        downloader_github_token: "{{ vault_github_token }}"
```

### Install Specific Version

```yaml
---
- hosts: servers
  become: yes
  roles:
    - role: wzzrd.ghdl
      vars:
        downloader_organization: "kubernetes"
        downloader_project: "kubectl"
        downloader_version: "v1.28.0"
        downloader_github_token: "{{ vault_github_token }}"
```

### Custom Installation Directory

```yaml
---
- hosts: servers
  become: yes
  roles:
    - role: wzzrd.ghdl
      vars:
        downloader_organization: "cli"
        downloader_project: "cli"
        downloader_install_dir: "/opt/bin"
        downloader_binary_name: "gh"
        downloader_github_token: "{{ vault_github_token }}"
```

### Multiple Tools Installation

```yaml
---
- hosts: servers
  become: yes
  tasks:
    - name: Install Terraform
      include_role:
        name: wzzrd.ghdl
      vars:
        downloader_organization: "hashicorp"
        downloader_project: "terraform"
        downloader_github_token: "{{ vault_github_token }}"

    - name: Install kubectl
      include_role:
        name: wzzrd.ghdl
      vars:
        downloader_organization: "kubernetes"
        downloader_project: "kubectl"
        downloader_github_token: "{{ vault_github_token }}"

    - name: Install helm
      include_role:
        name: wzzrd.ghdl
      vars:
        downloader_organization: "helm"
        downloader_project: "helm"
        downloader_github_token: "{{ vault_github_token }}"
```

## How It Works

1. **Preflight Checks**: Validates that required variables are set
2. **Binary Selection**: Determines the appropriate binary based on system architecture
3. **GitHub API Query**: Fetches release information from GitHub API
4. **Binary Matching**: Uses the `wzzrd.ghdl.filter_binaries` filter to find matching binaries
5. **Download**: Downloads the selected binary/archive to a temporary directory
6. **Extraction**: If the download is an archive, extracts it and finds executable files
7. **Installation**: Copies the binary to the specified installation directory with correct permissions
8. **Cleanup**: Removes temporary files

## Supported Archive Formats

- ZIP (`.zip`)
- TAR (`.tar`)
- Gzipped TAR (`.tar.gz`, `.tgz`)
- Bzip2 TAR (`.tar.bz2`)
- XZ TAR (`.tar.xz`)
- Plain Bzip2 (`.bz2`)

## Troubleshooting

### Debug Mode

Enable debug output to troubleshoot issues:

```yaml
downloader_debug: true
```

### Common Issues

**API Rate Limiting**: Ensure your GitHub token is properly set and has sufficient permissions.

**No matching binary found**: Check if the release contains binaries for your architecture. You may need to extend the architecture matchers.

**Permission denied**: Ensure the role runs with appropriate privileges (typically `become: yes`).

**Binary not executable**: The role automatically sets executable permissions (`0755`) on installed binaries.

## Dependencies

This role includes a custom filter plugin (`wzzrd.ghdl.filter_binaries`) that handles binary selection based on architecture matchers.

## License

BSD-3-Clause

## Author Information

Maxim Burgerhout <maxim@wzzrd.com>
