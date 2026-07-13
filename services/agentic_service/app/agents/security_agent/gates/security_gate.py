"""
Security Gate.

Evaluates all security findings and produces
the final PASS / WARN / FAIL decision.
"""

from __future__ import annotations


class SecurityGate:
    """
    Evaluates security findings produced by the Security Agent.
    """

    def evaluate(self, findings: list[dict]) -> dict:
        """
        Evaluate all findings.

        Args:
            findings: Combined findings from all scanners.

        Returns:
            Security gate result.
        """

        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total_findings": len(findings),
        }

        for finding in findings:

            severity = finding.get("severity", "Low").lower()

            if severity == "critical":
                summary["critical"] += 1

            elif severity == "high":
                summary["high"] += 1

            elif severity == "medium":
                summary["medium"] += 1

            else:
                summary["low"] += 1

        decision = self._determine_gate(summary)

        return {
            "status": decision,
            "summary": summary,
        }

    def _determine_gate(self, summary: dict) -> str:
        """
        Determine the security gate decision.

        Rules:

        FAIL
            Any Critical finding
            OR 3+ High findings

        WARN
            Any High finding
            OR Medium findings

        PASS
            Only Low findings or no findings.
        """

        if summary["critical"] > 0:
            return "FAIL"

        if summary["high"] >= 3:
            return "FAIL"

        if summary["high"] > 0:
            return "WARN"

        if summary["medium"] > 0:
            return "WARN"

        return "PASS"