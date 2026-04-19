"""
Streamlit UI for the Adaptive Learning Content System.
Triggers the agent pipeline and displays generator output, reviewer feedback,
and refined output in a tabbed interface.
"""

import os
import sys
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import Orchestrator


def initialize_session_state():
    """Set default values for session state on first load."""
    if "orchestrator" not in st.session_state:
        api_key = os.getenv("OPENAI_API_KEY")
        st.session_state.orchestrator = Orchestrator(api_key=api_key)

    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = None

    if "running" not in st.session_state:
        st.session_state.running = False


def format_mcq(mcq: dict, index: int) -> str:
    """Format a single MCQ as a markdown string."""
    question = mcq.get("question", "")
    options = mcq.get("options", [])
    answer = mcq.get("answer", "")

    lines = [f"**Question {index}:** {question}\n"]
    for i, opt in enumerate(options, 1):
        letter = chr(64 + i)
        marker = " (correct)" if letter == answer else ""
        lines.append(f"- {letter}. {opt}{marker}")

    return "\n".join(lines)


def display_content(output: dict):
    """Render generator output: explanation and MCQs."""
    if "error" in output:
        st.error(f"Error: {output['error']}")
        return

    st.markdown("**Explanation:**")
    st.markdown(output.get("explanation", ""))

    st.markdown("**Multiple Choice Questions:**")
    for i, mcq in enumerate(output.get("mcqs", []), 1):
        with st.expander(f"Question {i}", expanded=True):
            st.markdown(format_mcq(mcq, i))


def display_review(output: dict):
    """Render reviewer feedback with status indicator."""
    status = output.get("status", "unknown")
    feedback = output.get("feedback", [])

    if status == "pass":
        st.success("Status: PASS")
    else:
        st.error("Status: FAIL")

    if feedback:
        st.markdown("**Feedback:**")
        for i, item in enumerate(feedback, 1):
            st.write(f"{i}. {item}")
    else:
        st.info("No feedback items.")


def main():
    """Application entry point."""
    st.set_page_config(
        page_title="Adaptive Learning Content System",
        page_icon="A",
        layout="wide"
    )

    initialize_session_state()

    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is not set. Configure it via environment variable or .env file.")
        return

    st.title("Adaptive Learning Content System")
    st.markdown("Agent-driven pipeline for generating, evaluating, and refining educational content")

    st.sidebar.header("Input Parameters")
    grade = st.sidebar.number_input("Grade Level", min_value=1, max_value=12, value=4, step=1)
    topic = st.sidebar.text_input("Topic", value="Types of angles", placeholder="e.g., Photosynthesis")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        run_button = st.button("Run Pipeline", use_container_width=True, disabled=not topic)
    with col2:
        clear_button = st.button("Clear Results", use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### System Flow")
    st.sidebar.markdown(
        "1. Content Generation (Generator Agent)\n"
        "2. Evaluation (Reviewer Agent)\n"
        "3. Conditional Refinement (1-pass feedback loop)"
    )

    if clear_button:
        st.session_state.pipeline_result = None
        st.rerun()

    if run_button:
        st.session_state.running = True
        with st.spinner("Executing pipeline..."):
            try:
                result = st.session_state.orchestrator.run_pipeline(grade, topic)
                st.session_state.pipeline_result = result
                st.session_state.running = False
            except Exception as e:
                st.error(f"Pipeline failed: {str(e)}")
                st.session_state.running = False
                return

    if not st.session_state.pipeline_result:
        st.markdown("---")
        st.markdown("""
### How It Works

1. **Input** — Select a grade level and topic
2. **Generate** — Generator Agent produces structured educational content (explanation + MCQs)
3. **Review** — Reviewer Agent evaluates age appropriateness, conceptual correctness, and clarity
4. **Refine** — If review fails, Generator Agent re-generates with embedded feedback (1 pass max)
5. **Output** — View and export the final structured content
        """)
        return

    result = st.session_state.pipeline_result

    st.markdown("---")
    st.subheader("Pipeline Status")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Grade", result["grade"])
    with col2:
        st.metric("Topic", result["topic"])
    with col3:
        status = result.get("final_status", "unknown")
        status_label = "PASS" if status == "pass" else "FAIL"
        st.metric("Final Status", status_label)

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs([
        "Generated Content",
        "Reviewer Feedback",
        "Refinement"
    ])

    with tab1:
        st.subheader("Generated Content")
        if result["generator_output"]:
            display_content(result["generator_output"])
        else:
            st.warning("No generator output available.")

    with tab2:
        st.subheader("Reviewer Feedback")
        initial_review = result.get("initial_reviewer_output")
        if initial_review:
            display_review(initial_review)
        else:
            st.warning("No reviewer output available.")

    with tab3:
        refined = result.get("refined_output")
        if refined:
            st.subheader("Refined Content")
            st.info("Content was refined based on reviewer feedback.")
            display_content(refined)

            refined_review = result.get("refined_reviewer_output")
            if refined_review:
                st.markdown("---")
                st.subheader("Post-Refinement Review")
                display_review(refined_review)
        else:
            st.info("No refinement needed. The initial content passed review.")

    st.markdown("---")
    st.subheader("Export Results")

    export_json = json.dumps(result, indent=2)
    st.download_button(
        label="Download Results as JSON",
        data=export_json,
        file_name=f"content_grade{result['grade']}_{result['topic'].replace(' ', '_')}.json",
        mime="application/json"
    )


if __name__ == "__main__":
    main()
