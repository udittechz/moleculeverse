import importlib.util

from modules import assessment as a


def test_bank_integrity():
    ids = [q["id"] for q in a.QUESTION_BANK]
    assert len(ids) == len(set(ids))
    for q in a.QUESTION_BANK:
        assert len(q["options"]) >= 2 and len(set(q["options"])) == len(q["options"])
        assert 0 <= q["answer"] < len(q["options"])
        assert q["explanation"].strip()
        assert q["category"] in a.CATEGORIES
    assert set(a.categories_available()) == set(a.CATEGORIES)


def test_build_quiz_shuffles_but_keeps_correct_answer():
    by_id = {q["id"]: q for q in a.QUESTION_BANK}
    quiz = a.build_quiz(n=15, seed=3)
    assert len(quiz) == 15
    for q in quiz:
        orig = by_id[q["id"]]
        assert q["options"][q["answer"]] == orig["options"][orig["answer"]]
    assert [q["id"] for q in a.build_quiz(n=15, seed=3)] == [q["id"] for q in quiz]
    assert [q["id"] for q in a.build_quiz(n=15, seed=4)] != [q["id"] for q in quiz]


def test_category_filter_and_size_cap():
    quiz = a.build_quiz(["SMILES notation"], n=100, seed=1)
    assert quiz and all(q["category"] == "SMILES notation" for q in quiz)
    assert len(quiz) == sum(1 for q in a.QUESTION_BANK if q["category"] == "SMILES notation")


def test_scoring_and_review():
    quiz = a.build_quiz(n=4, seed=9)
    answers = {quiz[0]["id"]: quiz[0]["answer"], quiz[1]["id"]: (quiz[1]["answer"] + 1) % len(quiz[1]["options"])}
    res = a.score_quiz(quiz, answers)
    assert res["score"] == 1 and res["total"] == 4 and res["percent"] == 25.0
    assert len(res["incorrect"]) == 3
    assert any(r["your_answer"] == "No answer" for r in res["incorrect"])
    assert all(r["explanation"] for r in res["incorrect"])


def test_perfect_and_empty_scores():
    quiz = a.build_quiz(n=5, seed=2)
    perfect = a.score_quiz(quiz, {q["id"]: q["answer"] for q in quiz})
    assert perfect["percent"] == 100.0 and not perfect["incorrect"]
    assert a.score_quiz([], {})["percent"] == 0.0


def test_rdkit_verifiable_answers():
    """Re-compute every 'verify' fact with RDKit (skipped when RDKit is missing)."""
    if importlib.util.find_spec("rdkit") is None:
        import pytest

        pytest.skip("RDKit not installed")
    from modules import chemistry

    checked = 0
    for q in a.QUESTION_BANK:
        v = q.get("verify")
        if not v:
            continue
        rec = chemistry.analyze_smiles(v["smiles"])
        assert rec["valid"], q["id"]
        got = rec["values"][v["key"]]
        if isinstance(v["expected"], str):
            assert got == v["expected"], q["id"]
        else:
            assert abs(got - v["expected"]) <= v.get("tol", 1e-9), (q["id"], got)
        checked += 1
    assert checked >= 8
