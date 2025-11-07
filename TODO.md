# TODO List for wzzrd.ghdl

This document tracks improvements and enhancements for the wzzrd.ghdl Ansible collection.

## ✅ Completed

### Critical Bugs (All Fixed)
- [x] **Bug 1**: Wrong variable in versioned downloads (`select_binary.yml:48`)
  - Fixed: Use `github_api_data_versioned` instead of `github_api_data_latest`
- [x] **Bug 2**: Crash when no binary matches (`filter_binaries.py:79`)
  - Fixed: Added error handling with diagnostic output
- [x] **Bug 3**: GitHub token exposed in logs
  - Fixed: Added `no_log: true` to all API calls using token
- [x] **Bug 4**: Binary naming logic broken (`handle_binary.yml`)
  - Fixed: Smart regex extraction with fallback logic

### High Priority Features
- [x] **Bug 6**: Architecture validation
  - Added clear error messages listing supported architectures
  - Fails early with instructions on how to extend support
- [x] **Bug 7**: Checksum verification
  - Downloads and parses checksum files from GitHub releases
  - Verifies SHA256 hashes automatically
  - Gracefully degrades when checksums not available
- [x] **Bug 12**: Unit tests for filter plugin
  - Created comprehensive test suite (17 test cases)
  - Tests edge cases, error handling, and real-world examples
  - Can be integrated into CI/CD pipeline
- [x] **Bug 14**: Debug output too verbose
  - Changed from dumping full API response to showing only asset names
  - Much more readable and useful for troubleshooting
- [x] **Bug 15**: Missing owner/group in binary handler
  - Added `owner` and `group` parameters for consistency with archive handler
- [x] **Bug 18**: Dead code cleanup
  - Removed unused `pprint` import from filter plugin
  - Removed empty handler files (downloader, starship)
  - Removed empty vars file (starship)

### Skipped (By Design)
- [ ] **Bug 5**: Darwin/macOS matcher support
  - Reason: Not needed for current use case
  - Can be added later when needed
- [ ] **Bug 8**: Idempotency check
  - Reason: Deferred to future release
  - Would check if binary already installed before downloading

---

## 🔄 In Progress

None currently.

---

## 📋 TODO - Medium Priority

### Bug 9: CI/CD Pipeline
- [ ] Create `.github/workflows/test.yml` for unit tests
- [ ] Create `.github/workflows/molecule.yml` for integration tests
- [ ] Add status badges to README.md
- [ ] Consider adding codecov integration

**Benefit**: Catch breaking changes before release

### Bug 10: Starship Role Documentation
- [ ] Update `roles/starship/README.md` (currently boilerplate)
- [ ] Document purpose, variables, and usage
- [ ] Add example playbook

**Benefit**: Users can understand and use the starship role

### Bug 11: Proxy Support
- [ ] Add `downloader_proxy` variable to defaults
- [ ] Add proxy support to `uri` module calls
- [ ] Add proxy support to `get_url` module calls
- [ ] Test with corporate proxy environment

**Benefit**: Works in corporate environments with proxies

### Bug 13: Metadata Inconsistencies
- [ ] Update `CHANGELOG.md` to version 1.1.0 (currently shows 1.0.4)
- [ ] Document all changes since 1.0.4
- [ ] Ensure version matches `galaxy.yml`

**Benefit**: Clear version history for users

---

## 📋 TODO - Low Priority

### Bug 16: Build Artifacts
- [ ] Update `galaxy.yml` build_ignore to exclude:
  - `.vscode`
  - `.envrc`
  - `.devcontainer`
  - `flow.txt`
  - `*.tar.gz`
  - `.git*`
  - `TODO.md`

**Benefit**: Smaller published package, cleaner releases

### Bug 17: Troubleshooting Guide
- [ ] Add detailed troubleshooting section to README.md
- [ ] How to debug "No matching binary found" errors
- [ ] How to add custom architecture matchers
- [ ] How to test filter plugin directly
- [ ] Common API rate limiting solutions

**Benefit**: Users can self-service debug issues

### Bug 19: Contributing Guidelines
- [ ] Create `CONTRIBUTING.md`
- [ ] Document how to run tests (unit + molecule)
- [ ] Document code style requirements
- [ ] Document PR submission process
- [ ] Add issue templates

**Benefit**: Easier for contributors to participate

### Bug 20: Configurable Drop Matchers
- [ ] Make `drop_matchers` in `filter_binaries.py` configurable
- [ ] Add as optional parameter with defaults
- [ ] Update documentation

**Benefit**: Users can override package format filtering

### Bug 21: Platform Metadata
- [ ] Add platform information to `roles/*/meta/main.yml`
- [ ] List tested platforms (EL 8/9, Ubuntu, Fedora)
- [ ] Uncomment platforms section

**Benefit**: Better Galaxy discoverability

### Bug 22: Multiple Executables in Archives
- [ ] Add logic to handle multiple executables in archives
- [ ] Either fail with clear message or add selection parameter
- [ ] Currently takes first found (intentional but undocumented)

**Benefit**: Better error messages, more predictable behavior

---

## 📊 Progress Summary

- **Completed**: 10 items (all critical + key features)
- **Skipped**: 2 items (by design)
- **Remaining**: 12 items (6 medium, 6 low priority)

**Status**: Collection is production-ready. All critical bugs fixed, security hardened, and properly tested.

---

## Testing Commands

### Run Unit Tests
```bash
pip install -r tests/requirements.txt
cd tests/unit
pytest -v
```

### Run Integration Tests (Molecule)
```bash
cd roles/downloader
GITHUB_PAT="your_token" molecule test
```

### Build Collection
```bash
ansible-galaxy collection build
```

### Install Locally
```bash
ansible-galaxy collection install ./wzzrd-ghdl-1.1.0.tar.gz --force
```

---

Last Updated: 2025-01-07
