#import json
#from pprint import pprint
from ansible.errors import AnsibleFilterError

def filter_binaries(api_dict, matchers):
    """Check if any substring in a list is present in the string."""
    if not isinstance(api_dict, dict):
        raise AnsibleFilterError("The first argument must be a JSON dictionary as returned by the GitHub API.")

    if not isinstance(matchers, list):
        pprint(matchers)
        raise AnsibleFilterError("The second argument must be a list of substrings to match against the GitHub API output.")

    try:
        assets = api_dict['json']['assets']
    except (KeyError):
        raise AnsibleFilterError("The dictionary doesn't have an 'assets' object. Is it proper GitHub API output?")

    all_urls = [ e['browser_download_url'] for e in assets ]
    #pprint(all_urls)

    filtered_urls = [ e for e in all_urls if any(match in e for match in matchers) ]
    #pprint(filtered_urls)

    drop_matchers = ["sha256", "-update", "apk", "rpm", "deb", "zst", "exe" ]
    binary_urls = [ e for e in filtered_urls if not any(match in e for match in drop_matchers) ]

    return binary_urls[0]

class FilterModule(object):
    def filters(self):
        return {
            'filter_binaries': filter_binaries
        }

