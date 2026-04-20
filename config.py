"""Central configuration for the Governed AI Content Pipeline."""

OPENAI_MODEL = "gpt-4o-mini"
GENERATION_TEMPERATURE = 0.7
REVIEW_TEMPERATURE = 0.3

MAX_REFINEMENT_ATTEMPTS = 2

MIN_AVERAGE_SCORE = 4.0
MIN_INDIVIDUAL_SCORE = 3

GRADE_LEVEL_SETTINGS = {
    1:  {"vocabulary": "very simple", "sentence_length": "short",       "concepts": "basic"},
    2:  {"vocabulary": "simple",      "sentence_length": "short",       "concepts": "basic"},
    3:  {"vocabulary": "simple",      "sentence_length": "medium",      "concepts": "foundational"},
    4:  {"vocabulary": "simple",      "sentence_length": "medium",      "concepts": "foundational"},
    5:  {"vocabulary": "moderate",    "sentence_length": "medium",      "concepts": "intermediate"},
    6:  {"vocabulary": "moderate",    "sentence_length": "medium-long",  "concepts": "intermediate"},
    7:  {"vocabulary": "moderate",    "sentence_length": "long",        "concepts": "intermediate"},
    8:  {"vocabulary": "advanced",    "sentence_length": "long",        "concepts": "advanced"},
    9:  {"vocabulary": "advanced",    "sentence_length": "long",        "concepts": "advanced"},
    10: {"vocabulary": "advanced",    "sentence_length": "long",        "concepts": "complex"},
    11: {"vocabulary": "academic",    "sentence_length": "long",        "concepts": "complex"},
    12: {"vocabulary": "academic",    "sentence_length": "long",        "concepts": "complex"},
}
