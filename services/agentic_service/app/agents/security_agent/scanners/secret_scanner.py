"""
Secret Scanner.

Detects hardcoded secrets using regular expressions.
"""

from __future__ import annotations

import re
from pathlib import Path


class SecretScanner:
    """
    Scans source files for hardcoded credentials and secrets.
    """

    SECRET_PATTERNS = [

        # password = "..."
        (
            "Hardcoded Password",
            re.compile(
                r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']'
            ),
            "High",
            "CWE-798",
            "Store passwords in environment variables or a secret manager.",
        ),

        # api_key = "..."
        (
            "Hardcoded API Key",
            re.compile(
                r'(?i)(api[_-]?key)\s*=\s*["\'][^"\']+["\']'
            ),
            "High",
            "CWE-798",
            "Store API keys securely outside the source code.",
        ),

        # secret = "..."
        (
            "Hardcoded Secret",
            re.compile(
                r'(?i)(secret|client_secret)\s*=\s*["\'][^"\']+["\']'
            ),
            "High",
            "CWE-798",
            "Move secrets to secure configuration storage.",
        ),

        # token = "..."
        (
            "Hardcoded Token",
            re.compile(
                r'(?i)(token|access_token)\s*=\s*["\'][^"\']+["\']'
            ),
            "Medium",
            "CWE-798",
            "Avoid storing access tokens in source code.",
        ),

        # AWS Access Key
        (
            "AWS Access Key",
            re.compile(r'AKIA[0-9A-Z]{16}'),
            "Critical",
            "CWE-798",
            "Rotate the exposed AWS credentials immediately.",
        ),
    ]

    def scan(self, file_path: Path) -> list[dict]:
        """
        Scan a source file for secrets.

        Args:
            file_path: Source file path.

        Returns:
            List of detected findings.
        """

        findings: list[dict] = []

        try:
            content = file_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            return findings

        lines = content.splitlines()

        for line_number, line in enumerate(lines, start=1):

            for (
                title,
                pattern,
                severity,
                cwe,
                recommendation,
            ) in self.SECRET_PATTERNS:

                if pattern.search(line):

                    findings.append(
                        {
                            "title": title,
                            "description": line.strip(),
                            "severity": severity,
                            "line": line_number,
                            "cwe": cwe,
                            "recommendation": recommendation,
                        }
                    )

        return findings