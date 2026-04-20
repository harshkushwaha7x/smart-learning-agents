"""Refiner Agent: Improves content based on structured reviewer feedback."""

from typing import Optional, Tuple
from agents.generator import GeneratorAgent
from schemas.models import GeneratedContent, ReviewResult


class RefinerAgent:

    def __init__(self, api_key: Optional[str] = None):
        self.generator = GeneratorAgent(api_key=api_key)

    def refine(
        self,
        grade: int,
        topic: str,
        current_content: GeneratedContent,
        review_result: ReviewResult,
        attempt_number: int
    ) -> Tuple[Optional[GeneratedContent], Optional[str]]:
        feedback_lines = []

        scores = review_result.scores
        feedback_lines.append("SCORE SUMMARY:")
        for criterion, score in scores.items():
            feedback_lines.append(f"- {criterion.replace('_', ' ').title()}: {score}/5")
        feedback_lines.append(f"- Average: {review_result.average_score:.1f}/5")
        feedback_lines.append("")

        if review_result.feedback:
            feedback_lines.append("SPECIFIC ISSUES:")
            for fb in review_result.feedback:
                feedback_lines.append(f"- Field '{fb.field}': {fb.issue} (severity: {fb.severity.value})")
        else:
            feedback_lines.append("No specific feedback items provided.")

        feedback_lines.append("")
        feedback_lines.append("INSTRUCTION: Improve the content to address all issues above.")
        feedback_text = "\n".join(feedback_lines)

        refined, error = self.generator.generate(
            grade=grade,
            topic=topic,
            feedback=feedback_text
        )

        if error:
            return None, f"Refinement generation failed: {error}"

        return refined, None
