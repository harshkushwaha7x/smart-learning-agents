"""Orchestrator: Deterministic pipeline producing complete RunArtifacts."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from agents.generator import GeneratorAgent
from agents.reviewer import ReviewerAgent
from agents.refiner import RefinerAgent
from agents.tagger import TaggerAgent
from config import MAX_REFINEMENT_ATTEMPTS
from schemas.models import (
    GenerationInput,
    GeneratedContent,
    ReviewResult,
    Attempt,
    AttemptStatus,
    ContentStatus,
    FinalResult,
    RunArtifact,
)


class Orchestrator:
    """Deterministic pipeline: Generate → Review → Refine (if needed) → Tag (if approved)."""

    def __init__(self, api_key: Optional[str] = None):
        self.generator = GeneratorAgent(api_key=api_key)
        self.reviewer = ReviewerAgent(api_key=api_key)
        self.refiner = RefinerAgent(api_key=api_key)
        self.tagger = TaggerAgent(api_key=api_key)

    def execute(
        self,
        grade: int,
        topic: str,
        user_id: Optional[str] = None
    ) -> RunArtifact:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(timezone.utc)
        input_data = GenerationInput(grade=grade, topic=topic)
        attempts = []

        final_status = ContentStatus.REJECTED
        final_content = None
        final_tags = None

        attempt_1, content_1, review_1 = self._attempt_generate_and_review(
            attempt_num=1, grade=grade, topic=topic,
        )
        attempts.append(attempt_1)

        if review_1 and review_1.pass_overall:
            final_status = ContentStatus.APPROVED
            final_content = content_1
            final_tags = self._run_tagger(grade, topic, content_1)
        else:
            current_content = content_1
            current_review = review_1

            for refinement_num in range(1, MAX_REFINEMENT_ATTEMPTS + 1):
                if not current_content or not current_review:
                    break

                attempt_n, refined_content, new_review = self._attempt_refine_and_review(
                    attempt_num=1 + refinement_num,
                    grade=grade,
                    topic=topic,
                    current_content=current_content,
                    review_result=current_review,
                )
                attempts.append(attempt_n)

                if new_review and new_review.pass_overall:
                    final_status = ContentStatus.APPROVED
                    final_content = refined_content
                    final_tags = self._run_tagger(grade, topic, refined_content)
                    break

                current_content = refined_content
                current_review = new_review

        finished_at = datetime.now(timezone.utc)

        artifact = RunArtifact(
            run_id=run_id,
            input=input_data,
            attempts=attempts,
            final=FinalResult(
                status=final_status,
                content=final_content,
                tags=final_tags,
            ),
            timestamps={
                "started_at": started_at,
                "finished_at": finished_at,
            },
            user_id=user_id,
        )

        return artifact

    def _attempt_generate_and_review(
        self,
        attempt_num: int,
        grade: int,
        topic: str,
    ) -> tuple:
        timestamp_start = datetime.now(timezone.utc)
        attempt_status = AttemptStatus.FAIL
        generated_content = None
        review_result = None

        gen_content, gen_error = self.generator.generate(grade, topic)

        if gen_content:
            generated_content = gen_content
            rev_result, rev_error = self.reviewer.review(grade, topic, gen_content)
            if rev_result:
                review_result = rev_result
                attempt_status = AttemptStatus.PASS if rev_result.pass_overall else AttemptStatus.FAIL

        timestamp_end = datetime.now(timezone.utc)

        attempt = Attempt(
            attempt_number=attempt_num,
            status=attempt_status,
            draft=generated_content,
            review=review_result,
            refined=None,
            refinement_feedback=None,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

        return attempt, generated_content, review_result

    def _attempt_refine_and_review(
        self,
        attempt_num: int,
        grade: int,
        topic: str,
        current_content: GeneratedContent,
        review_result: ReviewResult,
    ) -> tuple:
        timestamp_start = datetime.now(timezone.utc)
        attempt_status = AttemptStatus.FAIL
        refined_content = None
        new_review = None

        feedback_lines = ["REVIEWER FEEDBACK:"]
        feedback_lines.append(f"Average Score: {review_result.average_score:.1f}/5")
        feedback_lines.append("")
        if review_result.feedback:
            for fb in review_result.feedback:
                feedback_lines.append(f"- {fb.field}: {fb.issue}")
        refinement_feedback = "\n".join(feedback_lines)

        refined, refine_error = self.refiner.refine(
            grade=grade,
            topic=topic,
            current_content=current_content,
            review_result=review_result,
            attempt_number=attempt_num,
        )

        if refined:
            refined_content = refined
            new_rev, new_rev_error = self.reviewer.review(grade, topic, refined)
            if new_rev:
                new_review = new_rev
                attempt_status = AttemptStatus.PASS if new_rev.pass_overall else AttemptStatus.FAIL

        timestamp_end = datetime.now(timezone.utc)

        attempt = Attempt(
            attempt_number=attempt_num,
            status=attempt_status,
            draft=None,
            review=new_review,
            refined=refined_content,
            refinement_feedback=refinement_feedback,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

        return attempt, refined_content, new_review

    def _run_tagger(self, grade: int, topic: str, content: GeneratedContent):
        tags, _ = self.tagger.tag(grade, topic, content)
        return tags
