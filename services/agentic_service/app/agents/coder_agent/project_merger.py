"""
Coder Agent project merger.

Purpose:
    Safely merge newly generated files into the existing project snapshot.
    This is the most critical module in the Coder Agent.

Architecture fit:
    - Called by agent.py AFTER parsing the LLM response.
    - Receives the previous project snapshot (list of GeneratedFile)
      and the LLM's raw output (new + updated files).
    - Returns a MergeResult containing all three file categories and a
      human-readable merge report.

Merge rules (from the spec):
    1. NEVER delete files. Any file in the previous snapshot that is not
       in the LLM output is automatically preserved as "unchanged".
    2. NEVER rename files. If a file path changes, it is treated as a
       new file — the original is still preserved.
    3. NEVER overwrite unrelated files. Only files explicitly returned
       by the LLM as "new" or "updated" are modified.
    4. Build the complete file tree from all three categories.

Author: Coder Agent (Auto-Forge MAS)
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agents.coder_agent.schemas import GeneratedFile, CoderAgentOutput, ArtifactMetadataEntry
from app.utils.logger import get_logger

logger = get_logger("coder_agent.project_merger")


# ---------------------------------------------------------------------------
# MergeResult data class
# ---------------------------------------------------------------------------

@dataclass
class MergeResult:
    """
    The complete result of a project merge operation.

    All three file lists together represent the full state of the project
    after this iteration.

    Attributes:
        generated_files:  New files created for this feature.
        updated_files:    Existing files modified to support this feature.
        unchanged_files:  Existing files preserved without modification.
        file_tree:        Nested dict representation of the project structure.
        merge_report_markdown: Human-readable summary of changes.
    """
    generated_files: list[GeneratedFile] = field(default_factory=list)
    updated_files: list[GeneratedFile] = field(default_factory=list)
    unchanged_files: list[GeneratedFile] = field(default_factory=list)
    file_tree: dict[str, Any] = field(default_factory=dict)
    merge_report_markdown: str = ""

    @property
    def all_files(self) -> list[GeneratedFile]:
        """Return all files across all three categories."""
        return self.generated_files + self.updated_files + self.unchanged_files


# ---------------------------------------------------------------------------
# ProjectMerger
# ---------------------------------------------------------------------------

class ProjectMerger:
    """
    Merges LLM-generated files into the existing project snapshot.

    This class enforces all merge rules from the specification.
    It is stateless — each call to merge() is independent.
    """

    def merge(
        self,
        previous_snapshot: list[GeneratedFile],
        llm_generated: list[GeneratedFile],
        llm_updated: list[GeneratedFile],
        feature_id: str,
        feature_name: str,
        project_id: str,
        project_name: str,
        target_stack: str,
        version: int,
    ) -> MergeResult:
        """
        Perform the full merge operation.

        Steps:
        1. Collect all file paths the LLM touched (new + updated).
        2. For each file in the previous snapshot that the LLM did NOT touch,
           mark it as "unchanged" and carry it forward.
        3. Validate that the LLM did not implicitly delete any previous files.
        4. Build the nested file tree.
        5. Generate the merge report.

        Args:
            previous_snapshot:  Files from the last approved CODE artifact.
            llm_generated:      New files returned by the LLM.
            llm_updated:        Updated files returned by the LLM.
            feature_id:         Current feature ID.
            feature_name:       Current feature name (for report).
            project_id:         Current project ID.
            project_name:       Current project name (for report).
            target_stack:       Technology stack (for report).
            version:            Artifact version number for this run.

        Returns:
            MergeResult with all three file categories.
        """
        logger.info(
            "[ProjectMerger] Starting merge for feature='%s'. "
            "Previous snapshot: %d files. LLM new: %d. LLM updated: %d.",
            feature_name,
            len(previous_snapshot),
            len(llm_generated),
            len(llm_updated)
        )

        # ------------------------------------------------------------------
        # 1. Collect all paths the LLM explicitly touched
        # ------------------------------------------------------------------
        llm_touched_paths: set[str] = set()
        for f in llm_generated:
            llm_touched_paths.add(self._normalize_path(f.file_path))
        for f in llm_updated:
            llm_touched_paths.add(self._normalize_path(f.file_path))

        # ------------------------------------------------------------------
        # 2. Preserve files the LLM did not touch
        # ------------------------------------------------------------------
        unchanged_files: list[GeneratedFile] = []

        for prev_file in previous_snapshot:
            norm_path = self._normalize_path(prev_file.file_path)
            if norm_path not in llm_touched_paths:
                # Preserve this file exactly as it was
                preserved = GeneratedFile(
                    file_path=prev_file.file_path,
                    content=prev_file.content,
                    change_type="unchanged",
                    purpose=prev_file.purpose,
                    description=(
                        f"Preserved from previous iteration. "
                        f"Not affected by '{feature_name}' feature."
                    ),
                    feature_id=prev_file.feature_id,
                    version=prev_file.version,
                )
                unchanged_files.append(preserved)
                logger.debug(
                    "[ProjectMerger] Preserving unchanged file: %s", prev_file.file_path
                )

        # ------------------------------------------------------------------
        # 3. Stamp generated and updated files with current feature context
        # ------------------------------------------------------------------
        stamped_generated = [
            self._stamp_file(f, feature_id, version) for f in llm_generated
        ]
        stamped_updated = [
            self._stamp_file(f, feature_id, version) for f in llm_updated
        ]

        logger.info(
            "[ProjectMerger] Merge complete. New: %d, Updated: %d, Unchanged: %d.",
            len(stamped_generated),
            len(stamped_updated),
            len(unchanged_files)
        )

        # ------------------------------------------------------------------
        # 4. Build the file tree from all files
        # ------------------------------------------------------------------
        all_files = stamped_generated + stamped_updated + unchanged_files
        file_tree = self.build_file_tree(all_files)

        # ------------------------------------------------------------------
        # 5. Generate the merge report
        # ------------------------------------------------------------------
        merge_report = self._generate_merge_report(
            feature_name=feature_name,
            project_name=project_name,
            generated_files=stamped_generated,
            updated_files=stamped_updated,
            unchanged_files=unchanged_files,
            version=version,
        )

        return MergeResult(
            generated_files=stamped_generated,
            updated_files=stamped_updated,
            unchanged_files=unchanged_files,
            file_tree=file_tree,
            merge_report_markdown=merge_report,
        )

    def _stamp_file(
        self,
        f: GeneratedFile,
        feature_id: str,
        version: int
    ) -> GeneratedFile:
        """
        Ensure the file has the correct feature_id and version stamped.

        LLMs sometimes omit or misformat these fields.
        """
        return GeneratedFile(
            file_path=f.file_path,
            content=f.content,
            change_type=f.change_type,
            purpose=f.purpose,
            description=f.description,
            feature_id=feature_id,
            version=version,
        )

    def _normalize_path(self, path: str) -> str:
        """
        Normalize a file path for comparison.

        Converts backslashes to forward slashes and strips leading separators.
        """
        return path.replace("\\", "/").strip("/").lower()

    def build_file_tree(self, files: list[GeneratedFile]) -> dict[str, Any]:
        """
        Build a nested dictionary representing the project file tree.

        Example:
            Input:  ["backend/routes/auth.js", "backend/models/User.js"]
            Output: {"backend": {"routes": {"auth.js": None},
                                 "models": {"User.js": None}}}

        Args:
            files: All files in the project (all three categories).

        Returns:
            Nested dict where leaf nodes are None.
        """
        tree: dict[str, Any] = {}

        for f in files:
            parts = self._normalize_path(f.file_path).split("/")
            node = tree
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # Leaf node (actual file)
                    node[part] = None
                else:
                    # Directory node
                    if part not in node:
                        node[part] = {}
                    node = node[part]

        return tree

    def _generate_merge_report(
        self,
        feature_name: str,
        project_name: str,
        generated_files: list[GeneratedFile],
        updated_files: list[GeneratedFile],
        unchanged_files: list[GeneratedFile],
        version: int,
    ) -> str:
        """
        Generate a human-readable Markdown merge report.

        The report is saved as an artifact so human reviewers can
        understand exactly what changed in this iteration.

        Args:
            feature_name:    Current feature name.
            project_name:    Project name.
            generated_files: New files created.
            updated_files:   Existing files modified.
            unchanged_files: Files preserved unchanged.
            version:         Artifact version number.

        Returns:
            Markdown string.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %Human:%M:%S UTC")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines: list[str] = [
            f"# Merge Report — {feature_name}",
            "",
            f"**Project:** {project_name}",
            f"**Feature:** {feature_name}",
            f"**Artifact Version:** v{version}",
            f"**Generated At:** {timestamp}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"| Category | Count |",
            f"|---|---|",
            f"| 🆕 New files generated | {len(generated_files)} |",
            f"| ✏️  Existing files updated | {len(updated_files)} |",
            f"| ✅ Existing files preserved | {len(unchanged_files)} |",
            f"| **Total files** | **{len(generated_files) + len(updated_files) + len(unchanged_files)}** |",
            "",
            "---",
        ]

        if generated_files:
            lines += [
                "",
                "## 🆕 New Files Generated",
                "",
                "These files were created for the first time in this iteration.",
                "",
            ]
            for f in generated_files:
                lines += [
                    f"### `{f.file_path}`",
                    f"**Purpose:** {f.purpose}",
                    f"{f.description}",
                    "",
                ]

        if updated_files:
            lines += [
                "",
                "## ✏️ Updated Files",
                "",
                "These existing files were modified to support the new feature.",
                "",
            ]
            for f in updated_files:
                lines += [
                    f"### `{f.file_path}`",
                    f"**Purpose:** {f.purpose}",
                    f"{f.description}",
                    "",
                ]

        if unchanged_files:
            lines += [
                "",
                "## ✅ Preserved Files (Unchanged)",
                "",
                "These files were NOT modified. Previous feature code is fully preserved.",
                "",
                "| File Path |",
                "|---|",
            ]
            for f in unchanged_files:
                lines.append(f"| `{f.file_path}` |")

        lines += [
            "",
            "---",
            "",
            "> Generated by Coder Agent — Auto-Forge MAS",
        ]

        return "\n".join(lines)


# Module-level singleton
project_merger = ProjectMerger()
