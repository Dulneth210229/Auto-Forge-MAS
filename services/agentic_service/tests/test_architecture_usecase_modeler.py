"""
Unit tests for ArchitectureUseCaseModeler (app/agents/architecture_agent/usecase_modeler.py).
No LLM involved -- these exercise the deterministic modeling logic directly.

Covers the two build() paths:
- LLM-specification path (specification["use_cases"] non-empty): the
  modeler must trust the LLM's names/categorization directly (no regex
  phrase-surgery) and merge near-duplicates via the three-pass
  _merge_near_duplicates (exact name, shared related_requirements, name
  stem similarity).
- Fallback path (specification empty): the last-resort deterministic
  builder must produce a clean main use case named from feature_name
  alone (no business-goal regex-mangling) and honest, non-garbled
  supporting use case names (via _build_fallback_supporting_use_case).

These fixtures are based on the real, confirmed-garbled examples recorded
in the approved rewrite plan (Task Comments, Login) to directly verify
those failure modes no longer occur.
"""

from app.agents.architecture_agent.usecase_modeler import ArchitectureUseCaseModeler


def _relationships_by_type(usecase_json: dict, relation_type: str) -> list[dict]:
    return [r for r in usecase_json["relationships"] if r["type"] == relation_type]


def _names(use_cases: list[dict]) -> list[str]:
    return [uc["name"] for uc in use_cases]


class TestLlmSpecificationPath:
    def test_trusts_llm_names_and_categorization_directly(self):
        modeler = ArchitectureUseCaseModeler()

        srs_json = {
            "feature_name": "Task Comments",
            "user_roles": ["Team Member"],
            "functional_requirements": [
                {"id": "FR-001", "description": "Users can add a comment to a task."},
                {"id": "FR-002", "description": "Users can view comments on a task."},
                {"id": "FR-003", "description": "Users can delete their own comment."},
            ],
        }
        sds_json = {"design_views": {}}
        specification = {
            "system_boundary": "Task Comments",
            "diagram_title": "Task Comments Use Case Diagram",
            "actors": [{"name": "Team Member", "type": "primary"}],
            "use_cases": [
                {
                    "name": "Discuss Task",
                    "type": "main",
                    "description": "A team member discusses a task via comments.",
                    "related_requirements": ["FR-001", "FR-002"],
                },
                {
                    "name": "Add Comment",
                    "type": "included",
                    "description": "Add a comment to a task.",
                    "related_requirements": ["FR-001"],
                },
                {
                    "name": "View Comments",
                    "type": "included",
                    "description": "View comments on a task.",
                    "related_requirements": ["FR-002"],
                },
                {
                    "name": "Delete Own Comment",
                    "type": "extension",
                    "description": "Delete a comment the user authored.",
                    "related_requirements": ["FR-003"],
                },
            ],
        }

        analysis, usecase_json = modeler.build(
            srs_json=srs_json, sds_json=sds_json, usecase_specification_json=specification
        )

        names = _names(usecase_json["use_cases"])

        # The confirmed real garbled examples ("A Task The Can", "A Comment
        # The Authored") must never appear -- names are trusted as-is.
        assert "Discuss Task" in names
        assert "Add Comment" in names
        assert "View Comments" in names
        assert "Delete Own Comment" in names
        for name in names:
            assert "The Can" not in name
            assert "The Authored" not in name

        main = [uc for uc in usecase_json["use_cases"] if uc["category"] == "main"]
        assert len(main) == 1
        assert main[0]["name"] == "Discuss Task"

    def test_merges_exact_duplicate_names(self):
        modeler = ArchitectureUseCaseModeler()
        srs_json = {"feature_name": "Search", "functional_requirements": [{"id": "FR-001", "description": "x"}]}
        specification = {
            "use_cases": [
                {"name": "Search Tasks", "type": "main", "related_requirements": ["FR-001"]},
                {"name": "Filter Results", "type": "included", "related_requirements": ["FR-002"]},
                {"name": "filter results", "type": "included", "related_requirements": ["FR-003"]},
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json=specification)

        included = [uc for uc in usecase_json["use_cases"] if uc["category"] == "included"]
        assert len(included) == 1
        assert set(included[0]["related_requirements"]) == {"FR-002", "FR-003"}

    def test_merges_use_cases_sharing_identical_related_requirements(self):
        """
        Real confirmed near-duplicate: "Initiate Forgot Password Process" vs
        "Initiate Recovery Flow" citing the same FR -- no string-similarity
        metric would catch this (they share no meaningful stems), but citing
        the exact same requirement id set is a strong duplicate signal.
        """
        modeler = ArchitectureUseCaseModeler()
        srs_json = {"feature_name": "Login", "functional_requirements": [{"id": "FR-005", "description": "x"}]}
        specification = {
            "use_cases": [
                {"name": "Login", "type": "main", "related_requirements": ["FR-001"]},
                {
                    "name": "Initiate Forgot Password Process",
                    "type": "extension",
                    "related_requirements": ["FR-005"],
                },
                {
                    "name": "Initiate Recovery Flow",
                    "type": "extension",
                    "related_requirements": ["FR-005"],
                },
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json=specification)

        extensions = [uc for uc in usecase_json["use_cases"] if uc["category"] == "extension"]
        assert len(extensions) == 1
        assert extensions[0]["related_requirements"] == ["FR-005"]

    def test_merges_near_duplicate_names_by_stem_overlap(self):
        modeler = ArchitectureUseCaseModeler()
        srs_json = {"feature_name": "Checkout", "functional_requirements": [{"id": "FR-001", "description": "x"}]}
        specification = {
            "use_cases": [
                {"name": "Checkout", "type": "main", "related_requirements": ["FR-001"]},
                {"name": "Apply Discount Coupon", "type": "included", "related_requirements": ["FR-010"]},
                {"name": "Apply Discount Coupons", "type": "included", "related_requirements": ["FR-011"]},
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json=specification)

        included = [uc for uc in usecase_json["use_cases"] if uc["category"] == "included"]
        assert len(included) == 1
        assert set(included[0]["related_requirements"]) == {"FR-010", "FR-011"}

    def test_promotes_a_main_use_case_when_llm_produced_none(self):
        modeler = ArchitectureUseCaseModeler()
        srs_json = {"feature_name": "Search", "functional_requirements": [{"id": "FR-001", "description": "x"}]}
        specification = {
            "use_cases": [
                {"name": "Filter Results", "type": "included", "related_requirements": ["FR-001"]},
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json=specification)

        main = [uc for uc in usecase_json["use_cases"] if uc["category"] == "main"]
        assert len(main) == 1
        assert main[0]["name"] == "Filter Results"

    def test_folds_extra_main_entries_into_included(self):
        modeler = ArchitectureUseCaseModeler()
        srs_json = {"feature_name": "Search", "functional_requirements": [{"id": "FR-001", "description": "x"}]}
        specification = {
            "use_cases": [
                {"name": "Search Tasks", "type": "main", "related_requirements": ["FR-001"]},
                {"name": "Export Results", "type": "main", "related_requirements": ["FR-002"]},
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json=specification)

        main = [uc for uc in usecase_json["use_cases"] if uc["category"] == "main"]
        included = [uc for uc in usecase_json["use_cases"] if uc["category"] == "included"]
        assert len(main) == 1
        assert main[0]["name"] == "Search Tasks"
        assert "Export Results" in _names(included)


class TestFallbackPath:
    def test_main_use_case_named_from_feature_name_only(self):
        """
        The fallback path must never regex-mangle a business_goal sentence
        into the main use case name -- feature_name is already a reasonable,
        conventional UML use case name (e.g. "Login").
        """
        modeler = ArchitectureUseCaseModeler()
        srs_json = {
            "feature_name": "Login",
            "business_goal": "Allow registered users to authenticate using their credentials.",
            "functional_requirements": [{"id": "FR-001", "description": "x"}],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json={})

        main = [uc for uc in usecase_json["use_cases"] if uc["category"] == "main"]
        assert len(main) == 1
        assert main[0]["name"] == "Login"

    def test_fallback_supporting_use_case_uses_matching_user_story_goal(self):
        modeler = ArchitectureUseCaseModeler()
        srs_json = {
            "feature_name": "Login",
            "user_stories": [
                {"id": "US-001", "role": "User", "goal": "Authenticate with my credentials", "benefit": "access my account"},
            ],
            "functional_requirements": [
                {"id": "FR-001", "description": "The system must validate the user credentials against stored records."},
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json={})

        included = [uc for uc in usecase_json["use_cases"] if uc["category"] == "included"]
        assert len(included) == 1
        assert included[0]["name"] == "Authenticate With Credentials"

    def test_fallback_supporting_use_case_falls_back_to_gentle_truncation(self):
        """
        No matching user story -- a single gentle pass (strip boilerplate
        lead-in, keep ~5 words, title-case) via _clean_use_case_name, not
        multi-pass regex verb/topic extraction.
        """
        modeler = ArchitectureUseCaseModeler()
        srs_json = {
            "feature_name": "Login",
            "user_stories": [],
            "functional_requirements": [
                {"id": "FR-001", "description": "The system must validate the user credentials against stored records."},
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json={})

        included = [uc for uc in usecase_json["use_cases"] if uc["category"] == "included"]
        assert len(included) == 1
        # No leftover article/pronoun fragment words in the fallback name.
        name_words = {w.lower() for w in included[0]["name"].split()}
        assert not name_words & {"the", "a", "an", "this", "that"}

    def test_fallback_preserves_full_fr_traceability(self):
        modeler = ArchitectureUseCaseModeler()
        srs_json = {
            "feature_name": "Login",
            "functional_requirements": [
                {"id": "FR-001", "description": "The system must validate the user credentials."},
                {"id": "FR-002", "description": "The system must display an error for invalid credentials."},
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json={})

        covered_ids: set[str] = set()
        for uc in usecase_json["use_cases"]:
            covered_ids.update(uc.get("related_requirements", []))
        assert {"FR-001", "FR-002"}.issubset(covered_ids)

    def test_fallback_relationships_are_correctly_wired(self):
        modeler = ArchitectureUseCaseModeler()
        srs_json = {
            "feature_name": "Login",
            "functional_requirements": [
                {"id": "FR-001", "description": "The system must validate the user credentials."},
                {"id": "FR-002", "description": "The system must display an error for invalid credentials."},
            ],
        }

        _, usecase_json = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, usecase_specification_json={})

        main_id = next(uc["id"] for uc in usecase_json["use_cases"] if uc["category"] == "main")

        for rel in _relationships_by_type(usecase_json, "include"):
            assert rel["from"] == main_id

        for rel in _relationships_by_type(usecase_json, "extend"):
            assert rel["to"] == main_id

        for rel in _relationships_by_type(usecase_json, "association"):
            assert rel["to"] == main_id
