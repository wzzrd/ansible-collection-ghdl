# wzzrd.ghdl.downloader

Downloads and installs binary releases from GitHub repositories.

For full documentation, variable reference, and examples see the
[collection README](../../README.md).

## Quick example

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
