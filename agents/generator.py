"""
Generator Agent: Produces schema-validated educational content with retry logic.
"""

import json
from typing import Optional, Tuple
from openai import OpenAI
from pydantic import ValidationError
from schemas.models import GeneratedContent, Explanation, MCQ, TeacherNotes
from config import GRADE_LEVEL_SETTINGS, OPENAI_MODEL, GENERATION_TEMPERATURE


class GeneratorAgent:

    MAX_RETRIES = 1

    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)
        self.model = OPENAI_MODEL

    def generate(
        self,
        grade: int,
        topic: str,
        feedback: Optional[str] = None,
    ) -> Tuple[Optional[GeneratedContent], Optional[str]]:
        """
        Generate educational content with schema validation and retry.

        Returns:
            (GeneratedContent, None) on success or (None, error_message) on failure.
        """
        prompt = self._build_prompt(grade, topic, feedback)
        last_error = None

        for attempt in range(1 + self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=GENERATION_TEMPERATURE,
                )
                content_text = response.choices[0].message.content
                result, error = self._parse_and_validate(content_text, grade)
                if result:
                    return result, None
                last_error = error
            except Exception as e:
                last_error = f"API call failed: {str(e)}"

        return None, last_error

    def _build_prompt(self, grade: int, topic: str, feedback: Optional[str] = None) -> str:
        grade_settings = GRADE_LEVEL_SETTINGS.get(grade, GRADE_LEVEL_SETTINGS[5])
        vocab = grade_settings["vocabulary"]
        sentence_len = grade_settings["sentence_length"]
        concepts = grade_settings["concepts"]

        refinement_note = ""
        if feedback:
            refinement_note = (
                f"\n\nIMPORTANT: Address the following reviewer feedback:\n{feedback}"
            )

        return f"""You are an educational content creator. Generate educational content for Grade {grade} students on the topic: "{topic}".

GRADE-LEVEL GUIDELINES:
- Vocabulary level: {vocab}
- Sentence length: {sentence_len}
- Concept depth: {concepts}

REQUIREMENTS:
1. Language must be appropriate for Grade {grade}
2. Provide a clear explanation that is age-appropriate (100-250 words)
3. Generate 4 multiple-choice questions testing understanding of the topic
4. Each MCQ should have exactly 4 options and one correct answer
5. Concepts must be factually correct
6. Return ONLY valid JSON matching the exact schema below - no markdown, no code blocks
{refinement_note}

MANDATORY JSON SCHEMA (produce EXACTLY this structure):
{{
    "explanation": {{
        "text": "Clear, age-appropriate explanation of the topic in {grade}th grade language",
        "grade": {grade}
    }},
    "mcqs": [
        {{
            "question": "Question testing understanding",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_index": 0
        }},
        {{
            "question": "Question testing understanding",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_index": 1
        }},
        {{
            "question": "Question testing understanding",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_index": 2
        }},
        {{
            "question": "Question testing understanding",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_index": 3
        }}
    ],
    "teacher_notes": {{
        "learning_objective": "What students should be able to do after learning this",
        "common_misconceptions": ["Common student error 1", "Common student error 2"]
    }}
}}

IMPORTANT:
- Ensure correct_index is 0-3 (NOT letters A-D)
- Ensure exactly 4 questions, exactly 4 options each
- Explanation text must be 100-250 words
- Return ONLY the JSON, nothing else"""

    def _parse_and_validate(
        self,
        content: str,
        grade: int
    ) -> Tuple[Optional[GeneratedContent], Optional[str]]:
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
            return None, f"Invalid JSON: {str(e)}"

        try:
            generated = GeneratedContent(
                explanation=Explanation(
                    text=data.get("explanation", {}).get("text", ""),
                    grade=data.get("explanation", {}).get("grade", grade)
                ),
                mcqs=[
                    MCQ(
                        question=mcq.get("question", ""),
                        options=mcq.get("options", []),
                        correct_index=mcq.get("correct_index", 0)
                    )
                    for mcq in data.get("mcqs", [])
                ],
                teacher_notes=TeacherNotes(
                    learning_objective=data.get("teacher_notes", {}).get("learning_objective", ""),
                    common_misconceptions=data.get("teacher_notes", {}).get("common_misconceptions", [])
                )
            )
            return generated, None
        except ValidationError as e:
            error_details = "; ".join([f"{err['loc']}: {err['msg']}" for err in e.errors()])
            return None, f"Schema validation failed: {error_details}"
