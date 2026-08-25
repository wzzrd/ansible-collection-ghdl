# wzzrd.ghdl

An Ansible collection that automates downloading and installing binary releases
from GitHub repositories. It handles cross-platform binary selection, archive
extraction, checksum verification, and installation with minimal configuration.

The primary repository is hosted privately on Gitea. The GitHub repository at
[github.com/wzzrd/ansible-collection-ghdl](https://github.com/wzzrd/ansible-collection-ghdl)
is a read-only mirror. See [Contributing](#contributing) for details.

## Contents

- [`wzzrd.ghdl.downloader`](#role-wzzrdghdldownloader) — the main role

## Requirements

- Ansible 2.16.11 or higher
- A GitHub Personal Access Token (PAT) — required to avoid the 60 req/hour
  unauthenticated API rate limit
- **macOS controllers only**: GNU tar (`brew install gnu-tar`) — the role
  automatically uses `gtar` instead of BSD tar when running on macOS

## Installation

```bash
ansible-galaxy collection install wzzrd.ghdl
```

## Role: wzzrd.ghdl.downloader

### How it works

1. Queries the GitHub API for the latest release (or a pinned version)
2. Matches release assets against architecture-specific patterns to find the
   right binary
3. Downloads the binary (or archive) to the Ansible controller
4. Verifies the download against a SHA256 checksum if one is available in the
   release
5. Extracts archives on the controller, finds the executable inside
6. Copies the binary to the target host's install directory

All download and extraction work happens on the Ansible controller. When
deploying to multiple hosts, the role downloads each architecture's binary
exactly once regardless of how many hosts need it — five x86_64 hosts and
three aarch64 hosts result in two downloads, not eight.

### Variables

#### Required

| Variable | Description | Example |
|---|---|---|
| `downloader_organization` | GitHub organization or user | `"hashicorp"` |
| `downloader_project` | Repository name | `"terraform"` |
| `downloader_github_token` | GitHub Personal Access Token | `"ghp_xxxx"` |

#### Optional

| Variable | Default | Description |
|---|---|---|
| `downloader_version` | latest release | Specific release tag, e.g. `"v1.0.0"` |
| `downloader_install_dir` | `/usr/local/bin` | Directory to install the binary |
| `downloader_libc` | `musl` | Preferred C library flavour: `musl`, `gnu` or `any`. See [libc preference](#libc-preference) |
| `downloader_variant` | unset | Select a specific build when a release ships several, e.g. `"server"` for `atuin-server-x86_64-unknown-linux-musl.tar.gz` |
| `downloader_binary_name` | derived from release asset name | Override the installed filename. Use when the binary name differs from the project name, e.g. project `ripgrep` installs as `rg` |
| `downloader_binary_owner` | `root` | Owner of the installed binary |
| `downloader_binary_group` | `root` | Group of the installed binary |
| `downloader_debug` | `false` | Print verbose output: available assets, selected URL, checksum details, extracted files |

### libc preference

Many projects publish both a musl and a glibc build of the same binary. The
role prefers the **musl** build by default, because those are statically linked
and carry no glibc version requirement — they run on older targets that would
reject a glibc build with `GLIBC_2.xx not found`.

```yaml
downloader_libc: musl # default
```

| Value | Behaviour |
|---|---|
| `musl` | Prefer musl builds, then assets naming no libc, then glibc builds |
| `gnu` | Prefer glibc builds, then assets naming no libc, then musl builds |
| `any` | Ignore libc flavour entirely; selection falls to matcher order |

Assets that name no libc at all — most Go releases, e.g. `terraform_1.5.0_linux_amd64.zip` —
are unaffected by this setting.

**When to choose `gnu`:** musl implements no NSS — it never reads
`/etc/nsswitch.conf`. It resolves users and groups by parsing `/etc/passwd` and
`/etc/group` directly, so **local users always resolve normally**. What a musl
build cannot see is an identity that exists *only* in a directory backend:
sssd, LDAP, Active Directory, winbind, or nss-systemd `DynamicUser`. On a
domain-joined host, tools that map UIDs to names (`lsd -l`, `dust`, `duf`) will
print numeric IDs for those users instead of names.

Note this is a property of musl, not of static linking — a dynamically linked
musl build behaves the same way.

Hostname resolution is largely unaffected: musl reads `/etc/hosts` and queries
DNS from `/etc/resolv.conf` with its own resolver. What is lost is NSS host
backends such as `nss-myhostname`, `nss-resolve` and mDNS. musl's resolver also
differs from glibc's in its handling of `search`/`ndots`, and lacked TCP
fallback for responses over 512 bytes before musl 1.2.4.

If any of that applies, set `downloader_libc: gnu` for that tool:

```yaml
- name: Install lsd with glibc so LDAP usernames resolve
  ansible.builtin.include_role:
    name: wzzrd.ghdl.downloader
  vars:
    downloader_organization: lsd-rs
    downloader_project: lsd
    downloader_libc: gnu
```

### Architecture matchers

The role selects the right binary by matching release asset filenames against a
list of substrings. Each supported platform has its own matcher list.

**Order matters**: when several assets match, the one matching the earliest
entry in the list wins. `downloader_libc` is applied first, so matcher order
decides only between assets of the same libc flavour.

**Linux x86_64** (`downloader_matchers_linux_x86_64`):
```yaml
- x86_64-unknown-linux-musl
- x86_64-unknown-linux-gnu
- linux_amd64
- x86_64-linux
- linux-amd64
- linux_x86_64
```

**Linux aarch64** (`downloader_matchers_linux_aarch64`):
```yaml
- aarch64-unknown-linux-musl
- aarch64-unknown-linux-gnu
- linux_arm64
- aarch64-linux
- linux-arm64
```

**Darwin ARM64** (`downloader_matchers_darwin_arm64`): empty by default.
Define it in your playbook or inventory to enable macOS target support:
```yaml
downloader_matchers_darwin_arm64:
  - darwin-arm64
  - darwin_arm64
  - macos-arm64
  - aarch64-apple-darwin
```

You can override any matcher list or add a new one for an unsupported
architecture by defining the appropriate variable:
```yaml
downloader_matchers_{{ ansible_system | lower }}_{{ ansible_architecture }}:
  - pattern1
  - pattern2
```

### Checksum verification

When a release includes a checksum file (`SHA256SUMS`, `sha256sum`,
`checksums.txt`, `CHECKSUMS`, or similar), the role downloads it and verifies
the binary's SHA256 hash automatically. If no checksum file is found, the
download proceeds with a warning.

### Supported archive formats

`.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tar.xz`, `.bz2`

Plain binaries (no archive extension) are handled directly.

### Examples

#### Install the latest release

```yaml
- hosts: servers
  become: true
  roles:
    - role: wzzrd.ghdl.downloader
      vars:
        downloader_organization: hashicorp
        downloader_project: terraform
        downloader_github_token: "{{ vault_github_token }}"
```

#### Pin to a specific version

```yaml
- hosts: servers
  become: true
  roles:
    - role: wzzrd.ghdl.downloader
      vars:
        downloader_organization: starship-rs
        downloader_project: starship
        downloader_version: v1.21.1
        downloader_github_token: "{{ vault_github_token }}"
```

#### Override the binary name

Use `downloader_binary_name` when the binary name in the release archive
differs from what you want installed, or differs from the project name.

```yaml
- hosts: servers
  become: true
  roles:
    - role: wzzrd.ghdl.downloader
      vars:
        downloader_organization: BurntSushi
        downloader_project: ripgrep
        downloader_binary_name: rg
        downloader_github_token: "{{ vault_github_token }}"
```

#### Install multiple tools

```yaml
- hosts: servers
  become: true
  tasks:
    - name: Install restic
      ansible.builtin.include_role:
        name: wzzrd.ghdl.downloader
      vars:
        downloader_organization: restic
        downloader_project: restic
        downloader_github_token: "{{ vault_github_token }}"

    - name: Install zoxide
      ansible.builtin.include_role:
        name: wzzrd.ghdl.downloader
      vars:
        downloader_organization: ajeetdsouza
        downloader_project: zoxide
        downloader_github_token: "{{ vault_github_token }}"

    - name: Install jq
      ansible.builtin.include_role:
        name: wzzrd.ghdl.downloader
      vars:
        downloader_organization: jqlang
        downloader_project: jq
        downloader_github_token: "{{ vault_github_token }}"
```

#### Custom install directory and non-root ownership

```yaml
- hosts: servers
  roles:
    - role: wzzrd.ghdl.downloader
      vars:
        downloader_organization: direnv
        downloader_project: direnv
        downloader_install_dir: /home/myuser/.local/bin
        downloader_binary_owner: myuser
        downloader_binary_group: myuser
        downloader_github_token: "{{ vault_github_token }}"
```

### GitHub token

The token only needs to authenticate — no scopes are required for public
repositories. Create one at GitHub → Settings → Developer settings →
Personal access tokens.

Store it securely with Ansible Vault:

```yaml
# group_vars/all/vault.yml (encrypted)
vault_github_token: "ghp_your_token_here"

# group_vars/all/vars.yml
downloader_github_token: "{{ vault_github_token }}"
```

### Troubleshooting

Enable debug output to see which assets are available, which URL was selected,
and what was found inside an archive:

```yaml
downloader_debug: true
```

**No matching binary found**: The error message lists all available asset names
and which matchers were tried. Either the project uses an unusual naming
convention or your architecture needs additional matcher patterns.

**Unsupported architecture**: The role fails immediately with a clear message
listing supported architectures and showing how to add your own matcher list.

**macOS controller, extraction fails**: Install GNU tar with
`brew install gnu-tar`. The role detects macOS and uses `gtar` automatically,
but it must be installed first.

### Tested projects

Semi-regularly verified against:

| Organization | Project | Notes |
|---|---|---|
| `restic` | `restic` | |
| `bootandy` | `dust` | |
| `lsd-rs` | `lsd` | |
| `starship-rs` | `starship` | used in integration tests |
| `direnv` | `direnv` | |
| `twpayne` | `chezmoi` | |
| `creativeprojects` | `resticprofile` | |
| `ajeetdsouza` | `zoxide` | |
| `atuinsh` | `atuin` | |
| `jqlang` | `jq` | |
| `muesli` | `duf` | tests the `linux_x86_64` matcher pattern |

## Contributing

The primary repository is hosted privately on Gitea and is not open to outside
access. The GitHub repository is a read-only mirror kept in sync automatically.

If you want to contribute, open a pull request against the GitHub mirror at
[github.com/wzzrd/ansible-collection-ghdl](https://github.com/wzzrd/ansible-collection-ghdl).
PRs there will be reviewed and applied manually upstream — they won't be merged
via GitHub's merge button, and GitHub CI will not run on them. Once a
contribution is applied, the mirror will update automatically and the PR will
be closed with a reference to the upstream commit.

## License

GPL-3.0-or-later

## Author

Maxim Burgerhout &lt;maxim@wzzrd.com&gt;
