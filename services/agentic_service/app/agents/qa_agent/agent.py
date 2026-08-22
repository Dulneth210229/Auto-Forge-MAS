"""
QA Agent.

Purpose (future):
- Run (and possibly write) the test suite for the merged feature branch.
- Report failures with enough detail for a human to act on.

Placeholder for this phase: passes through without blocking the pipeline.
Reuses sandbox_service (already built, generic, not coder-agent-specific)
when implemented for real -- running the generated test suite.
"""


class QAAgent:
    async def run(self, **kwargs):
        return {"status": "skipped", "message": "QA Agent not yet implemented."}


qa_agent = QAAgent()