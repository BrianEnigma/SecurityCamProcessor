"""Property-based test for make help listing all docker targets."""

import os
import re
import subprocess

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")

# All docker-* targets defined in the Makefile
DOCKER_TARGETS = ["docker-build", "docker-test", "docker-run", "docker-debug"]


def _get_help_output() -> str:
    """Run ``make help`` and return its stdout."""
    result = subprocess.run(
        ["make", "help"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"'make help' failed with exit code {result.returncode}.\n"
        f"stderr: {result.stderr.strip()}"
    )
    return result.stdout


def _parse_help_entries(output: str) -> dict[str, str]:
    """Parse make help output into a mapping of target name → description."""
    entries: dict[str, str] = {}
    for line in output.splitlines():
        # The help target formats output as:  "  target-name  description text"
        match = re.match(r"^\s*(\S+)\s+(.+)$", line)
        if match:
            entries[match.group(1)] = match.group(2).strip()
    return entries


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------

# Feature: docker-containerization, Property 6: Help target lists all docker targets
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(target=st.sampled_from(DOCKER_TARGETS))
def test_help_lists_all_docker_targets(target: str) -> None:
    """Property 6: For any docker target defined in the Makefile, running
    ``make help`` includes that target name with a non-empty description.

    Validates: Requirements 7.2
    """
    help_output = _get_help_output()
    entries = _parse_help_entries(help_output)

    assert target in entries, (
        f"Docker target '{target}' not found in 'make help' output.\n"
        f"Available targets: {list(entries.keys())}\n"
        f"Full output:\n{help_output}"
    )

    description = entries[target]
    assert len(description) > 0, (
        f"Docker target '{target}' has an empty description in 'make help' output."
    )
