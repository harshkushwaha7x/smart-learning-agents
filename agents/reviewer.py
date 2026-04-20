"""Reviewer Agent: Quantitative evaluation with deterministic pass/fail."""

import json
from typing import Optional, Tuple
from openai import OpenAI
from pydantic import ValidationError
from schemas.models import GeneratedContent, ReviewResult, ReviewFeedback, Severity
from config import MIN_AVERAGE_SCORE, MIN_INDIVIDUAL_SCORE, OPENAI_MODEL, REVIEW_TEMPERATURE


class ReviewerAgent:

    CRITERIA = [
        "age_appropriateness",
        "correctness",
        "clarity",
        "coverage",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)
        self.model = OPENAI_MODEL

    def review(
        self,
        grade: int,
        topic: str,
        content: GeneratedContent
    ) -> Tuple[Optional[ReviewResult], Optional[str]]:
        prompt = self._build_prompt(grade, topic, content)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=REVIEW_TEMPERATURE,
            )
            review_text = response.choices[0].message.content
            return self._parse_and_validate(review_text)
        except Exception as e:
            return None, f"Review API call failed: {str(e)}"

    def _build_prompt(self, grade: int, topic: str, content: GeneratedContent) -> str:
        explanation = content.explanation.text
        mcqs = content.mcqs
        teacher_notes = content.teacher_notes

        mcqs_text = ""
        for i, mcq in enumerate(mcqs, 1):
            options_str = "\n".join([f"  {chr(65 + j)}: {opt}" for j, opt in enumerate(mcq.options)])
            correct_letter = chr(65 + mcq.correct_index)
            mcqs_text += f"\nQuestion {i}: {mcq.question}\n{options_str}\nCorrect: {correct_letter}\n"

        return f"""You are an expert educational content evaluator. Review this content created for Grade {grade} students on: "{topic}".

EXPLANATION:
{explanation}

MULTIPLE CHOICE QUESTIONS:
{mcqs_text}

TEACHER NOTES:
Learning Objective: {teacher_notes.learning_objective}
Common Misconceptions: {', '.join(teacher_notes.common_misconceptions) if teacher_notes.common_misconceptions else 'None listed'}

EVALUATION CRITERIA:
1. Age Appropriateness (1-5): Is language, complexity, and concepts suitable for Grade {grade}?
2. Correctness (1-5): Are all facts and concepts factually accurate and well-explained?
3. Clarity (1-5): Is the explanation clear and understandable? Are questions unambiguous?
4. Coverage (1-5): Does content adequately cover the topic with sufficient depth?

SCORING RULES:
- Score each criterion 1-5 (1=poor, 5=excellent)
- Be critical but fair
- Average score must be >={MIN_AVERAGE_SCORE} to pass
- No individual score can be <{MIN_INDIVIDUAL_SCORE}
- Return ONLY valid JSON with NO other text:

{{
    "age_appropriateness": <1-5>,
    "correctness": <1-5>,
    "clarity": <1-5>,
    "coverage": <1-5>,
    "feedback": [
        {{
            "field": "explanation.text",
            "issue": "Specific issue or leave empty if no issue",
            "severity": "low|medium|high"
        }}
    ]
}}

Return ONLY the JSON, nothing else."""

    def _parse_and_validate(
        self,
        content: str
    ) -> Tuple[Optional[ReviewResult], Optional[str]]:
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError as e:
            return None, f"Invalid review JSON: {str(e)}"

        try:
            scores = {
                "age_appropriateness": int(data.get("age_appropriateness", 1)),
                "correctness": int(data.get("correctness", 1)),
                "clarity": int(data.get("clarity", 1)),
                "coverage": int(data.get("coverage", 1)),
            }

            for criterion, score in scores.items():
                if not (1 <= score <= 5):
                    return None, f"Invalid score for {criterion}: {score} (must be 1-5)"

            average_score = sum(scores.values()) / len(scores)

            if any(s < MIN_INDIVIDUAL_SCORE for s in scores.values()):
                pass_overall = False
            elif average_score >= MIN_AVERAGE_SCORE:
                pass_overall = True
            else:
                pass_overall = False

            feedback = []
            for fb in data.get("feedback", []):
                if isinstance(fb, dict):
                    issue = fb.get("issue", "").strip()
                    if issue:
                        severity_raw = fb.get("severity", "medium").lower()
                        try:
                            severity = Severity(severity_raw)
                        except ValueError:
                            severity = Severity.MEDIUM
                        try:
                            feedback_item = ReviewFeedback(
                                field=fb.get("field", ""),
                                issue=issue,
                                severity=severity,
                            )
                            feedback.append(feedback_item)
                        except ValidationError:
                            pass

            review_result = ReviewResult(
                scores=scores,
                pass_overall=pass_overall,
                average_score=average_score,
                feedback=feedback,
            )
            return review_result, None

        except (KeyError, ValueError, ValidationError) as e:
            return None, f"Failed to parse review structure: {str(e)}"
