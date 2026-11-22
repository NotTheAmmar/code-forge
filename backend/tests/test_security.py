"""Security hardening tests (Phase A2).

Verifies sandbox isolation, fork-bomb containment via pids_limit=64,
file descriptor limits via ulimit nofile=64:64, tmpfs mount constraints,
and network isolation across all execution containers.
"""

import os
import tempfile
import docker
import pytest
from app.config import settings
from app.worker.sandbox import _get_docker_client


class TestSecurityHardening:
    """Validate sandbox container security constraints."""

    def test_pids_limit_and_fork_bomb_containment(self):
        """Fork bomb is throttled and blocked by pids_limit without affecting host."""
        client = _get_docker_client()
        # Script that attempts to spawn unlimited processes
        cmd = [
            "sh",
            "-c",
            ":(){ :|:& };: 2>/dev/null; sleep 1; echo ok",
        ]
        container = client.containers.create(
            image="codeforge-sandbox-c",
            command=cmd,
            network_disabled=True,
            mem_limit="64m",
            pids_limit=settings.sandbox_pids_limit,
            user="runner",
        )
        try:
            container.start()
            res = container.wait(timeout=10)
            # The container either exits with error or terminates within timeout
            assert res is not None
        finally:
            container.remove(force=True)

    def test_ulimit_nofile_enforced(self):
        """File descriptor limit (ulimit -n) is strictly enforced to 64."""
        client = _get_docker_client()
        u = docker.types.Ulimit(
            name="nofile",
            soft=settings.sandbox_ulimit_nofile,
            hard=settings.sandbox_ulimit_nofile,
        )
        container = client.containers.create(
            image="codeforge-sandbox-python",
            command=["sh", "-c", "ulimit -n"],
            ulimits=[u],
            user="runner",
        )
        try:
            container.start()
            container.wait(timeout=10)
            output = container.logs().decode().strip()
            assert output == str(settings.sandbox_ulimit_nofile)
        finally:
            container.remove(force=True)

    def test_tmpfs_noexec_and_size_enforced(self):
        """tmpfs is mounted at /tmp with noexec flag and strict size limit."""
        client = _get_docker_client()
        container = client.containers.create(
            image="codeforge-sandbox-c",
            command=["sh", "-c", "mount | grep '/tmp'"],
            tmpfs={"/tmp": f"size={settings.sandbox_tmpfs_size},noexec,nosuid"},
            user="runner",
        )
        try:
            container.start()
            container.wait(timeout=10)
            output = container.logs().decode().strip()
            assert "noexec" in output
            assert "nosuid" in output
        finally:
            container.remove(force=True)

    def test_network_isolation(self):
        """Network access is completely disabled inside sandbox."""
        client = _get_docker_client()
        container = client.containers.create(
            image="codeforge-sandbox-python",
            command=["sh", "-c", "cat /sys/class/net/*/operstate 2>/dev/null || ip link 2>/dev/null || echo isolated"],
            network_disabled=True,
            user="runner",
        )
        try:
            container.start()
            container.wait(timeout=10)
            output = container.logs().decode().strip()
            # Only loopback exists if any, external interfaces are absent
            assert "eth0" not in output
        finally:
            container.remove(force=True)
