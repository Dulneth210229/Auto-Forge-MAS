"""
Dependency Scanner.

Detects known vulnerable dependency versions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.agents.security_agent.scanners.vulnerability_database import (
    VULNERABLE_PACKAGES,
)


class DependencyScanner:
    """
    Scans dependency manifests for known vulnerable packages.
    """

    def scan(self, project_path: Path) -> list[dict]:
        """
        Scan a project directory.

        Args:
            project_path: Root project directory.

        Returns:
            List of dependency findings.
        """

        findings = []

        findings.extend(self._scan_requirements(project_path))
        findings.extend(self._scan_package_json(project_path))

        return findings

    def _scan_requirements(self, project_path: Path) -> list[dict]:

        findings = []

        requirements = project_path / "requirements.txt"

        if not requirements.exists():
            return findings

        for line in requirements.read_text().splitlines():

            line = line.strip()

            if "==" not in line:
                continue

            package, version = line.split("==", 1)

            package = package.lower()

            if package in VULNERABLE_PACKAGES:

                findings.append(
                    {
                        "title": "Known Vulnerable Dependency",
                        "description": f"{package}=={version}",
                        "severity": "High",
                        "line": 0,
                        "cwe": "CWE-1104",
                        "recommendation": f"Upgrade {package} to a secure version.",
                    }
                )

        return findings

    def _scan_package_json(self, project_path: Path) -> list[dict]:

        findings = []

        package_json = project_path / "package.json"

        if not package_json.exists():
            return findings

        try:
            data = json.loads(package_json.read_text())
        except Exception:
            return findings

        dependencies = {}

        dependencies.update(data.get("dependencies", {}))
        dependencies.update(data.get("devDependencies", {}))

        for package, version in dependencies.items():

            if package.lower() in VULNERABLE_PACKAGES:

                findings.append(
                    {
                        "title": "Known Vulnerable Dependency",
                        "description": f"{package} {version}",
                        "severity": "High",
                        "line": 0,
                        "cwe": "CWE-1104",
                        "recommendation": f"Upgrade {package} to the latest secure version.",
                    }
                )

        return findings