"""Streamlit UI for the Governed AI Content Pipeline."""

import os
import sys
import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import Orchestrator


def initialize_session_state():
    if "orchestrator" not in st.session_state:
        api_key = os.getenv("OPENAI_API_KEY")
        st.session_state.orchestrator = Orchestrator(api_key=api_key)
    if "artifact" not in st.session_state:
        st.session_state.artifact = None
    if "running" not in st.session_state:
        st.session_state.running = False


def display_content(content):
    st.markdown(f"**Explanation (Grade {content.explanation.grade}):**")
    st.markdown(content.explanation.text)

    st.markdown("**Multiple Choice Questions:**")
    for i, mcq in enumerate(content.mcqs, 1):
        with st.expander(f"Question {i}", expanded=True):
            st.markdown(f"**{mcq.question}**")
            for j, opt in enumerate(mcq.options):
                marker = " [CORRECT]" if j == mcq.correct_index else ""
                st.markdown(f"- {chr(65 + j)}. {opt}{marker}")

    st.markdown("**Teacher Notes:**")
    st.markdown(f"*Learning Objective:* {content.teacher_notes.learning_objective}")
    if content.teacher_notes.common_misconceptions:
        st.markdown("*Common Misconceptions:*")
        for m in content.teacher_notes.common_misconceptions:
            st.markdown(f"- {m}")


def display_scores(review):
    cols = st.columns(4)
    for i, (criterion, score) in enumerate(review.scores.items()):
        with cols[i]:
            label = criterion.replace("_", " ").title()
            st.metric(label, f"{score}/5")

    st.metric("Average", f"{review.average_score:.1f}/5")

    if review.pass_overall:
        st.success("PASS")
    else:
        st.error("FAIL")

    if review.feedback:
        st.markdown("**Feedback:**")
        for fb in review.feedback:
            severity_label = fb.severity.value.upper()
            st.markdown(f"[{severity_label}] `{fb.field}` — {fb.issue}")


def main():
    st.set_page_config(
        page_title="Governed AI Content Pipeline",
        layout="wide"
    )

    initialize_session_state()

    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is not set. Configure it via environment variable or .env file.")
        return

    st.title("Governed AI Content Pipeline")
    st.markdown("Structured generation → quantitative evaluation → controlled refinement → full audit trail")

    st.sidebar.header("Input Parameters")
    grade = st.sidebar.number_input("Grade Level", min_value=1, max_value=12, value=4, step=1)
    topic = st.sidebar.text_input("Topic", value="Types of angles", placeholder="e.g., Photosynthesis")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        run_button = st.button("Run Pipeline", use_container_width=True, disabled=not topic)
    with col2:
        clear_button = st.button("Clear Results", use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Pipeline Flow")
    st.sidebar.markdown(
        "1. Generate (schema-validated)\n"
        "2. Review (quantitative scoring)\n"
        "3. Refine (max 2 attempts)\n"
        "4. Tag (approved content only)"
    )

    if clear_button:
        st.session_state.artifact = None
        st.rerun()

    if run_button:
        st.session_state.running = True
        with st.spinner("Executing pipeline..."):
            try:
                artifact = st.session_state.orchestrator.execute(grade, topic)
                st.session_state.artifact = artifact
                st.session_state.running = False
            except Exception as e:
                st.error(f"Pipeline failed: {str(e)}")
                st.session_state.running = False
                return

    if not st.session_state.artifact:
        st.markdown("---")
        st.markdown("""
### How It Works

1. **Input** — Select a grade level and topic
2. **Generate** — Generator produces schema-validated educational content
3. **Review** — Reviewer scores on 4 criteria (age appropriateness, correctness, clarity, coverage)
4. **Refine** — If review fails, content is refined based on structured feedback (max 2 refinements)
5. **Tag** — Approved content receives metadata classification
6. **Audit** — Complete RunArtifact captures every step with timestamps
        """)
        return

    artifact = st.session_state.artifact

    st.markdown("---")
    st.subheader("Pipeline Result")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Run ID", artifact.run_id)
    with col2:
        st.metric("Grade", artifact.input.grade)
    with col3:
        st.metric("Topic", artifact.input.topic)
    with col4:
        status = artifact.final.status.value.upper()
        st.metric("Final Status", status)

    started = artifact.timestamps.get("started_at")
    finished = artifact.timestamps.get("finished_at")
    if started and finished:
        duration = (finished - started).total_seconds()
        st.caption(f"Duration: {duration:.1f}s | Attempts: {len(artifact.attempts)}")

    st.markdown("---")

    tab_names = [f"Attempt {a.attempt_number}" for a in artifact.attempts]
    tab_names.append("Final Result")
    tabs = st.tabs(tab_names)

    for i, attempt in enumerate(artifact.attempts):
        with tabs[i]:
            st.subheader(f"Attempt {attempt.attempt_number}")
            st.markdown(f"**Status:** {attempt.status.value.upper()}")

            if attempt.refinement_feedback:
                with st.expander("Refinement Feedback Used", expanded=False):
                    st.code(attempt.refinement_feedback)

            content = attempt.refined or attempt.draft
            if content:
                display_content(content)

            if attempt.review:
                st.markdown("---")
                st.subheader("Review Scores")
                display_scores(attempt.review)

    with tabs[-1]:
        st.subheader("Final Result")
        if artifact.final.status.value == "approved" and artifact.final.content:
            st.success("Content Approved")
            display_content(artifact.final.content)

            if artifact.final.tags:
                st.markdown("---")
                st.subheader("Content Tags")
                tag_data = artifact.final.tags.model_dump()
                cols = st.columns(3)
                for idx, (key, val) in enumerate(tag_data.items()):
                    with cols[idx % 3]:
                        st.markdown(f"**{key.replace('_', ' ').title()}:** {val}")
        else:
            st.error("Content Rejected After Maximum Attempts")

    st.markdown("---")
    st.subheader("Export RunArtifact")

    export_json = artifact.model_dump_json(indent=2)
    st.download_button(
        label="Download RunArtifact (JSON)",
        data=export_json,
        file_name=f"{artifact.run_id}.json",
        mime="application/json"
    )


if __name__ == "__main__":
    main()
