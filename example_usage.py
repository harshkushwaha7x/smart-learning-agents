"""Example usage of the Governed AI Content Pipeline."""

import os
from dotenv import load_dotenv
from agents.orchestrator import Orchestrator

load_dotenv()


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
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

        artifact = orchestrator.execute(grade=grade, topic=topic)

        filename = f"example_result_{i}.json"
        with open(filename, "w") as f:
            f.write(artifact.model_dump_json(indent=2))

        print(f"Status: {artifact.final.status.value}")
        print(f"Attempts: {len(artifact.attempts)}")
        print(f"Saved to {filename}")

    print("\nAll examples complete.")


if __name__ == "__main__":
    main()
