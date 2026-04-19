"""Orchestrator: Manages the Generator-Reviewer pipeline with single-pass refinement."""

import logging
from typing import Optional
from agents.generator import GeneratorAgent
from agents.reviewer import ReviewerAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the Generator and Reviewer agents through a generate-review-refine pipeline."""

    def __init__(self, api_key: Optional[str] = None):
        self.generator = GeneratorAgent(api_key=api_key)
        self.reviewer = ReviewerAgent(api_key=api_key)

    def run_pipeline(self, grade: int, topic: str) -> dict:
        """
        Execute the full content generation pipeline.

        Flow:
            1. Generate initial content
            2. Review the content
            3. If review fails, refine once and re-review

        Args:
            grade: Student grade level (1-12).
            topic: Subject topic for content generation.

        Returns:
            Dict containing all pipeline outputs and final status.
        """
        result = {
            "grade": grade,
            "topic": topic,
            "generator_output": None,
            "initial_reviewer_output": None,
            "refined_output": None,
            "refined_reviewer_output": None,
            "final_status": "pending"
        }

        logger.info("Generating content for Grade %d: %s", grade, topic)
        generator_output = self.generator.generate(grade, topic)
        result["generator_output"] = generator_output

        if "error" in generator_output:
            result["final_status"] = "fail"
            return result

        logger.info("Reviewing generated content")
        reviewer_output = self.reviewer.review(grade, topic, generator_output)
        result["initial_reviewer_output"] = reviewer_output

        if reviewer_output["status"] == "pass":
            result["final_status"] = "pass"
            return result

        logger.info("Content failed review, running refinement")
        feedback_text = "\n".join(reviewer_output.get("feedback", []))
        refined_output = self.generator.generate(grade, topic, feedback=feedback_text)
        result["refined_output"] = refined_output

        if "error" in refined_output:
            result["final_status"] = "fail"
            return result

        logger.info("Re-reviewing refined content")
        refined_review = self.reviewer.review(grade, topic, refined_output)
        result["refined_reviewer_output"] = refined_review
        result["final_status"] = refined_review["status"]

        return result
