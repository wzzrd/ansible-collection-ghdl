#!/usr/bin/env python

DOCUMENTATION = r'''
name: filter_binaries
short_description: Filter GitHub API release assets to find binary downloads
description:
    - This filter takes GitHub API release data and a list of matchers to find relevant binary downloads
    - It filters out common package formats (rpm, deb, apk, etc.) and checksum files
    - Returns the first matching binary download URL
version_added: "1.0.0"
author: "Your Name"
options:
    api_dict:
        description:
            - Dictionary containing GitHub API release data
            - Must contain a 'json' key with 'assets' array
        type: dict
        required: true
    matchers:
        description:
            - List of substrings to match against asset download URLs
            - URLs containing any of these substrings will be included
        type: list
        elements: str
        required: true
'''

EXAMPLES = r'''
# Filter GitHub release assets for Linux x86_64 binaries
- name: Get binary URL for Linux x86_64
  set_fact:
    binary_url: "{{ github_release_data | wzzrd.ghdl.filter_binaries(['linux', 'x86_64']) }}"

# Filter for multiple architecture options
- name: Get binary URL for ARM64
  set_fact:
    binary_url: "{{ github_release_data | wzzrd.ghdl.filter_binaries(['arm64', 'aarch64']) }}"
'''

RETURN = r'''
_value:
    description: First matching binary download URL
    type: str
    returned: success
'''

from pprint import pprint
from ansible.errors import AnsibleFilterError


def filter_binaries(api_dict, matchers):
    """Check if any substring in a list is present in the string."""
    if not isinstance(api_dict, dict):
        raise AnsibleFilterError(
            "The first argument must be a JSON dictionary as returned by the GitHub API."
        )

    if not isinstance(matchers, list):
        raise AnsibleFilterError(
            "The second argument must be a list of substrings to match against the GitHub API output."
        )

    try:
        assets = api_dict["json"]["assets"]
    except KeyError:
        raise AnsibleFilterError(
            "The dictionary doesn't have an 'assets' object. Is it proper GitHub API output?"
        )

    all_urls = [e["browser_download_url"] for e in assets]

    filtered_urls = [e for e in all_urls if any(match in e for match in matchers)]

    drop_matchers = ["sha256", "-update", "apk", "rpm", "deb", "zst", "exe"]
    binary_urls = [
        e for e in filtered_urls if not any(match in e for match in drop_matchers)
    ]

    if not binary_urls:
        raise AnsibleFilterError(
            f"No matching binaries found for matchers {matchers}. "
            f"Available assets: {[e.split('/')[-1] for e in all_urls]}. "
            f"After filtering for matchers: {[e.split('/')[-1] for e in filtered_urls]}. "
            f"After removing package formats: {binary_urls}"
        )

    return binary_urls[0]


class FilterModule(object):
    def filters(self):
        return {"filter_binaries": filter_binaries}
