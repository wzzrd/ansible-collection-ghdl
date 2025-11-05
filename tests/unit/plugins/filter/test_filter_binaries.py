#!/usr/bin/env python3
"""Unit tests for filter_binaries plugin."""

import pytest
import sys
from pathlib import Path

# Add the plugin directory to the path
plugin_dir = Path(__file__).resolve().parents[4] / 'plugins' / 'filter'
sys.path.insert(0, str(plugin_dir))

from filter_binaries import filter_binaries
from ansible.errors import AnsibleFilterError


class TestFilterBinaries:
    """Test cases for the filter_binaries filter plugin."""

    def test_simple_match_linux_amd64(self):
        """Test matching a simple linux amd64 binary."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-darwin-arm64"},
                ]
            }
        }
        matchers = ["linux-amd64", "linux_amd64"]
        result = filter_binaries(api_dict, matchers)
        assert result == "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"

    def test_filters_out_rpm_packages(self):
        """Test that RPM packages are excluded from results."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-1.0.0-x86_64.rpm"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"},
                ]
            }
        }
        matchers = ["linux-amd64", "x86_64"]
        result = filter_binaries(api_dict, matchers)
        # Should skip the .rpm and return the binary
        assert result == "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"

    def test_filters_out_checksums(self):
        """Test that checksum files are excluded from results."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64.sha256"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"},
                ]
            }
        }
        matchers = ["linux-amd64"]
        result = filter_binaries(api_dict, matchers)
        assert result == "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"

    def test_filters_out_all_package_formats(self):
        """Test that all package formats are excluded."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-1.0.0.rpm"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-1.0.0.deb"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-1.0.0.apk"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-windows.exe"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary.zst"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"},
                ]
            }
        }
        matchers = ["linux-amd64", "rpm", "deb", "apk", "exe", "windows"]
        result = filter_binaries(api_dict, matchers)
        # Should only return the plain binary, not any packages
        assert result == "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"

    def test_no_matching_binary_raises_error(self):
        """Test that an error is raised when no binary matches."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-windows.exe"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-darwin-arm64"},
                ]
            }
        }
        matchers = ["linux-amd64", "linux_amd64"]

        with pytest.raises(AnsibleFilterError) as exc_info:
            filter_binaries(api_dict, matchers)

        # Verify error message contains useful info
        error_msg = str(exc_info.value)
        assert "No matching binaries found" in error_msg
        assert "linux-amd64" in error_msg or "linux_amd64" in error_msg

    def test_empty_assets_raises_error(self):
        """Test that an error is raised when assets list is empty."""
        api_dict = {
            "json": {
                "assets": []
            }
        }
        matchers = ["linux-amd64"]

        with pytest.raises(AnsibleFilterError) as exc_info:
            filter_binaries(api_dict, matchers)

        error_msg = str(exc_info.value)
        assert "No matching binaries found" in error_msg

    def test_invalid_api_dict_raises_error(self):
        """Test that an error is raised for invalid API dict."""
        api_dict = "not a dict"
        matchers = ["linux-amd64"]

        with pytest.raises(AnsibleFilterError) as exc_info:
            filter_binaries(api_dict, matchers)

        assert "must be a JSON dictionary" in str(exc_info.value)

    def test_invalid_matchers_raises_error(self):
        """Test that an error is raised for invalid matchers."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"},
                ]
            }
        }
        matchers = "not a list"

        with pytest.raises(AnsibleFilterError) as exc_info:
            filter_binaries(api_dict, matchers)

        assert "must be a list" in str(exc_info.value)

    def test_missing_assets_key_raises_error(self):
        """Test that an error is raised when assets key is missing."""
        api_dict = {
            "json": {
                "foo": "bar"
            }
        }
        matchers = ["linux-amd64"]

        with pytest.raises(AnsibleFilterError) as exc_info:
            filter_binaries(api_dict, matchers)

        assert "assets" in str(exc_info.value)

    def test_multiple_matchers(self):
        """Test matching with multiple matcher patterns."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-x86_64-unknown-linux-musl"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-darwin-arm64"},
                ]
            }
        }
        matchers = ["x86_64-unknown-linux-musl", "x86_64-unknown-linux-gnu", "linux_amd64"]
        result = filter_binaries(api_dict, matchers)
        assert result == "https://github.com/org/proj/releases/download/v1.0.0/binary-x86_64-unknown-linux-musl"

    def test_returns_first_match(self):
        """Test that the first matching binary is returned when multiple match."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/another-linux-amd64"},
                ]
            }
        }
        matchers = ["linux-amd64"]
        result = filter_binaries(api_dict, matchers)
        assert result == "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"

    def test_archive_files_match(self):
        """Test that archive files (tar.gz, zip) are matched correctly."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64.tar.gz"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-darwin-arm64.zip"},
                ]
            }
        }
        matchers = ["linux-amd64"]
        result = filter_binaries(api_dict, matchers)
        assert result == "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64.tar.gz"

    def test_filters_update_binaries(self):
        """Test that -update binaries are filtered out."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64-update"},
                    {"browser_download_url": "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"},
                ]
            }
        }
        matchers = ["linux-amd64"]
        result = filter_binaries(api_dict, matchers)
        assert result == "https://github.com/org/proj/releases/download/v1.0.0/binary-linux-amd64"

    def test_real_world_chezmoi_example(self):
        """Test with real-world chezmoi release pattern."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/twpayne/chezmoi/releases/download/v2.67.0/chezmoi-2.67.0-aarch64.rpm"},
                    {"browser_download_url": "https://github.com/twpayne/chezmoi/releases/download/v2.67.0/chezmoi-darwin-arm64"},
                    {"browser_download_url": "https://github.com/twpayne/chezmoi/releases/download/v2.67.0/chezmoi-linux-amd64"},
                    {"browser_download_url": "https://github.com/twpayne/chezmoi/releases/download/v2.67.0/checksums.txt"},
                ]
            }
        }
        matchers = ["darwin-arm64", "aarch64-apple-darwin"]
        result = filter_binaries(api_dict, matchers)
        assert result == "https://github.com/twpayne/chezmoi/releases/download/v2.67.0/chezmoi-darwin-arm64"

    def test_real_world_terraform_example(self):
        """Test with real-world terraform release pattern."""
        api_dict = {
            "json": {
                "assets": [
                    {"browser_download_url": "https://github.com/hashicorp/terraform/releases/download/v1.5.0/terraform_1.5.0_linux_amd64.zip"},
                    {"browser_download_url": "https://github.com/hashicorp/terraform/releases/download/v1.5.0/terraform_1.5.0_linux_arm64.zip"},
                    {"browser_download_url": "https://github.com/hashicorp/terraform/releases/download/v1.5.0/terraform_1.5.0_SHA256SUMS"},
                ]
            }
        }
        matchers = ["linux_amd64", "linux-amd64"]
        result = filter_binaries(api_dict, matchers)
        assert result == "https://github.com/hashicorp/terraform/releases/download/v1.5.0/terraform_1.5.0_linux_amd64.zip"
