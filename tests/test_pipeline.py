"""Comprehensive tests for the Governed AI Content Pipeline."""

import os
import json
import tempfile
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from agents.generator import GeneratorAgent
from agents.reviewer import ReviewerAgent
from agents.refiner import RefinerAgent
from agents.tagger import TaggerAgent
from agents.orchestrator import Orchestrator
from storage.store import ArtifactStore
from schemas.models import (
    GeneratedContent,
    Explanation,
    MCQ,
    TeacherNotes,
    ReviewResult,
    ReviewFeedback,
    Tags,
    RunArtifact,
    FinalResult,
    ContentStatus,
    Severity,
    Difficulty,
    BloomsLevel,
)


@pytest.fixture
def valid_content():
    return GeneratedContent(
        explanation=Explanation(
            text="A fraction represents a part of a whole. When you divide something into equal parts, each part is a fraction of the whole. For example, if you cut a pizza into 4 equal slices and eat 1 slice, you have eaten 1/4 of the pizza.",
            grade=5
        ),
        mcqs=[
            MCQ(question="What is 1/2 of 8?", options=["2", "4", "6", "8"], correct_index=1),
            MCQ(question="Which fraction is larger, 1/2 or 1/4?", options=["1/2", "1/4", "They are equal", "Cannot determine"], correct_index=0),
            MCQ(question="If a pizza has 8 slices and you eat 2, what fraction did you eat?", options=["1/8", "2/8", "2/6", "1/2"], correct_index=1),
            MCQ(question="What does the bottom number in a fraction represent?", options=["The number eaten", "The total number of parts", "The numerator", "The size of each part"], correct_index=1),
        ],
        teacher_notes=TeacherNotes(
            learning_objective="Students will understand fractions as parts of a whole",
            common_misconceptions=["Thinking larger denominator means larger fraction", "Not recognizing equivalent fractions"]
        )
    )


@pytest.fixture
def passing_review():
    return ReviewResult(
        scores={"age_appropriateness": 5, "correctness": 5, "clarity": 4, "coverage": 4},
        pass_overall=True,
        average_score=4.5,
        feedback=[]
    )


@pytest.fixture
def failing_review():
    return ReviewResult(
        scores={"age_appropriateness": 3, "correctness": 2, "clarity": 3, "coverage": 3},
        pass_overall=False,
        average_score=2.75,
        feedback=[
            ReviewFeedback(field="explanation.text", issue="Language too complex for grade 5", severity=Severity.HIGH),
            ReviewFeedback(field="mcqs[0].question", issue="Question is ambiguous", severity=Severity.MEDIUM),
        ]
    )


@pytest.fixture
def sample_tags():
    return Tags(
        subject="Mathematics",
        topic="Fractions",
        grade=5,
        difficulty=Difficulty.MEDIUM,
        content_type=["Explanation", "Quiz"],
        blooms_level=BloomsLevel.UNDERSTANDING,
    )


class TestSchemaValidation:

    def test_generator_returns_content_on_valid_json(self, valid_content):
        gen = GeneratorAgent(api_key="test-key")
        valid_json = valid_content.model_dump_json()

        with patch.object(gen.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content=valid_json))])
            content, error = gen.generate(grade=5, topic="Fractions")

            assert content is not None
            assert error is None
            assert isinstance(content, GeneratedContent)
            assert content.explanation.grade == 5

    def test_generator_returns_error_on_invalid_json(self):
        gen = GeneratorAgent(api_key="test-key")

        with patch.object(gen.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content="{ invalid json ]"))])
            content, error = gen.generate(grade=5, topic="Fractions")

            assert content is None
            assert error is not None
            assert "Invalid JSON" in error

    def test_generator_validation_error_on_missing_mcqs(self):
        gen = GeneratorAgent(api_key="test-key")
        invalid_output = {
            "explanation": {"text": "Short text here", "grade": 5},
            "teacher_notes": {"learning_objective": "Learn", "common_misconceptions": []}
        }

        with patch.object(gen.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content=json.dumps(invalid_output)))])
            content, error = gen.generate(grade=5, topic="Fractions")

            assert content is None
            assert error is not None
            assert "Schema validation failed" in error

    def test_generator_validation_error_on_wrong_mcq_count(self):
        gen = GeneratorAgent(api_key="test-key")
        invalid_output = {
            "explanation": {"text": "A fraction represents a part of a whole. " * 5, "grade": 5},
            "mcqs": [
                {"question": "What is 1/2 of 8?", "options": ["2", "4", "6", "8"], "correct_index": 0},
            ],
            "teacher_notes": {"learning_objective": "Learn", "common_misconceptions": []}
        }

        with patch.object(gen.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content=json.dumps(invalid_output)))])
            content, error = gen.generate(grade=5, topic="Fractions")

            assert content is None
            assert error is not None

    def test_review_result_requires_all_four_score_keys(self):
        with pytest.raises(Exception):
            ReviewResult(
                scores={"age_appropriateness": 5, "correctness": 5},
                pass_overall=True,
                average_score=5.0,
                feedback=[]
            )

    def test_review_result_rejects_out_of_range_scores(self):
        with pytest.raises(Exception):
            ReviewResult(
                scores={"age_appropriateness": 6, "correctness": 5, "clarity": 5, "coverage": 5},
                pass_overall=True,
                average_score=5.25,
                feedback=[]
            )


class TestGeneratorRetry:

    def test_generator_retries_on_first_validation_failure(self, valid_content):
        gen = GeneratorAgent(api_key="test-key")
        valid_json = valid_content.model_dump_json()

        with patch.object(gen.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = [
                Mock(choices=[Mock(message=Mock(content="{ invalid }"))]),
                Mock(choices=[Mock(message=Mock(content=valid_json))]),
            ]
            content, error = gen.generate(grade=5, topic="Fractions")

            assert content is not None
            assert error is None
            assert mock_create.call_count == 2

    def test_generator_fails_after_max_retries(self):
        gen = GeneratorAgent(api_key="test-key")

        with patch.object(gen.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content="{ bad json }"))])
            content, error = gen.generate(grade=5, topic="Fractions")

            assert content is None
            assert error is not None
            assert mock_create.call_count == 2


class TestReviewerScoring:

    def test_reviewer_passes_on_high_scores(self, valid_content):
        rev = ReviewerAgent(api_key="test-key")
        review_json = json.dumps({
            "age_appropriateness": 5, "correctness": 5, "clarity": 4, "coverage": 4,
            "feedback": []
        })

        with patch.object(rev.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content=review_json))])
            result, error = rev.review(5, "Fractions", valid_content)

            assert result is not None
            assert result.pass_overall is True
            assert result.average_score == 4.5

    def test_reviewer_fails_on_low_average(self, valid_content):
        rev = ReviewerAgent(api_key="test-key")
        review_json = json.dumps({
            "age_appropriateness": 3, "correctness": 3, "clarity": 3, "coverage": 3,
            "feedback": []
        })

        with patch.object(rev.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content=review_json))])
            result, error = rev.review(5, "Fractions", valid_content)

            assert result is not None
            assert result.pass_overall is False

    def test_reviewer_fails_on_individual_score_below_threshold(self, valid_content):
        rev = ReviewerAgent(api_key="test-key")
        review_json = json.dumps({
            "age_appropriateness": 5, "correctness": 2, "clarity": 4, "coverage": 4,
            "feedback": []
        })

        with patch.object(rev.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content=review_json))])
            result, error = rev.review(5, "Fractions", valid_content)

            assert result is not None
            assert result.pass_overall is False

    def test_reviewer_includes_structured_feedback(self, valid_content):
        rev = ReviewerAgent(api_key="test-key")
        review_json = json.dumps({
            "age_appropriateness": 3, "correctness": 2, "clarity": 3, "coverage": 3,
            "feedback": [
                {"field": "explanation.text", "issue": "Too complex", "severity": "high"},
                {"field": "mcqs[0].question", "issue": "Ambiguous", "severity": "medium"}
            ]
        })

        with patch.object(rev.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = Mock(choices=[Mock(message=Mock(content=review_json))])
            result, error = rev.review(5, "Fractions", valid_content)

            assert result is not None
            assert len(result.feedback) == 2
            assert result.feedback[0].field == "explanation.text"
            assert result.feedback[0].severity == Severity.HIGH


class TestRefiner:

    def test_refiner_passes_feedback_to_generator(self, valid_content, failing_review):
        refiner = RefinerAgent(api_key="test-key")
        refined = GeneratedContent(
            explanation=Explanation(text="A fraction shows a part of a whole using simple language. " * 3, grade=5),
            mcqs=valid_content.mcqs,
            teacher_notes=valid_content.teacher_notes,
        )

        with patch.object(refiner.generator, 'generate') as mock_gen:
            mock_gen.return_value = (refined, None)
            result, error = refiner.refine(
                grade=5, topic="Fractions",
                current_content=valid_content,
                review_result=failing_review,
                attempt_number=2
            )

            assert result is not None
            assert error is None
            call_kwargs = mock_gen.call_args[1]
            assert "feedback" in call_kwargs
            assert "SCORE SUMMARY" in call_kwargs["feedback"]


class TestOrchestratorFailRefinePass:

    def test_fail_then_refine_then_pass(self, valid_content, failing_review, passing_review, sample_tags):
        orch = Orchestrator(api_key="test-key")

        with patch.object(orch.generator, 'generate') as mock_gen, \
             patch.object(orch.reviewer, 'review') as mock_rev, \
             patch.object(orch.refiner, 'refine') as mock_refine, \
             patch.object(orch.tagger, 'tag') as mock_tag:

            mock_gen.return_value = (valid_content, None)
            mock_rev.side_effect = [(failing_review, None), (passing_review, None)]
            mock_refine.return_value = (valid_content, None)
            mock_tag.return_value = (sample_tags, None)

            artifact = orch.execute(grade=5, topic="Fractions")

            assert artifact.final.status == ContentStatus.APPROVED
            assert len(artifact.attempts) == 2
            assert artifact.attempts[0].status.value == "fail"
            assert artifact.attempts[1].status.value == "pass"
            mock_tag.assert_called_once()


class TestOrchestratorFailRefineFailReject:

    def test_reject_after_max_attempts(self, valid_content, failing_review):
        orch = Orchestrator(api_key="test-key")

        with patch.object(orch.generator, 'generate') as mock_gen, \
             patch.object(orch.reviewer, 'review') as mock_rev, \
             patch.object(orch.refiner, 'refine') as mock_refine, \
             patch.object(orch.tagger, 'tag') as mock_tag:

            mock_gen.return_value = (valid_content, None)
            mock_rev.return_value = (failing_review, None)
            mock_refine.return_value = (valid_content, None)

            artifact = orch.execute(grade=5, topic="Fractions")

            assert artifact.final.status == ContentStatus.REJECTED
            assert artifact.final.content is None
            assert artifact.final.tags is None
            assert len(artifact.attempts) == 3
            mock_tag.assert_not_called()


class TestTaggerApprovedOnly:

    def test_tagger_not_called_on_rejection(self, valid_content, failing_review):
        orch = Orchestrator(api_key="test-key")

        with patch.object(orch.generator, 'generate') as mock_gen, \
             patch.object(orch.reviewer, 'review') as mock_rev, \
             patch.object(orch.refiner, 'refine') as mock_refine, \
             patch.object(orch.tagger, 'tag') as mock_tag:

            mock_gen.return_value = (valid_content, None)
            mock_rev.return_value = (failing_review, None)
            mock_refine.return_value = (valid_content, None)

            artifact = orch.execute(grade=5, topic="Fractions")

            assert artifact.final.status == ContentStatus.REJECTED
            mock_tag.assert_not_called()

    def test_tagger_called_on_approval(self, valid_content, passing_review, sample_tags):
        orch = Orchestrator(api_key="test-key")

        with patch.object(orch.generator, 'generate') as mock_gen, \
             patch.object(orch.reviewer, 'review') as mock_rev, \
             patch.object(orch.tagger, 'tag') as mock_tag:

            mock_gen.return_value = (valid_content, None)
            mock_rev.return_value = (passing_review, None)
            mock_tag.return_value = (sample_tags, None)

            artifact = orch.execute(grade=5, topic="Fractions")

            assert artifact.final.status == ContentStatus.APPROVED
            mock_tag.assert_called_once()


class TestRunArtifactStructure:

    def test_artifact_has_all_required_fields(self, valid_content, passing_review, sample_tags):
        orch = Orchestrator(api_key="test-key")

        with patch.object(orch.generator, 'generate') as mock_gen, \
             patch.object(orch.reviewer, 'review') as mock_rev, \
             patch.object(orch.tagger, 'tag') as mock_tag:

            mock_gen.return_value = (valid_content, None)
            mock_rev.return_value = (passing_review, None)
            mock_tag.return_value = (sample_tags, None)

            artifact = orch.execute(grade=5, topic="Fractions", user_id="user_123")

            assert artifact.run_id.startswith("run_")
            assert artifact.input.grade == 5
            assert artifact.input.topic == "Fractions"
            assert len(artifact.attempts) > 0
            assert artifact.final.status in [ContentStatus.APPROVED, ContentStatus.REJECTED]
            assert artifact.timestamps["started_at"] is not None
            assert artifact.timestamps["finished_at"] is not None
            assert artifact.user_id == "user_123"

    def test_artifact_serialization_roundtrip(self, valid_content, passing_review, sample_tags):
        orch = Orchestrator(api_key="test-key")

        with patch.object(orch.generator, 'generate') as mock_gen, \
             patch.object(orch.reviewer, 'review') as mock_rev, \
             patch.object(orch.tagger, 'tag') as mock_tag:

            mock_gen.return_value = (valid_content, None)
            mock_rev.return_value = (passing_review, None)
            mock_tag.return_value = (sample_tags, None)

            artifact = orch.execute(grade=5, topic="Fractions")
            json_str = artifact.model_dump_json()
            restored = RunArtifact(**json.loads(json_str))

            assert restored.run_id == artifact.run_id
            assert restored.final.status == artifact.final.status


class TestStorageReadWrite:

    def test_store_and_retrieve_artifact(self, valid_content, passing_review, sample_tags):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = ArtifactStore(db_path=db_path)
            orch = Orchestrator(api_key="test-key")

            with patch.object(orch.generator, 'generate') as mock_gen, \
                 patch.object(orch.reviewer, 'review') as mock_rev, \
                 patch.object(orch.tagger, 'tag') as mock_tag:

                mock_gen.return_value = (valid_content, None)
                mock_rev.return_value = (passing_review, None)
                mock_tag.return_value = (sample_tags, None)

                artifact = orch.execute(grade=5, topic="Fractions", user_id="test_user")
                store.store(artifact)

                retrieved = store.get_by_run_id(artifact.run_id)
                assert retrieved is not None
                assert retrieved.run_id == artifact.run_id
                assert retrieved.final.status == ContentStatus.APPROVED

                assert store.count_total() == 1
                assert store.count_by_user("test_user") == 1

                user_artifacts = store.get_by_user_id("test_user")
                assert len(user_artifacts) == 1

        finally:
            os.unlink(db_path)

    def test_get_nonexistent_run_id(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = ArtifactStore(db_path=db_path)
            result = store.get_by_run_id("nonexistent_id")
            assert result is None
        finally:
            os.unlink(db_path)


class TestAPIEndpoints:

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        from api.backend import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self):
        from fastapi.testclient import TestClient
        from api.backend import app

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "endpoints" in data

    def test_stats_endpoint(self):
        from fastapi.testclient import TestClient
        from api.backend import app

        client = TestClient(app)
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_artifacts" in data

    def test_history_endpoint(self):
        from fastapi.testclient import TestClient
        from api.backend import app

        client = TestClient(app)
        response = client.get("/history")
        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data
        assert "artifacts" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
