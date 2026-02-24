# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**wzzrd.ghdl** is an Ansible collection that automates downloading and installing binary releases from GitHub repositories. It handles cross-platform binary selection, archive extraction, and installation with minimal user configuration.

**Core functionality:** Query GitHub API → Match binary to architecture → Download → Extract (if archive) → Install → Verify checksum

**Key integration point:** The `wzzrd.ghdl.filter_binaries` custom Ansible filter plugin (`plugins/filter/filter_binaries.py`) is central to binary selection logic.

## Architecture

### Task Flow (roles/downloader/tasks/)

1. **preflight.yml** - Validates required variables (`downloader_organization`, `downloader_project`, `downloader_github_token`)
2. **select_binary.yml** - Constructs architecture matcher, queries GitHub API (delegated to localhost with `run_once`), finds checksum file, filters assets to get download URL
3. **prepare_checksum.yml** - Downloads checksum file to localhost, parses it to extract hash for the specific binary
4. **main.yml** - Orchestrates: creates temp dir on localhost → includes above tasks → downloads binary to localhost with checksum verification → routes to handler
5. **handle_archive.yml** - Extracts archive on localhost (zip/tar variants), finds executable, copies from localhost to target install dir
6. **handle_binary.yml** - Handles plain binaries (uses `downloader_binary_name` if set, otherwise strips platform suffix with fallback to project name), copies from localhost to target install dir

### Performance Optimization

The role is optimized for multi-host deployments with mixed architectures:

- **GitHub API calls**: Delegated to localhost with `run_once: true` - fetched once regardless of number of hosts
- **Architecture-specific shared storage**: Creates a base temp directory once, then architecture-specific subdirectories (e.g., `linux_x86_64`, `linux_aarch64`)
- **Download deduplication**: Each host checks if its architecture's binary already exists before downloading
  - First x86_64 host: downloads to shared directory
  - Subsequent x86_64 hosts: see binary exists, skip download
  - First aarch64 host: downloads its binary to a different subdirectory
  - Subsequent aarch64 hosts: see binary exists, skip download
- **Extraction deduplication**: Archives are only extracted once per architecture using file existence checks
- **Target-side work**: Only the final file copy runs on the target host, minimizing network transfers and target resource usage
- **Cleanup**: Base temp directory deleted once after all hosts complete

**Example**: Deploying to 5 x86_64 hosts and 3 aarch64 hosts results in exactly 2 downloads (one per architecture), not 8.

### Binary Selection Logic

The architecture detection builds a variable name dynamically:
```
downloader_matchers_{{ ansible_system | lower }}_{{ ansible_architecture }}
```

This references lists in `defaults/main.yml`:
- `downloader_matchers_linux_x86_64` - patterns like `x86_64-unknown-linux-musl`, `linux_amd64`, `x86_64-linux`, `linux-amd64`, `linux_x86_64`
- `downloader_matchers_linux_aarch64` - patterns like `aarch64-unknown-linux-musl`, `linux_arm64`, `aarch64-linux`, `linux-arm64`
- `downloader_matchers_darwin_arm64` - Darwin/macOS patterns (currently empty)

The filter plugin (`filter_binaries.py`) receives GitHub API release data and matcher list, then:
1. Extracts all `browser_download_url` from assets
2. Filters URLs containing any matcher substring
3. Excludes package formats: `sha256`, `-update`, `apk`, `rpm`, `deb`, `zst`, `exe`
4. Returns first match or raises `AnsibleFilterError` with diagnostic info

### Archive vs Binary Handling

Route determined by regex in `vars/main.yml`:
```
downloader_archive_regex: .*\.(zip|tar|tar\.gz|tgz|tar\.bz2|tar\.xz|bz2)$
```

- **Archives**: Extract all, find executable files by permission bits, install with `downloader_binary_name | default(downloader_project)`
- **Plain binaries**: If `downloader_binary_name` is set, use it; otherwise strip platform suffix using regex `[._-].*`, and if that results in empty string, fallback to `downloader_project`

Example: `chezmoi-darwin-arm64` → regex strips to `chezmoi` → install as `chezmoi`
Edge case: `starship` (no separator) → regex returns empty → fallback to `downloader_project`

### Checksum Verification

Optional security feature (degrades gracefully):
1. Search release assets for files matching `.*(SHA256SUMS|sha256sum|checksums\.txt|CHECKSUMS|checksum).*`
2. Download checksum file to temp directory
3. Parse for line containing binary filename, extract hash by splitting line and taking first field
4. Pass `checksum: "sha256:{{ hash }}"` to `get_url` module
5. If no checksum found, warn and proceed without verification

## Testing

### Molecule Tests

Run integration tests with molecule (requires Docker/Podman):

```bash
cd roles/downloader
GITHUB_PAT="your_token_here" molecule test
```

Test scenario location: `roles/downloader/molecule/default/`
- **converge.yml** - Test playbook (currently tests starship v1.21.1 installation)
- **molecule.yml** - Scenario configuration
- **verify.yml** - Post-installation validation

The test disables full fact gathering and only collects architecture facts for performance.

### Building the Collection

```bash
ansible-galaxy collection build
```

Produces: `wzzrd-ghdl-1.1.0.tar.gz`

### Installing Locally for Testing

```bash
ansible-galaxy collection install ./wzzrd-ghdl-1.1.0.tar.gz --force
```

## Critical Implementation Details

### GitHub Token Security
- ALL tasks using `downloader_github_token` MUST have `no_log: true`
- Token is required to avoid API rate limiting (60 req/hour unauthenticated vs 5000/hour authenticated)
- Never log full API responses that might contain token in headers

### Binary Naming Override
`downloader_binary_name` exists for projects where binary name ≠ project name:
- Example: Project `ripgrep` → binary `rg`
- NOT for renaming (e.g., terraform → tf)
- Used consistently by both `handle_archive.yml` and `handle_binary.yml`

### Architecture Validation
Fail early with clear message if:
1. Matcher variable doesn't exist (`matcher not in vars`)
2. Matcher list is empty (`vars[matcher] | length == 0`)

Error message must list supported architectures and show how to extend.

### Filter Plugin Error Messages
When no binary matches, `AnsibleFilterError` must include:
- Matchers that were tried
- All available asset filenames
- Assets after matcher filtering
- Assets after package format exclusion

This diagnostic output is critical for users debugging unsupported projects.

### Task Delegation Strategy
Most tasks are delegated to localhost with `become: false` for performance:
- **Why delegate**: Reduces load on target hosts, faster downloads from control node, enables efficient multi-host deployments
- **Why per-host (no run_once)**: Each architecture needs different binaries (x86_64 vs aarch64)
- **localhost operations**: API calls, downloads, checksum parsing, archive extraction, temp directory management
- **Target operations**: Only the final `copy` task runs on target to install the binary

Important: When modifying tasks, maintain this delegation pattern. Only tasks that must write to the target's install directory should run on the target.

### macOS Controller Support
When the Ansible controller runs on macOS, the role automatically uses GNU tar (`gtar`) instead of BSD tar for archive extraction:
- **Requirement**: Install GNU tar via Homebrew: `brew install gnu-tar`
- **Why**: GNU tar has better compatibility with certain archive formats created on Linux
- **Automatic detection**: The role checks `ansible_os_family == 'Darwin'` and switches to `gtar` automatically

## Variables Reference

**Required:**
- `downloader_organization` - GitHub org (e.g., "hashicorp")
- `downloader_project` - Repo name (e.g., "terraform")
- `downloader_github_token` - GitHub PAT for API access

**Optional with defaults:**
- `downloader_version` - Specific version tag (default: latest release)
- `downloader_install_dir` - Install path (default: `/usr/local/bin`)
- `downloader_binary_name` - Override binary name (default: `downloader_project`)
- `downloader_binary_owner` / `_group` - File ownership (default: `root`/`root`)
- `downloader_debug` - Enable verbose output (default: `false`)

## Known Tested Projects

Semi-regularly verified with:
- restic, dust, lsd, starship, direnv, chezmoi, resticprofile, zoxide, atuin, jq, duf

When adding features, test against projects with different binary naming conventions and archive formats.

## File Selection Logic Edge Cases

1. **Multiple executables in archive**: Currently takes first found; intentional behavior
2. **Plain binary with no separator** (e.g., just `starship`): Regex returns empty string, fallback to `downloader_project` applies
3. **Checksum file exists but binary not listed**: Warns and skips verification
4. **Version specified but tag doesn't exist**: GitHub API returns 404, role fails cleanly
5. **Empty darwin_arm64 matchers**: Fails with validation message, not undefined variable error

## Adding New Architecture Support

To support new platform (e.g., Windows, FreeBSD):

1. Add matcher list to `roles/downloader/defaults/main.yml`:
   ```yaml
   downloader_matchers_{{ os }}_{{ arch }}:
     - pattern1
     - pattern2
   ```

2. Update validation message in `select_binary.yml` to list new architecture

3. Test with `downloader_debug: true` to see asset names and verify matchers work

4. Consider if new package formats need exclusion in `filter_binaries.py` drop_matchers

No changes needed to core task logic; architecture detection is fully dynamic.
