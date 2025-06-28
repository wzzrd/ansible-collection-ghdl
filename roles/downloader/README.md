# ghdl Role

This role downloads and installs binary releases from GitHub repositories.

For complete documentation, examples, and usage instructions, see the [collection README](../../README.md).

## Quick Example

```yaml
- hosts: servers
  become: yes
  roles:
    - role: wzzrd.ghdl.ghdl
      vars:
        downloader_organization: "hashicorp"
        downloader_project: "terraform"
        downloader_github_token: "{{ vault_github_token }}"
