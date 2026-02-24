# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**wzzrd.ghdl** is an Ansible collection that automates downloading and installing binary releases from GitHub repositories. It handles cross-platform binary selection, archive extraction, checksum verification, and installation with minimal user configuration.

**Core functionality:** Query GitHub API → Match binary to architecture → Download → Verify checksum → Extract (if archive) → Install

**Key integration point:** The `wzzrd.ghdl.filter_binaries` custom Ansible filter plugin (`plugins/filter/filter_binaries.py`) is central to binary selection logic.

## Architecture

### Task Flow (roles/downloader/tasks/)

Input validation is handled by `meta/argument_specs.yml` before any tasks run — there is no `preflight.yml`.

1. **select_binary.yml** - Constructs architecture matcher, validates it exists and is non-empty, queries GitHub API (delegated to localhost with `run_once`), finds checksum file URL, filters assets to get download URL
2. **prepare_checksum.yml** - Downloads checksum file to localhost, parses it to extract hash for the specific binary
3. **main.yml** - Orchestrates: creates temp dir on localhost → includes above tasks → downloads binary to localhost with checksum verification → routes to handler
4. **handle_archive.yml** - Extracts archive on localhost (zip/tar variants), finds executable files by permission bits, fails clearly if none found, copies from localhost to target install dir
5. **handle_binary.yml** - Handles plain binaries (uses `downloader_binary_name` if set, otherwise strips platform suffix with fallback to project name), copies from localhost to target install dir

### Performance Optimization

The role is optimized for multi-host deployments with mixed architectures:

- **GitHub API calls**: Delegated to localhost with `run_once: true` — fetched once regardless of number of hosts
- **Architecture-specific shared storage**: Creates a base temp directory once, then architecture-specific subdirectories (e.g., `linux_x86_64`, `linux_aarch64`)
- **Download deduplication**: Each host checks if its architecture's binary already exists before downloading
  - First x86_64 host: downloads to shared directory
  - Subsequent x86_64 hosts: see binary exists, skip download
  - First aarch64 host: downloads its binary to a different subdirectory
  - Subsequent aarch64 hosts: see binary exists, skip download
- **Extraction deduplication**: Archives are only extracted once per architecture using a `.extracted` marker file
- **Target-side work**: Only the final `copy` task runs on the target host
- **Cleanup**: Base temp directory deleted once after all hosts complete (in `always` block)

**Example**: Deploying to 5 x86_64 hosts and 3 aarch64 hosts results in exactly 2 downloads, not 8.

### Binary Selection Logic

The architecture detection builds a variable name dynamically:
```
downloader_matchers_{{ ansible_system | lower }}_{{ ansible_architecture }}
```

This references lists in `defaults/main.yml`:
- `downloader_matchers_linux_x86_64` - `x86_64-unknown-linux-musl`, `x86_64-unknown-linux-gnu`, `linux_amd64`, `x86_64-linux`, `linux-amd64`, `linux_x86_64`
- `downloader_matchers_linux_aarch64` - `aarch64-unknown-linux-musl`, `aarch64-unknown-linux-gnu`, `linux_arm64`, `aarch64-linux`, `linux-arm64`
- `downloader_matchers_darwin_arm64` - empty by default; must be defined to use macOS targets

The filter plugin (`filter_binaries.py`) receives GitHub API release data and matcher list, then:
1. Validates inputs (dict, list)
2. Checks for `json` key, then `assets` key — separate error messages for each
3. Extracts all `browser_download_url` from assets
4. Filters URLs containing any matcher substring
5. Excludes package formats: `sha256`, `-update`, `apk`, `android`, `rpm`, `deb`, `zst`, `exe`
6. Deprioritizes variant binaries (`-server`, `-daemon`, `-cli`, `-agent`) so the main binary is returned first
7. Returns first match or raises `AnsibleFilterError` with full diagnostic info

### Archive vs Binary Handling

Route determined by regex in `vars/main.yml`:
```
downloader_archive_regex: .*\.(zip|tar|tar\.gz|tgz|tar\.bz2|tar\.xz|bz2)$
```

- **Archives**: Extract all, find executable files by permission bits (`[157]$`), fail with clear message if none found, install with `downloader_binary_name | default(downloader_project)`
- **Plain binaries**: If `downloader_binary_name` is set, use it; otherwise strip platform suffix using regex `[._-].*`; if that returns empty string, fallback to `downloader_project`

Example: `chezmoi-darwin-arm64` → strips to `chezmoi`
Edge case: `starship` (no separator) → regex returns empty → fallback to `downloader_project`

### Checksum Verification

Optional security feature (degrades gracefully):
1. Search release assets for files matching `.*(SHA256SUMS|sha256sum|checksums\.txt|CHECKSUMS|checksum).*`
2. Download checksum file to temp directory (deduplicated per architecture)
3. Parse for line containing binary filename, extract hash by splitting on whitespace and taking first field
4. **Format assumption**: expects `<hash>  <filename>` — reversed formats (`<filename> <hash>`) will not work
5. Pass `checksum: "sha256:{{ hash }}"` to `get_url` module
6. If no checksum found, warn and proceed without verification

All checksum-related variables are explicitly reset at the start of `prepare_checksum.yml` to prevent values from one architecture's run leaking into the next.

## Testing

### Unit Tests (pytest)

```bash
pip install -r tests/requirements.txt
pytest tests/unit/ -v
```

Test file: `tests/unit/plugins/filter/test_filter_binaries.py`

Covers: matcher logic, package format exclusion, variant deprioritization, all error paths (invalid inputs, missing keys, no matches).

### Molecule Integration Tests

```bash
GITHUB_PAT="your_token_here" molecule test
```

Test scenario location: `extensions/molecule/default/`
- **converge.yml** - Installs starship v1.21.1
- **molecule.yml** - Podman driver, UBI9 and UBI10 platforms
- **verify.yml** - Checks binary exists and is executable
- **prepare.yml** - Installs tar, gzip, bzip2, xz on test containers

### Building the Collection

```bash
ansible-galaxy collection build
```

Produces: `wzzrd-ghdl-2.0.0.tar.gz`

### Installing Locally for Testing

```bash
ansible-galaxy collection install ./wzzrd-ghdl-2.0.0.tar.gz --force
```

## Critical Implementation Details

### Input Validation
Required variable validation (`downloader_organization`, `downloader_project`, `downloader_github_token`) is handled by `meta/argument_specs.yml`, which runs before any tasks. Do not add a manual `preflight.yml` — the argument specs provide better error messages and type checking.

### GitHub Token Security
- ALL tasks using `downloader_github_token` MUST have `no_log: true` — this includes both the latest-release and versioned API calls in `select_binary.yml`
- Token is required to avoid API rate limiting (60 req/hour unauthenticated vs 5000/hour authenticated)
- Never log full API responses that might contain the token in headers

### Binary Naming Override
`downloader_binary_name` exists for projects where binary name ≠ project name:
- Example: Project `ripgrep` → binary `rg`
- NOT for renaming convenience (e.g., terraform → tf)
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
- **Why per-host (no run_once)**: Each architecture needs different binaries
- **localhost operations**: API calls, downloads, checksum parsing, archive extraction, temp directory management
- **Target operations**: Only the final `copy` task runs on target to install the binary

When modifying tasks, maintain this delegation pattern. Only tasks that must write to the target's install directory should run on the target.

### macOS Controller Support
When the Ansible controller runs on macOS, the role automatically uses GNU tar (`gtar`) instead of BSD tar:
- **Requirement**: `brew install gnu-tar`
- **Automatic detection**: checks `hostvars['localhost'].ansible_os_family == 'Darwin'` and sets `TAR` environment variable to `gtar`

## Variables Reference

**Required** (enforced by argument_specs.yml):
- `downloader_organization` - GitHub org (e.g., `"hashicorp"`)
- `downloader_project` - Repo name (e.g., `"terraform"`)
- `downloader_github_token` - GitHub PAT for API access

**Optional with defaults:**
- `downloader_version` - Specific version tag (default: latest release)
- `downloader_install_dir` - Install path (default: `/usr/local/bin`)
- `downloader_binary_name` - Override binary name
- `downloader_binary_owner` / `_group` - File ownership (default: `root`/`root`)
- `downloader_debug` - Enable verbose output (default: `false`)

## Debug Output

When `downloader_debug: true`, the following is printed at each stage:
- `select_binary.yml`: all available asset names, selected download URL, checksum file URL
- `prepare_checksum.yml`: binary filename being searched, matched checksum line, final checksum string
- `handle_archive.yml`: archive tool used (tar/gtar), all files extracted, executable files found
- `handle_binary.yml`: resolved source filename and final install path
- `main.yml`: temp directory paths, cache hit/miss per binary

## Known Tested Projects

Semi-regularly verified with:
- restic, dust, lsd, starship, direnv, chezmoi, resticprofile, zoxide, atuin, jq, duf

When adding features, test against projects with different binary naming conventions and archive formats. `duf` is useful for testing the `linux_x86_64` matcher pattern specifically.

## File Selection Logic Edge Cases

1. **Multiple executables in archive**: Takes first found — intentional behavior
2. **No executables in archive**: Fails with a clear error message pointing to `downloader_debug`
3. **Plain binary with no separator** (e.g., `starship`): Regex returns empty, fallback to `downloader_project`
4. **Checksum file exists but binary not listed**: Warns and skips verification
5. **Version specified but tag doesn't exist**: GitHub API returns 404, role fails cleanly
6. **Empty darwin_arm64 matchers**: Fails with validation message, not undefined variable error

## Adding New Architecture Support

To support a new platform:

1. Add matcher list to `roles/downloader/defaults/main.yml`:
   ```yaml
   downloader_matchers_{{ os }}_{{ arch }}:
     - pattern1
     - pattern2
   ```

2. Add it to `meta/argument_specs.yml` so it's documented and overridable

3. Update validation message in `select_binary.yml` to list the new architecture

4. Test with `downloader_debug: true` to verify matchers work

5. Consider if new package formats need exclusion in `filter_binaries.py` `drop_matchers`

No changes needed to core task logic — architecture detection is fully dynamic.
