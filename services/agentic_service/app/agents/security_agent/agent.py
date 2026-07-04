"""
Security Agent.

Purpose (future):
- Run npm audit / SAST tooling against the merged feature branch via sandbox_service.
- Flag vulnerabilities mapped to specific files/lines.
- Produce a security_report artifact for human review.

Placeholder for this phase: passes through without blocking the pipeline.
Reuses sandbox_service (already built, generic, not coder-agent-specific)
when implemented for real -- npm audit / dependency scanning.
"""


class SecurityAgent:
    async def run(self, **kwargs):
        return {"status": "skipped", "message": "Security Agent not yet implemented."}


security_agent = SecurityAgent()
