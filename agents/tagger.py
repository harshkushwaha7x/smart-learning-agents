"""Tagger Agent: Generates metadata tags for approved content only."""

import json
from typing import Optional, Tuple
from openai import OpenAI
from pydantic import ValidationError
from schemas.models import GeneratedContent, Tags, Difficulty, BloomsLevel
from config import OPENAI_MODEL


class TaggerAgent:

    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)
        self.model = OPENAI_MODEL

    def tag(
        self,
        grade: int,
        topic: str,
        content: GeneratedContent
    ) -> Tuple[Optional[Tags], Optional[str]]:
        prompt = self._build_prompt(grade, topic, content)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            tags_text = response.choices[0].message.content
            return self._parse_and_validate(tags_text, grade, topic)
        except Exception as e:
            return None, f"Tagging API call failed: {str(e)}"

    def _build_prompt(self, grade: int, topic: str, content: GeneratedContent) -> str:
        explanation = content.explanation.text[:200]
        learning_objective = content.teacher_notes.learning_objective

        return f"""You are an educational content curator. Generate metadata tags for this approved content for Grade {grade} students.

CONTENT SUMMARY:
Topic: {topic}
Grade: {grade}
Learning Objective: {learning_objective}

EXPLANATION EXCERPT:
{explanation}

TAGGING RULES:
1. Subject: Mathematics | Science | Language Arts | Social Studies | Other
2. Topic: The specific topic (3-5 words)
3. Grade: {grade}
4. Difficulty: Easy | Medium | Hard
5. Content Type (choose multiple): Explanation | Quiz | Practice | Video-Friendly
6. Bloom's Level: Remembering | Understanding | Applying | Analyzing | Evaluating | Creating

Return ONLY valid JSON with NO other text:
{{
    "subject": "Mathematics",
    "topic": "{topic}",
    "grade": {grade},
    "difficulty": "Medium",
    "content_type": ["Explanation", "Quiz"],
    "blooms_level": "Understanding"
}}"""

    def _parse_and_validate(
        self,
        content: str,
        grade: int,
        topic: str
    ) -> Tuple[Optional[Tags], Optional[str]]:
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
            return None, f"Invalid tags JSON: {str(e)}"

        try:
            difficulty_raw = data.get("difficulty", "Medium")
            try:
                difficulty = Difficulty(difficulty_raw)
            except ValueError:
                difficulty = Difficulty.MEDIUM

            blooms_raw = data.get("blooms_level", "Understanding")
            try:
                blooms = BloomsLevel(blooms_raw)
            except ValueError:
                blooms = BloomsLevel.UNDERSTANDING

            tags = Tags(
                subject=data.get("subject", "Other"),
                topic=data.get("topic", topic),
                grade=data.get("grade", grade),
                difficulty=difficulty,
                content_type=data.get("content_type", ["Explanation"]),
                blooms_level=blooms,
            )
            return tags, None
        except ValidationError as e:
            error_details = "; ".join([f"{err['loc']}: {err['msg']}" for err in e.errors()])
            return None, f"Tags validation failed: {error_details}"
