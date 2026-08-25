#!/usr/bin/env python3

DOCUMENTATION = r"""
name: filter_binaries
short_description: Filter GitHub API release assets to find binary downloads
description:
    - This filter takes GitHub API release data and a list of matchers to find relevant binary downloads
    - It filters out common package formats (rpm, deb, apk, etc.) and checksum files
    - Returns the first matching binary download URL
version_added: "1.0.0"
author: "Maxim Burgerhout"
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
            - Order matters, earlier matchers are preferred over later ones
        type: list
        elements: str
        required: true
    variant:
        description:
            - Select a specific release variant, e.g. 'server'
            - When set, only assets whose filename contains '-{variant}' are considered
        type: str
        required: false
        default: ""
    libc:
        description:
            - Preferred C library flavour when a release ships both musl and glibc builds
            - musl prefers statically linked musl builds, which run on older systems
            - gnu prefers glibc builds, which keep NSS lookups and glibc DNS behaviour
            - any disables the libc preference, leaving selection to matcher order
        type: str
        required: false
        default: musl
        choices:
            - musl
            - gnu
            - any
"""

EXAMPLES = r"""
# Filter GitHub release assets for Linux x86_64 binaries
- name: Get binary URL for Linux x86_64
  set_fact:
    binary_url: "{{ github_release_data | wzzrd.ghdl.filter_binaries(['linux', 'x86_64']) }}"

# Filter for multiple architecture options
- name: Get binary URL for ARM64
  set_fact:
    binary_url: "{{ github_release_data | wzzrd.ghdl.filter_binaries(['arm64', 'aarch64']) }}"
"""

RETURN = r"""
_value:
    description: First matching binary download URL
    type: str
    returned: success
"""

import re

from ansible.errors import AnsibleFilterError

LIBC_CHOICES = ("musl", "gnu", "any")

# Match a libc token only when it is delimited by a separator or string boundary,
# so 'gnupg-linux-amd64' is not mistaken for a glibc build. The optional eabi
# suffix covers arm naming such as 'arm-unknown-linux-gnueabihf'.
MUSL_RE = re.compile(r"(?:^|[._-])musl(?:eabi(?:hf)?)?(?:$|[._-])")
GNU_RE = re.compile(r"(?:^|[._-])(?:gnu|glibc)(?:eabi(?:hf)?)?(?:$|[._-])")


def libc_rank(filename, libc):
    """Rank a filename by libc flavour, lower sorts first.

    Assets that name no libc at all (typically Go builds, which are static
    anyway) sort between the two, so an explicitly preferred flavour still wins
    but a plain asset beats the flavour that was not asked for.
    """
    if libc == "any":
        return 0

    if MUSL_RE.search(filename):
        found = "musl"
    elif GNU_RE.search(filename):
        found = "gnu"
    else:
        return 1

    return 0 if found == libc else 2


def filter_binaries(api_dict, matchers, variant="", libc="musl"):
    """Filter GitHub API release assets to find the best matching binary download URL."""
    if not isinstance(api_dict, dict):
        raise AnsibleFilterError(
            "The first argument must be a JSON dictionary as returned by the GitHub API."
        )

    if not isinstance(matchers, list):
        raise AnsibleFilterError(
            "The second argument must be a list of substrings to match against the GitHub API output."
        )

    if libc not in LIBC_CHOICES:
        raise AnsibleFilterError(
            f"Invalid libc preference '{libc}'. Valid choices are: {', '.join(LIBC_CHOICES)}."
        )

    if "json" not in api_dict:
        raise AnsibleFilterError(
            "The dictionary doesn't have a 'json' key. Is it proper Ansible uri module output?"
        )

    try:
        assets = api_dict["json"]["assets"]
    except KeyError:
        raise AnsibleFilterError(
            "The dictionary doesn't have an 'assets' key under 'json'. Is it proper GitHub API output?"
        )

    all_urls = [e["browser_download_url"] for e in assets]

    filtered_urls = [e for e in all_urls if any(match in e for match in matchers)]

    drop_matchers = ["sha256", "-update", "apk", "android", "rpm", "deb", "zst", "exe"]
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

    # Prioritize main binaries over variants (server, daemon, cli, agent, etc.)
    deprioritize_patterns = ["-server", "-android", "-daemon", "-agent", "-cli"]

    def sort_priority(url):
        """Rank a candidate URL, lowest sorts first.

        Ranks on three dimensions in order: main binaries before variant
        binaries, preferred libc flavour before the rest, and earlier matchers
        before later ones. Sorting is stable, so assets that tie on all three
        keep the order GitHub returned them in.
        """
        filename = url.split("/")[-1]
        variant_rank = (
            1 if any(pattern in filename for pattern in deprioritize_patterns) else 0
        )
        matcher_rank = next(
            (i for i, match in enumerate(matchers) if match in url), len(matchers)
        )
        return (variant_rank, libc_rank(filename, libc), matcher_rank)

    if variant:
        variant_pattern = f"-{variant}"
        variant_urls = [e for e in binary_urls if variant_pattern in e.split("/")[-1]]
        if not variant_urls:
            raise AnsibleFilterError(
                f"No matching binaries found for variant '{variant}' with matchers {matchers}. "
                f"Available assets after architecture and format filtering: "
                f"{[e.split('/')[-1] for e in binary_urls]}"
            )
        return sorted(variant_urls, key=sort_priority)[0]

    return sorted(binary_urls, key=sort_priority)[0]


class FilterModule(object):
    def filters(self):
        return {"filter_binaries": filter_binaries}
