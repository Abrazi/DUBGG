from dataclasses import dataclass, field
from typing import List
import socket
import subprocess
import platform


@dataclass
class NetworkInterface:
    name: str
    ip_address: str
    is_up: bool
    all_ips: List[str] = field(default_factory=list)


class NetworkUtils:
    @staticmethod
    def get_network_interfaces() -> List[NetworkInterface]:
        """Return a list of available network interfaces (best-effort).

        Tries to use psutil when available; falls back to a single "primary"
        interface using the host name lookup.
        """
        try:
            import psutil

            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            interfaces: List[NetworkInterface] = []
            for name, addr_list in addrs.items():
                ip = "127.0.0.1"
                all_ips = []
                for a in addr_list:
                    if getattr(a, "family", None) == socket.AF_INET:
                        if ip == "127.0.0.1":
                            ip = a.address
                        all_ips.append(a.address)
                is_up = bool(stats.get(name).isup) if stats.get(name) else False
                interfaces.append(NetworkInterface(name=name, ip_address=ip, is_up=is_up, all_ips=all_ips))
            return interfaces
        except Exception:
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
            except Exception:
                ip = "127.0.0.1"
            return [NetworkInterface(name="primary", ip_address=ip, is_up=True, all_ips=[ip])]

    @staticmethod
    def check_host_reachable(ip: str, timeout: float = 1.0) -> bool:
        """Best-effort check whether `ip` responds to a single ping.

        Uses the system `ping` command for cross-platform behavior. Returns
        True when ping returns success, False otherwise.
        """
        try:
            system = platform.system().lower()
            if system == "windows":
                # -n 1 (one echo request) -w timeout_in_ms
                cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip]
            else:
                # -c 1 (one packet) -W timeout_in_seconds
                cmd = ["ping", "-c", "1", "-W", str(int(max(1, timeout))), ip]
            return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        except Exception:
            return False


class NetworkScriptGenerator:
    @staticmethod
    def generate_linux_script(ips: List[str], adapter_name: str) -> str:
        """Generate a Linux bash script that adds the given IPs to the adapter.

        Uses the `ip addr add` command. Requires sudo privileges.
        """
        lines = ["#!/bin/bash", "echo 'Adding IP addresses...'"]
        for ip in ips:
            # ip addr add <ip>/24 dev <device>
            lines.append(f'sudo ip addr add {ip}/24 dev "{adapter_name}"')
        lines.append("echo 'Done.'")
        return "\n".join(lines)

    @staticmethod
    def generate_windows_batch(ips: List[str], adapter_name: str) -> str:
        """Generate a Windows batch script that adds the given IPs to the adapter.

        This is a simple, idempotent generator which issues `netsh interface ip add address`
        commands for each provided IP. The mask is left as a common /16 (255.255.0.0);
        callers may edit if a different netmask is required.
        """
        lines = ["@echo off", "echo Adding IP addresses...", "setlocal enabledelayedexpansion"]
        for ip in ips:
            # netsh syntax: name="Adapter Name" addr=<ip> mask=<netmask>
            lines.append(f'netsh interface ip add address name="{adapter_name}" addr={ip} mask=255.255.0.0')
        lines.append("echo Done.")
        return "\r\n".join(lines)

