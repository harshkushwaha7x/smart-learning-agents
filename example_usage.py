"""Example usage of the Adaptive Learning Content System without the Streamlit UI.
Runs the pipeline for two sample inputs and saves results as JSON.
"""

import os
import json
from dotenv import load_dotenv
from agents.orchestrator import Orchestrator

load_dotenv()


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Set it via environment variable or .env file before running.")
        return

    orchestrator = Orchestrator(api_key=api_key)

    examples = [
        {"grade": 4, "topic": "Types of angles"},
        {"grade": 6, "topic": "Water cycle"},
    ]

    for i, example in enumerate(examples, 1):
        grade, topic = example["grade"], example["topic"]
        print(f"\nExample {i}: Grade {grade} - {topic}")
        print("-" * 50)

        result = orchestrator.run_pipeline(grade=grade, topic=topic)

        filename = f"example_result_{i}.json"
        with open(filename, "w") as f:
            json.dump(result, f, indent=2)

        print(f"Status: {result['final_status']}")
        print(f"Saved to {filename}")

    print("\nAll examples complete.")


if __name__ == "__main__":
    main()
