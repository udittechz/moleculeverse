"""Assessment: practice mode (unlimited retries, not recorded) and scored mode (one attempt, session history)."""
import secrets
import time

import pandas as pd
import streamlit as st

from modules import assessment, ui

ui.init_state()
ss = st.session_state
ui.page_header("Assessment", "Test your understanding of SMILES, structures, descriptors and cheminformatics.")

PRACTICE, SCORED = "Practice mode", "Scored assessment"


def _start() -> None:
    cats = ss.get("mv_w_acats") or assessment.categories_available()
    quiz = assessment.build_quiz(cats, int(ss["mv_w_acount"]), secrets.randbelow(10**9))
    if not quiz:
        return
    ss["mv_assess"] = {"mode": ss["mv_w_amode"], "questions": quiz, "index": 0, "answers": {}, "tries": {},
                       "run": secrets.token_hex(4), "finished": False, "recorded": False}


def _submit(qid: str, widget_key: str) -> None:
    run = ss["mv_assess"]
    choice = ss.get(widget_key)
    if choice is None:
        ss["mv_assess_warn"] = "Choose an answer before submitting."
        return
    run["answers"][qid] = choice
    ss["mv_questions_answered"] += 1


def _retry_question(qid: str) -> None:
    run = ss["mv_assess"]
    run["answers"].pop(qid, None)
    run["tries"][qid] = run["tries"].get(qid, 0) + 1


def _go(delta: int) -> None:
    ss["mv_assess"]["index"] += delta


def _finish() -> None:
    ss["mv_assess"]["finished"] = True


def _exit_to_setup() -> None:
    ss["mv_assess"] = None


run = ss["mv_assess"]

# ------------------------------------------------------------------ setup screen
if run is None:
    with st.container(border=True):
        st.subheader("Set up an assessment")
        mode = st.radio("Mode", [PRACTICE, SCORED], key="mv_w_amode", horizontal=True)
        if mode == PRACTICE:
            st.info("Practice mode: instant feedback, unlimited retries of each question, and nothing is recorded.")
        else:
            st.info("Scored assessment: each question gets one attempt. The final score is added to this session's history (not saved permanently).")
        st.multiselect("Categories", assessment.categories_available(), key="mv_w_acats", placeholder="All categories")
        avail = len([q for q in assessment.QUESTION_BANK if not ss.get("mv_w_acats") or q["category"] in ss["mv_w_acats"]])
        if avail:
            top = min(20, avail)
            if top > 1:
                st.slider("Number of questions", 1, top, min(10, top), key=f"mv_w_acount_{top}")
            ss["mv_w_acount"] = ss.get(f"mv_w_acount_{top}", 1)
            st.button("Start", type="primary", on_click=_start, key="mv_a_start")
        else:
            st.warning("No questions match the chosen categories.")
    hist = ss["mv_assess_history"]
    st.subheader("Scored attempts in this session")
    if hist:
        st.dataframe(pd.DataFrame(hist).rename(columns=str.title), hide_index=True, use_container_width=True)
        st.caption("Stored in this browser session only; it is lost when the session ends.")
    else:
        st.markdown("<div class='mv-empty'>No scored attempts yet.</div>", unsafe_allow_html=True)
    st.stop()

questions = run["questions"]
mode = run["mode"]

# ------------------------------------------------------------------ results screen
if run["finished"]:
    result = assessment.score_quiz(questions, run["answers"])
    st.subheader(f"{'Practice' if mode == PRACTICE else 'Scored'} results")
    if mode == SCORED and not run["recorded"]:
        ss["mv_assess_history"].append({"time": time.strftime("%H:%M:%S"), "mode": "Scored", "score": result["score"],
                                        "total": result["total"], "percent": result["percent"]})
        ui.log_activity("Assessment", f"Scored assessment: {result['score']}/{result['total']} ({result['percent']}%)")
        run["recorded"] = True
    m1, m2 = st.columns(2)
    m1.metric("Score", f"{result['score']} / {result['total']}")
    m2.metric("Percentage", f"{result['percent']}%")
    st.caption("Practice results are not recorded." if mode == PRACTICE else "Added to this session's history only; nothing is saved permanently.")
    cat_rows = [{"Category": k, "Correct": v["correct"], "Total": v["total"]} for k, v in result["by_category"].items()]
    st.dataframe(pd.DataFrame(cat_rows), hide_index=True, use_container_width=True)
    st.markdown("#### Review of incorrect answers")
    if not result["incorrect"]:
        st.success("Every answer was correct.")
    for item in result["incorrect"]:
        with st.container(border=True):
            st.markdown(f"**{item['question']}**  \n<span class='mv-muted'>{item['category']}</span>", unsafe_allow_html=True)
            st.write(f"Your answer: {item['your_answer']}")
            st.write(f"Correct answer: **{item['correct_answer']}**")
            st.write(item["explanation"])
    a, b = st.columns(2)
    a.button("Retry with new questions", type="primary", on_click=_start, key="mv_a_retry")
    b.button("Back to setup", on_click=_exit_to_setup, key="mv_a_back")
    st.stop()

# ------------------------------------------------------------------ question screen
idx = run["index"]
q = questions[idx]
st.progress((idx) / len(questions), text=f"{mode} · question {idx + 1} of {len(questions)}")
with st.container(border=True):
    st.markdown(f"<span class='mv-badge'>{q['category']}</span>", unsafe_allow_html=True)
    st.markdown(f"### {q['question']}")
    answered = q["id"] in run["answers"]
    tries = run["tries"].get(q["id"], 0)
    if answered:
        chosen = run["answers"][q["id"]]
        st.radio("Your answer", list(range(len(q["options"]))), index=chosen, format_func=lambda i: q["options"][i],
                 key=f"mv_ql_{run['run']}_{q['id']}_{tries}", disabled=True)
        if chosen == q["answer"]:
            st.success("Correct.")
        else:
            st.error(f"Not quite. The correct answer is: {q['options'][q['answer']]}")
        st.write(q["explanation"])
        if mode == PRACTICE and chosen != q["answer"]:
            st.button("Try this question again", on_click=_retry_question, args=(q["id"],), key=f"mv_a_try_{q['id']}_{tries}")
    else:
        wkey = f"mv_qa_{run['run']}_{q['id']}_{tries}"
        st.radio("Choose one answer", list(range(len(q["options"]))), index=None, format_func=lambda i: q["options"][i], key=wkey)
        st.button("Submit answer", type="primary", on_click=_submit, args=(q["id"], wkey), key=f"mv_a_sub_{q['id']}_{tries}")
        if ss.get("mv_assess_warn"):
            st.warning(ss.pop("mv_assess_warn"))

n1, n2, n3 = st.columns([1, 1, 1])
if idx > 0 and mode == PRACTICE:
    n1.button("Previous", on_click=_go, args=(-1,), key="mv_a_prev")
if idx < len(questions) - 1:
    n2.button("Next question", on_click=_go, args=(1,), key="mv_a_next", disabled=(mode == SCORED and not answered))
else:
    n2.button("Finish and see results", type="primary", on_click=_finish, key="mv_a_fin", disabled=not answered)
n3.button("Quit to setup", on_click=_exit_to_setup, key="mv_a_quit")
if mode == SCORED:
    st.caption("Scored mode: answers are final once submitted.")
