"""Question bank, quiz building and scoring (pure Python).

Questions with a ``verify`` entry have an RDKit-checkable fact behind the answer;
tests/test_assessment.py re-computes those facts with RDKit when RDKit is installed.
"""
from __future__ import annotations

import random
from typing import Any, Optional

CATEGORIES = [
    "SMILES notation", "Molecular structures", "Functional groups", "Formulae and molecular mass",
    "Molecular descriptors", "2D and 3D representations", "Structure-property relationships", "Cheminformatics concepts",
]


def _q(qid, cat, text, options, answer, why, verify=None):
    return {"id": qid, "category": cat, "question": text, "options": options, "answer": answer,
            "explanation": why, "verify": verify}


QUESTION_BANK: list[dict[str, Any]] = [
    _q("smi1", CATEGORIES[0], "Which SMILES string represents ethanol?", ["CCO", "C=O", "COC", "CC=O"], 0,
       "CCO is two carbons in a chain with an OH on the second one. C=O is formaldehyde, COC is dimethyl ether and CC=O is acetaldehyde."),
    _q("smi2", CATEGORIES[0], "In SMILES, what does a lowercase atom symbol such as c or n indicate?",
       ["The atom is aromatic", "The atom is negatively charged", "The atom is an isotope", "The atom has a double bond"], 0,
       "Lowercase letters mark aromatic atoms, so c1ccccc1 is a benzene ring."),
    _q("smi3", CATEGORIES[0], "Which symbol denotes a double bond in SMILES?", ["=", "#", "-", "/"], 0,
       "= is a double bond, # a triple bond, - an explicit single bond, and / a directional bond used for E/Z geometry."),
    _q("smi4", CATEGORIES[0], "What do parentheses mean in a SMILES such as CC(=O)O?",
       ["A branch attached to the preceding atom", "A ring closure", "A charged atom", "A stereocenter"], 0,
       "Parentheses enclose a branch. In CC(=O)O the =O branch hangs off the second carbon."),
    _q("smi5", CATEGORIES[0], "Which molecule does the SMILES c1ccccc1 describe?", ["Benzene", "Cyclohexane", "Toluene", "Phenol"], 0,
       "Six aromatic carbons closed into a ring give benzene. Cyclohexane would be C1CCCCC1.",
       {"smiles": "c1ccccc1", "key": "formula", "expected": "C6H6"}),
    _q("smi6", CATEGORIES[0], "Why are atoms such as [NH4+] written inside square brackets in SMILES?",
       ["To state an explicit hydrogen count and formal charge", "To mark a ring", "To mark an aromatic atom", "To start a branch"], 0,
       "Square brackets are needed whenever the hydrogen count, charge, isotope or stereo-tag must be given explicitly."),
    _q("str1", CATEGORIES[1], "What are constitutional isomers?",
       ["Molecules with the same formula but different atom connectivity", "Molecules with different formulas and the same connectivity",
        "Mirror-image molecules", "Molecules that differ only in isotopes"], 0,
       "Constitutional isomers share a molecular formula but connect their atoms differently."),
    _q("str2", CATEGORIES[1], "Which pair are constitutional isomers?",
       ["Ethanol (CCO) and dimethyl ether (COC)", "Ethanol and ethane", "Water and hydrogen peroxide", "Methane and ethane"], 0,
       "Both ethanol and dimethyl ether are C2H6O but have different connectivity.",
       {"smiles": "COC", "key": "formula", "expected": "C2H6O"}),
    _q("str3", CATEGORIES[1], "What is the hybridisation of the carbon atoms in benzene?", ["sp2", "sp3", "sp", "dsp3"], 0,
       "Each benzene carbon has three sigma bonds in a plane and one p orbital in the delocalised pi system, so it is sp2."),
    _q("str4", CATEGORIES[1], "A tetrahedral carbon is a stereocenter when it carries:",
       ["Four different substituents", "Two hydrogen atoms", "A double bond", "Three identical substituents"], 0,
       "Four different groups make the carbon chiral, giving two non-superimposable arrangements (R and S)."),
    _q("fg1", CATEGORIES[2], "Which functional group is present in CC(=O)O?", ["Carboxylic acid", "Ester", "Aldehyde", "Ether"], 0,
       "A C(=O)OH unit is a carboxylic acid. This SMILES is acetic acid."),
    _q("fg2", CATEGORIES[2], "Which functional group is present in CC(C)=O (acetone)?", ["Ketone", "Aldehyde", "Alcohol", "Amide"], 0,
       "A carbonyl carbon bonded to two other carbons is a ketone."),
    _q("fg3", CATEGORIES[2], "Which functional group is present in COC?", ["Ether", "Ester", "Alcohol", "Ketone"], 0,
       "An oxygen bonded to two carbon atoms is an ether."),
    _q("fg4", CATEGORIES[2], "Which functional group is present in CC(=O)N (acetamide)?", ["Amide", "Amine only", "Nitrile", "Ester"], 0,
       "A carbonyl carbon bonded to nitrogen is an amide."),
    _q("mass1", CATEGORIES[3], "What is the molecular formula of glucose?", ["C6H12O6", "C12H22O11", "C6H6O6", "C5H10O5"], 0,
       "Glucose is a hexose with six carbons, twelve hydrogens and six oxygens. C12H22O11 is sucrose.",
       {"smiles": "C([C@@H]1[C@H]([C@@H]([C@H]([C@@H](O1)O)O)O)O)O", "key": "formula", "expected": "C6H12O6"}),
    _q("mass2", CATEGORIES[3], "What is the approximate molecular weight of water?", ["18.02 g/mol", "16.00 g/mol", "17.01 g/mol", "20.03 g/mol"], 0,
       "2 x 1.008 + 15.999 is about 18.02 g/mol.", {"smiles": "O", "key": "mol_weight", "expected": 18.015, "tol": 0.01}),
    _q("mass3", CATEGORIES[3], "What is the approximate molecular weight of carbon dioxide?", ["44.01 g/mol", "28.01 g/mol", "32.00 g/mol", "46.01 g/mol"], 0,
       "12.011 + 2 x 15.999 is about 44.01 g/mol.", {"smiles": "O=C=O", "key": "mol_weight", "expected": 44.009, "tol": 0.01}),
    _q("mass4", CATEGORIES[3], "How does exact (monoisotopic) mass differ from average molecular weight?",
       ["Exact mass uses the most abundant isotope of each element; average weight uses natural isotope abundances",
        "Exact mass ignores hydrogen atoms", "They are always identical", "Exact mass is measured; average weight is calculated"], 0,
       "Mass spectrometry resolves individual isotopic masses, while average molecular weight is used for bulk quantities."),
    _q("mass5", CATEGORIES[3], "What is the molecular formula of caffeine?", ["C8H10N4O2", "C9H8O4", "C7H8N4O2", "C8H9NO2"], 0,
       "Caffeine is C8H10N4O2. C9H8O4 is aspirin, C7H8N4O2 is theophylline and C8H9NO2 is paracetamol.",
       {"smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O", "key": "formula", "expected": "C8H10N4O2"}),
    _q("desc1", CATEGORIES[4], "What does topological polar surface area (TPSA) estimate?",
       ["Surface contributed by polar atoms, mainly N and O with their hydrogens", "The total surface area of the molecule",
        "The number of polar bonds", "The boiling point"], 0,
       "TPSA sums fragment contributions of polar atoms; it is a quick polarity indicator."),
    _q("desc2", CATEGORIES[4], "What does a calculated logP estimate?",
       ["Preference for a lipid-like (octanol) phase over water", "The acidity of the molecule", "The molecular size", "The melting point"], 0,
       "logP is the logarithm of an octanol/water partition ratio; higher values suggest greater lipophilicity."),
    _q("desc3", CATEGORIES[4], "How many hydrogen-bond donors does ethanol have by RDKit's rule?", ["1", "0", "2", "3"], 0,
       "Ethanol has one O-H group that can donate a hydrogen bond.", {"smiles": "CCO", "key": "hbd", "expected": 1}),
    _q("desc4", CATEGORIES[4], "How many rotatable bonds does butane (CCCC) have under the standard definition?", ["1", "0", "2", "3"], 0,
       "Only the central C-C bond lies between two non-terminal heavy atoms, so there is one rotatable bond.",
       {"smiles": "CCCC", "key": "rotatable_bonds", "expected": 1}),
    _q("desc5", CATEGORIES[4], "What is the fraction of sp3 carbons (Fsp3) of benzene?", ["0", "0.5", "1", "6"], 0,
       "All six benzene carbons are sp2, so Fsp3 = 0.", {"smiles": "c1ccccc1", "key": "fsp3", "expected": 0.0, "tol": 0.001}),
    _q("desc6", CATEGORIES[4], "How many rings does naphthalene contain?", ["2", "1", "3", "10"], 0,
       "Naphthalene is two fused six-membered rings.", {"smiles": "c1ccc2ccccc2c1", "key": "ring_count", "expected": 2}),
    _q("rep1", CATEGORIES[5], "What does a 2D structure diagram mainly convey?",
       ["Which atoms are bonded and by what bond types", "The exact experimental 3D geometry", "The electron density", "The melting point"], 0,
       "A 2D diagram draws the molecular graph (connectivity) on a plane; it is not a true 3D geometry."),
    _q("rep2", CATEGORIES[5], "Why are hydrogens added explicitly before generating a 3D conformer?",
       ["Hydrogen positions strongly affect realistic geometry and energy", "Hydrogens make the molecule heavier",
        "RDKit cannot read implicit hydrogens", "It removes aromaticity"], 0,
       "Force fields and embedding need hydrogen coordinates to produce reasonable bond angles and sterics."),
    _q("rep3", CATEGORIES[5], "A single computed 3D conformer is best described as:",
       ["One plausible model geometry, not necessarily the experimental structure", "The experimentally determined structure",
        "The global minimum for every molecule", "A guaranteed bioactive shape"], 0,
       "Flexible molecules populate many conformers; a generated one is a model, not a measurement."),
    _q("rep4", CATEGORIES[5], "Which 3D display style draws atoms as large spheres at van der Waals-like radii?",
       ["Space-filling", "Wireframe", "Stick", "Ball-and-stick"], 0,
       "Space-filling (CPK) shows the volume atoms occupy; stick and wireframe emphasise bonds."),
    _q("sp1", CATEGORIES[6], "Which has the higher boiling point: ethanol or dimethyl ether (both C2H6O)?",
       ["Ethanol, because it forms hydrogen bonds", "Dimethyl ether, because it is heavier", "They are identical", "Dimethyl ether, because it has an O-H"], 0,
       "Ethanol (about 78 C) has an O-H group that hydrogen-bonds to neighbours; dimethyl ether (about -24 C) cannot."),
    _q("sp2", CATEGORIES[6], "How does boiling point generally change as the chain of straight alkanes lengthens?",
       ["It increases", "It decreases", "It stays constant", "It alternates randomly"], 0,
       "Longer chains have stronger London dispersion forces, so more energy is needed to separate molecules."),
    _q("sp3", CATEGORIES[6], "Which is expected to dissolve better in water: ethanol or hexane?",
       ["Ethanol, because of its polar O-H group", "Hexane, because it is larger", "Both equally", "Neither dissolves at all"], 0,
       "Ethanol can hydrogen-bond with water; hexane is nonpolar."),
    _q("sp4", CATEGORIES[6], "A molecule with a high TPSA and many hydrogen-bond donors tends to be:",
       ["More polar and more hydrophilic", "Nonpolar and very lipophilic", "Always insoluble in water", "Always toxic"], 0,
       "Polar surface and donors usually raise polarity and water interaction; this is a tendency, not a rule for every case."),
    _q("chem1", CATEGORIES[7], "What is the purpose of a canonical SMILES?",
       ["To give one consistent string for the same structure (within a toolkit and version)", "To store the 3D coordinates", "To encrypt the molecule",
        "To predict toxicity"], 0,
       "Canonicalisation removes ambiguity from atom ordering, which makes duplicate detection and searching reliable."),
    _q("chem2", CATEGORIES[7], "What range of values can the Tanimoto similarity of two fingerprints take?",
       ["0 to 1", "-1 to 1", "0 to 100 only", "1 to 10"], 0,
       "It is the shared on-bits divided by the total distinct on-bits: 0 means no shared bits and 1 means identical fingerprints."),
    _q("chem3", CATEGORIES[7], "What is a molecular fingerprint?",
       ["A fixed-length bit vector encoding structural features", "A photograph of the crystal", "A 3D coordinate file", "A list of experimental properties"], 0,
       "Fingerprints such as Morgan/ECFP encode substructure environments, enabling fast similarity searching."),
    _q("chem4", CATEGORIES[7], "Do calculated descriptors alone prove that a molecule will be an effective or safe drug?",
       ["No; they are computed properties and do not prove biological activity or safety", "Yes, if logP is below 5", "Yes, if the SMILES is valid",
        "Yes, if TPSA is high"], 0,
       "Descriptors guide hypotheses, but activity, toxicity and safety require experimental evidence."),
]


def categories_available() -> list[str]:
    return [c for c in CATEGORIES if any(q["category"] == c for q in QUESTION_BANK)]


def build_quiz(categories: Optional[list[str]] = None, n: int = 10, seed: Optional[int] = None) -> list[dict[str, Any]]:
    """Random question order and shuffled options; ``answer`` is re-indexed after shuffling."""
    rng = random.Random(seed)
    pool = [q for q in QUESTION_BANK if not categories or q["category"] in categories]
    chosen = rng.sample(pool, min(max(n, 0), len(pool)))
    quiz = []
    for q in chosen:
        order = list(range(len(q["options"])))
        rng.shuffle(order)
        quiz.append({**q, "options": [q["options"][i] for i in order], "answer": order.index(q["answer"])})
    return quiz


def is_correct(question: dict[str, Any], choice: Optional[int]) -> bool:
    return choice is not None and choice == question["answer"]


def score_quiz(questions: list[dict[str, Any]], answers: dict[str, Optional[int]]) -> dict[str, Any]:
    """Score answers (question id -> chosen option index). Unanswered counts as incorrect."""
    correct, review, by_cat = 0, [], {}
    for q in questions:
        choice = answers.get(q["id"])
        ok = is_correct(q, choice)
        stat = by_cat.setdefault(q["category"], {"correct": 0, "total": 0})
        stat["total"] += 1
        if ok:
            correct += 1
            stat["correct"] += 1
        else:
            review.append({"id": q["id"], "category": q["category"], "question": q["question"],
                           "your_answer": q["options"][choice] if choice is not None else "No answer",
                           "correct_answer": q["options"][q["answer"]], "explanation": q["explanation"]})
    total = len(questions)
    return {"score": correct, "total": total, "percent": round(100.0 * correct / total, 1) if total else 0.0,
            "incorrect": review, "by_category": by_cat}
