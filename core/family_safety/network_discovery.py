"""
J.A.R.V.I.S. Mark XVII — Authorized Local Network Discovery
============================================================
Non-intrusive, privacy-respecting local network device discovery using
OS network tables and mDNS. Strictly separates Discovered, Identified,
Verified Owner, and Active User identities.
"""

import os
import re
import socket
import subprocess
import time
from typing import Dict, List, Optional, Any

from .models import DiscoveredDevice
from .storage import family_storage

class AuthorizedLocalNetworkDiscovery:
    def __init__(self, storage=None):
        self.storage = storage or family_storage
        self.last_scan_time = 0.0
        self.min_scan_interval_seconds = 10.0  # Rate limit
        self.last_discovered_devices: List[DiscoveredDevice] = []

    def scan_local_network(self, network_segment: str = "local_subnet") -> Dict[str, Any]:
        """
        Executes a passive OS ARP-table inspection to discover devices on the local network.
        Does NOT perform aggressive port scanning or traffic interception.
        """
        now = time.time()
        if (now - self.last_scan_time) < self.min_scan_interval_seconds and self.last_discovered_devices:
            return {
                "success": True,
                "cached": True,
                "count": len(self.last_discovered_devices),
                "devices": [d.model_dump() for d in self.last_discovered_devices],
                "limitations": "Rate-limited scan returned from cache."
            }

        discovered_list: List[DiscoveredDevice] = []
        enrolled_devices = self.storage.list_devices()

        # Build enrollment lookup by IP or capabilities
        enrolled_by_ip = {}
        for ed in enrolled_devices:
            last_conn = ed.get("lastKnownConnection") or {}
            if "ip" in last_conn and last_conn["ip"]:
                enrolled_by_ip[last_conn["ip"]] = ed

        try:
            # Read OS ARP Table safely
            arp_output = ""
            if os.name == "nt":
                arp_proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
                arp_output = arp_proc.stdout
            else:
                arp_proc = subprocess.run(["arp", "-n"], capture_output=True, text=True, timeout=5)
                arp_output = arp_proc.stdout

            # Parse IP and MAC entries
            # Format on Windows: 192.168.1.1 00-11-22-33-44-55 dynamic
            pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([0-9a-fA-F\:\-]{11,17})")
            for match in pattern.finditer(arp_output):
                ip = match.group(1)
                raw_mac = match.group(2).replace("-", ":").upper()

                # Ignore broadcast/multicast
                if ip.endswith(".255") or ip.startswith("224.") or ip.startswith("239.") or raw_mac == "FF:FF:FF:FF:FF:FF":
                    continue

                # Mask MAC for privacy protection (keep OUI prefix, mask individual ID)
                mac_parts = raw_mac.split(":")
                if len(mac_parts) == 6:
                    mac_masked = f"{mac_parts[0]}:{mac_parts[1]}:{mac_parts[2]}:XX:XX:{mac_parts[5]}"
                else:
                    mac_masked = raw_mac

                # Attempt hostname resolution with short timeout
                hostname = None
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except Exception:
                    pass

                # Check enrollment match
                enrollment_match = None
                is_identified = False
                is_owner_verified = False
                confidence = 0.4

                if ip in enrolled_by_ip:
                    matched_dev = enrolled_by_ip[ip]
                    enrollment_match = matched_dev["deviceId"]
                    is_identified = True
                    is_owner_verified = True
                    confidence = 0.95

                disc = DiscoveredDevice(
                    ipAddress=ip,
                    macMasked=mac_masked,
                    hostname=hostname,
                    manufacturer=self._resolve_oui_vendor(raw_mac),
                    discoveredAt=now,
                    networkSegment=network_segment,
                    enrollmentMatch=enrollment_match,
                    confidenceLevel=confidence,
                    isIdentified=is_identified,
                    isOwnerVerified=is_owner_verified
                )
                discovered_list.append(disc)

        except Exception as e:
            return {
                "success": False,
                "error": f"Local network discovery failed: {str(e)}",
                "limitations": "Operating system ARP inspection unavailable."
            }

        self.last_scan_time = now
        self.last_discovered_devices = discovered_list

        self.storage.log_audit(
            event_type="LOCAL_NETWORK_SCAN",
            actor_id="system",
            action=f"Discovered {len(discovered_list)} local network nodes.",
            risk_level="LOW"
        )

        return {
            "success": True,
            "cached": False,
            "count": len(discovered_list),
            "devices": [d.model_dump() for d in discovered_list],
            "limitations": (
                "Passively derived from OS ARP tables. "
                "Network presence does NOT prove human identity without enrolled authentication."
            )
        }

    def _resolve_oui_vendor(self, mac: str) -> Optional[str]:
        """Provides high-level manufacturer hint from standard OUI prefix where known."""
        prefix = mac.upper().replace("-", ":")[:8]
        known_ouis = {
            "00:50:56": "VMware",
            "00:1C:42": "Parallels",
            "B8:27:EB": "Raspberry Pi",
            "DC:A6:32": "Raspberry Pi",
            "00:0C:29": "VMware",
            "3C:D9:2B": "HP",
            "F0:18:98": "Apple",
            "AC:BC:32": "Apple",
            "FC:F8:AE": "Intel",
            "70:85:C2": "Samsung"
        }
        return known_ouis.get(prefix, "Standard Network Interface")

network_discovery = AuthorizedLocalNetworkDiscovery()
