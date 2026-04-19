"""Generator Agent: Generates draft educational content for a given grade and topic."""

import json
from typing import Optional
from openai import OpenAI


class GeneratorAgent:
    """Generates educational content (explanation + MCQs) for a specified grade and topic."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def generate(self, grade: int, topic: str, feedback: Optional[str] = None) -> dict:
        """
        Generate educational content for a given grade and topic.

        Args:
            grade: Student grade level (1-12).
            topic: Subject topic to generate content for.
            feedback: Optional reviewer feedback to incorporate during refinement.

        Returns:
            Structured dict with 'explanation' and 'mcqs' keys.
        """
        prompt = self._build_prompt(grade, topic, feedback)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            return self._parse_response(content)
        except Exception as e:
            return {
                "error": f"Generation failed: {str(e)}",
                "explanation": "",
                "mcqs": []
            }

    def _build_prompt(self, grade: int, topic: str, feedback: Optional[str] = None) -> str:
        """Construct the LLM prompt with optional refinement feedback."""
        refinement_note = ""
        if feedback:
            refinement_note = (
                f"\n\nIMPORTANT: Address the following reviewer feedback:\n{feedback}"
            )

        return f"""You are an educational content creator. Generate educational content for Grade {grade} students on the topic: "{topic}".

Requirements:
1. Language must be appropriate for Grade {grade} (use simple vocabulary, short sentences)
2. Provide a clear explanation that is age-appropriate
3. Generate 4 multiple-choice questions testing understanding of the topic
4. Each MCQ should have 4 options (A, B, C, D) and one correct answer
5. Concepts must be factually correct
{refinement_note}

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
    "explanation": "A clear, age-appropriate explanation of the topic...",
    "mcqs": [
        {{
            "question": "Question text...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "B"
        }},
        {{
            "question": "Question text...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "A"
        }},
        {{
            "question": "Question text...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "C"
        }},
        {{
            "question": "Question text...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "D"
        }}
    ]
}}"""

    def _parse_response(self, content: str) -> dict:
        """
        Parse and validate the LLM response into structured JSON.

        Args:
            content: Raw string response from the LLM.

        Returns:
            Validated dict with 'explanation' and 'mcqs'.

        Raises:
            ValueError: If the response is malformed or fails validation.
        """
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        try:
            result = json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")

        if "explanation" not in result or "mcqs" not in result:
            raise ValueError("Missing required fields: 'explanation' or 'mcqs'")

        if not isinstance(result["mcqs"], list) or len(result["mcqs"]) != 4:
            raise ValueError("'mcqs' must be a list of exactly 4 questions")

        for i, mcq in enumerate(result["mcqs"]):
            required_keys = {"question", "options", "answer"}
            if not required_keys.issubset(mcq):
                raise ValueError(f"MCQ {i + 1} is missing required fields")
            if len(mcq["options"]) != 4:
                raise ValueError(f"MCQ {i + 1} must have exactly 4 options")
            if mcq["answer"] not in ("A", "B", "C", "D"):
                raise ValueError(f"MCQ {i + 1} answer must be A, B, C, or D")

        return result
