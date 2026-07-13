"""
Python AST-based security scanner.

Performs deterministic static analysis on Python source code.
"""

from __future__ import annotations

import ast
from pathlib import Path


class ASTScanner:
    """
    Performs AST-based static security analysis.
    """

    def scan(self, file_path: Path) -> list[dict]:
        """
        Scan a Python source file.

        Args:
            file_path: Python source file.

        Returns:
            List of detected security findings.
        """

        findings: list[dict] = []

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            return findings

        for node in ast.walk(tree):

            # Detect eval()
            if isinstance(node, ast.Call):

                if isinstance(node.func, ast.Name):

                    if node.func.id == "eval":
                        findings.append(
                            {
                                "title": "Use of eval()",
                                "description": "eval() can execute arbitrary code.",
                                "severity": "Critical",
                                "line": node.lineno,
                                "cwe": "CWE-95",
                                "recommendation": "Avoid eval(). Use safe parsing instead."
                            }
                        )

                    elif node.func.id == "exec":
                        findings.append(
                            {
                                "title": "Use of exec()",
                                "description": "exec() executes arbitrary Python code.",
                                "severity": "Critical",
                                "line": node.lineno,
                                "cwe": "CWE-95",
                                "recommendation": "Avoid exec() whenever possible."
                            }
                        )

            # Detect os.system()
            if isinstance(node, ast.Call):

                if isinstance(node.func, ast.Attribute):

                    if (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "os"
                        and node.func.attr == "system"
                    ):
                        findings.append(
                            {
                                "title": "Use of os.system()",
                                "description": "os.system() may allow command injection.",
                                "severity": "High",
                                "line": node.lineno,
                                "cwe": "CWE-78",
                                "recommendation": "Use subprocess.run() with validated inputs."
                            }
                        )

                    if (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "subprocess"
                        and node.func.attr in [
                            "Popen",
                            "run",
                            "call",
                            "check_output",
                        ]
                    ):

                        for keyword in node.keywords:

                            if (
                                keyword.arg == "shell"
                                and isinstance(keyword.value, ast.Constant)
                                and keyword.value.value is True
                            ):
                                findings.append(
                                    {
                                        "title": "subprocess with shell=True",
                                        "description": "shell=True may enable command injection.",
                                        "severity": "High",
                                        "line": node.lineno,
                                        "cwe": "CWE-78",
                                        "recommendation": "Avoid shell=True and validate inputs."
                                    }
                                )

        return findings