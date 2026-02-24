# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.3] - 2026-02-24

### Tests
- Add black testing for plugins and tests

## [2.0.2] - 2026-02-24

### Fixed
- Redo workflow to not depend on tag push

## [2.0.1] - 2026-02-24

### Fixed
- Retrigger mirror workflow after adding tag
- Push to galaxy automatically

## [2.0.0] - 2026-02-24

### Breaking changes

- **Removed the `wzzrd.ghdl.starship` role.** The collection now ships only the
  generic `downloader` role. Users of `wzzrd.ghdl.starship` should replace it
  with `wzzrd.ghdl.downloader` and set `downloader_organization: starship-rs`,
  `downloader_project: starship`.
- **All internal variables renamed** to carry the `downloader_` prefix so they
  no longer pollute the global variable namespace and pass ansible-lint. If you
  referenced any of these in your own playbooks (e.g. `result_url`,
  `binary_checksum`, `checksum_file_url`, `download_result`, `src_file_path`,
  `dest_filename`, `binary_hash`) you will need to update those references to
  their `downloader_*` equivalents.

### New features

- **Version pinning.** Set `downloader_version` to a release tag (e.g.
  `v1.21.1`) to install a specific version. Omitting it continues to install
  the latest release.
- **Checksum verification.** The role now automatically detects SHA256 checksum
  files in a release (SHA256SUMS, sha256sum, checksums.txt, etc.), downloads
  them, and passes the hash to `get_url` for verification. Download proceeds
  without verification if no checksum file is found, with a warning.
- **Architecture validation.** The role now fails early with a clear, actionable
  error message when the target architecture has no configured matchers, listing
  supported architectures and how to add new ones.
- **macOS controller support.** When the Ansible controller runs on macOS, the
  role automatically uses `gtar` instead of BSD tar for archive extraction.
  Requires `brew install gnu-tar` on the controller.
- **Role argument specs.** Added `meta/argument_specs.yml`, which gives
  Ansible built-in validation of required variables and types before any tasks
  run, and enables `ansible-doc` and IDE autocompletion for role variables.
- **Filter: Android binary exclusion.** Android binaries are now excluded from
  asset selection alongside rpm, deb, apk, exe, and zst.
- **Filter: Variant binary deprioritization.** When a release includes both a
  main binary and named variants (e.g. `-server`, `-daemon`, `-cli`, `-agent`),
  the main binary is now preferred automatically.

### Performance

- **Download deduplication across hosts.** All downloads are delegated to the
  Ansible controller and stored in per-architecture subdirectories. When
  deploying to multiple hosts of the same architecture, the binary is downloaded
  exactly once. Five x86_64 hosts and three aarch64 hosts result in two
  downloads, not eight.
- **Extraction deduplication.** Archives are extracted once per architecture
  using a marker file. Subsequent hosts with the same architecture reuse the
  already-extracted content.
- **Race condition prevention.** Concurrent download and extraction operations
  are serialised with `throttle: 1` and guarded by file-existence checks to
  prevent collisions in parallel runs.

### Fixed

- Checksum variables are now explicitly cleared between architecture iterations,
  preventing a hash from one architecture being applied to another.
- Plain `.bz2` files (not `.tar.bz2`) are now correctly handled in all code
  paths using a negative lookbehind regex.
- Filter plugin no longer erroneously accepts Android APKs that matched
  architecture patterns before the package-format exclusion list ran.

### Tests

- Added a pytest unit test suite for `filter_binaries` covering matcher logic,
  package format exclusion, variant deprioritization, and error paths.

## [1.0.4]

Initial somewhat working version of ghdl collection
