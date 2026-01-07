"""
Skill Attempt Test Cases
------------------------
Test cases that should be ASSESSED by triage (actual skill practice attempts).

These responses are genuine attempts at practicing communication skills.
The triage service should classify these as "skill_practice" and trigger assessment.

Usage:
    pytest backend/tests/scripts/skill_attempt.py -v
    python backend/tests/scripts/skill_attempt.py  # standalone
"""

from dataclasses import dataclass


@dataclass
class AssessmentTestCase:
    """A test case for triage + assessment."""

    name: str
    context: list[dict]  # Previous conversation turns
    user_response: str
    expected_decision: str  # Should always be "assess" for this file
    expected_score_range: tuple[int, int]  # (min, max) expected score
    target_skills: list[str]  # Which skills this tests (for filtering)
    notes: str | None = None


SKILL_ATTEMPT_EXAMPLES: list[AssessmentTestCase] = [
    # ─────────────────────────────────────────────────────────────────────────
    # HIGH QUALITY ATTEMPTS (Expected: 7-10)
    # ─────────────────────────────────────────────────────────────────────────
    AssessmentTestCase(
        name="excellent_pitch_structured",
        context=[
            {"role": "assistant", "content": "Pitch me this water bottle as if I'm a busy CEO."}
        ],
        user_response="This bottle saves you time and money. It keeps drinks cold for 24 hours, so you never waste time refilling. Plus, it's sustainable—one purchase replaces hundreds of plastic bottles. In three months, it pays for itself.",
        expected_decision="assess",
        expected_score_range=(8, 10),
        target_skills=["clarity", "persuasiveness", "conciseness"],
        notes="Clear structure, concrete benefits, strong close",
    ),
    AssessmentTestCase(
        name="excellent_explanation_analogy",
        context=[
            {"role": "assistant", "content": "Explain machine learning to a non-technical person."}
        ],
        user_response="Machine learning is like teaching a computer to recognize patterns. Instead of programming every rule, you show it examples and it learns. For instance, show it thousands of cat photos, and it learns what cats look like. The more examples, the better it gets.",
        expected_decision="assess",
        expected_score_range=(8, 10),
        target_skills=["clarity", "discourse_coherence"],
        notes="Great analogy, builds progressively, clear examples",
    ),
    AssessmentTestCase(
        name="excellent_argument_evidence",
        context=[{"role": "assistant", "content": "Argue why remote work should be permanent."}],
        user_response="Remote work benefits everyone. Employees save commute time—that's 10 hours a week on average. Companies save on office costs, often millions annually. And Stanford research shows productivity increases by 13%. The data is clear: remote work works.",
        expected_decision="assess",
        expected_score_range=(8, 10),
        target_skills=["persuasiveness", "rhetorical_effectiveness"],
        notes="Multiple evidence points, specific data, strong conclusion",
    ),
    AssessmentTestCase(
        name="excellent_concise_summary",
        context=[{"role": "assistant", "content": "Summarize the key decision in one sentence."}],
        user_response="We're launching in Q2 because market research shows peak demand and our development will be complete by then.",
        expected_decision="assess",
        expected_score_range=(9, 10),
        target_skills=["conciseness", "clarity"],
        notes="Maximally concise, includes reasoning",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # GOOD QUALITY ATTEMPTS (Expected: 5-7)
    # ─────────────────────────────────────────────────────────────────────────
    AssessmentTestCase(
        name="good_pitch_some_structure",
        context=[{"role": "assistant", "content": "Pitch me on your project idea."}],
        user_response="Our project helps small businesses manage inventory. It's cloud-based, so no installation needed. It tracks stock levels and sends alerts when things are running low. We've had really positive feedback from our beta users, and we think it could help a lot of businesses.",
        expected_decision="assess",
        expected_score_range=(5, 7),
        target_skills=["clarity", "persuasiveness"],
        notes="Decent structure, could be more concise, weak close",
    ),
    AssessmentTestCase(
        name="good_explanation_adequate",
        context=[
            {"role": "assistant", "content": "Explain blockchain to someone unfamiliar with it."}
        ],
        user_response="Blockchain is basically a digital ledger that's shared across many computers. When someone makes a transaction, it gets recorded and everyone can see it. It's really secure because to change anything, you'd need to change it on all the computers at once, which is basically impossible.",
        expected_decision="assess",
        expected_score_range=(5, 7),
        target_skills=["clarity", "discourse_coherence"],
        notes="Clear but could use better structure and examples",
    ),
    AssessmentTestCase(
        name="good_storytelling_adequate",
        context=[
            {
                "role": "assistant",
                "content": "Tell me about a challenge you overcame professionally.",
            }
        ],
        user_response="Last year, our main client threatened to leave. I scheduled a call, listened to their concerns, and proposed a custom solution within 48 hours. They not only stayed but increased their contract by 30%. It taught me the importance of quick, proactive communication.",
        expected_decision="assess",
        expected_score_range=(6, 8),
        target_skills=["discourse_coherence", "clarity"],
        notes="Good narrative arc, concrete outcome, slight filler",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # MEDIUM QUALITY ATTEMPTS (Expected: 3-5)
    # ─────────────────────────────────────────────────────────────────────────
    AssessmentTestCase(
        name="medium_pitch_vague",
        context=[{"role": "assistant", "content": "Pitch your product to potential investors."}],
        user_response="So we have this really cool product that helps people with their daily tasks. It's very innovative and uses the latest technology. We think it could be really big and help a lot of people. The market is huge and we're well positioned.",
        expected_decision="assess",
        expected_score_range=(3, 5),
        target_skills=["clarity", "persuasiveness"],
        notes="Vague, no specifics, buzzword-heavy",
    ),
    AssessmentTestCase(
        name="medium_explanation_unfocused",
        context=[
            {
                "role": "assistant",
                "content": "Explain why your team should adopt agile methodology.",
            }
        ],
        user_response="Well, agile is really good because it helps teams work better. You have sprints and standups and stuff. It makes things more efficient, I think. A lot of companies use it now. It's more flexible than the old way of doing things, you know, waterfall.",
        expected_decision="assess",
        expected_score_range=(3, 5),
        target_skills=["clarity", "rhetorical_effectiveness"],
        notes="Unfocused, hedge words, lacks concrete benefits",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # LOW QUALITY ATTEMPTS (Expected: 1-3)
    # ─────────────────────────────────────────────────────────────────────────
    AssessmentTestCase(
        name="low_pitch_many_fillers",
        context=[{"role": "assistant", "content": "Practice pitching me on your favorite book."}],
        user_response="So, um, I think the book is, like, really good? It's about, you know, this person who like does stuff and, um, learns things. I don't know, it's just, um, I really liked it because it was, like, interesting?",
        expected_decision="assess",
        expected_score_range=(1, 3),
        target_skills=["fluency", "clarity"],
        notes="Heavy filler usage, vague, uncertain",
    ),
    AssessmentTestCase(
        name="low_explanation_confused",
        context=[{"role": "assistant", "content": "Explain the benefits of exercise."}],
        user_response="Exercise is, uh, good for you because it makes you, um, healthier? And you feel better, I guess. It's something everyone should probably do. There's like studies and stuff. It helps with, um, various things.",
        expected_decision="assess",
        expected_score_range=(1, 3),
        target_skills=["clarity", "discourse_coherence"],
        notes="Vague, many fillers, no structure",
    ),
    AssessmentTestCase(
        name="low_presentation_nervous",
        context=[{"role": "assistant", "content": "Present your quarterly results to the board."}],
        user_response="Um, so, this quarter we, uh, did pretty good I think? Sales were up, like, I don't remember exactly, maybe 15%? And, um, we hired some people... The numbers are in the, uh, the document I sent. So yeah.",
        expected_decision="assess",
        expected_score_range=(1, 3),
        target_skills=["clarity", "fluency", "confidence"],
        notes="Uncertain, imprecise, many fillers, weak close",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # EDGE CASES - SHORT BUT SUBSTANTIVE
    # ─────────────────────────────────────────────────────────────────────────
    AssessmentTestCase(
        name="short_but_good",
        context=[{"role": "assistant", "content": "Give me your main argument in one sentence."}],
        user_response="We should invest now because waiting costs more than acting.",
        expected_decision="assess",
        expected_score_range=(7, 9),
        target_skills=["conciseness", "clarity"],
        notes="Short but complete and compelling",
    ),
    AssessmentTestCase(
        name="short_but_weak",
        context=[{"role": "assistant", "content": "Summarize your proposal."}],
        user_response="It's basically a good idea that could help.",
        expected_decision="assess",
        expected_score_range=(2, 4),
        target_skills=["clarity", "conciseness"],
        notes="Too vague even for short response",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # SPECIFIC SKILL TESTS
    # ─────────────────────────────────────────────────────────────────────────
    AssessmentTestCase(
        name="lexical_sophistication_high",
        context=[{"role": "assistant", "content": "Describe the current market situation."}],
        user_response="The market exhibits considerable volatility, with macroeconomic headwinds precipitating a contraction in consumer spending. Nevertheless, our sector demonstrates remarkable resilience, suggesting latent demand that should materialize once stability returns.",
        expected_decision="assess",
        expected_score_range=(8, 10),
        target_skills=["lexical_sophistication"],
        notes="Sophisticated vocabulary, domain-appropriate",
    ),
    AssessmentTestCase(
        name="syntactic_complexity_high",
        context=[{"role": "assistant", "content": "Explain your decision-making process."}],
        user_response="After carefully evaluating the alternatives, which included both conservative and aggressive approaches, I determined that a phased implementation—starting with the highest-impact, lowest-risk components—would maximize our chances of success while preserving our ability to pivot if circumstances changed.",
        expected_decision="assess",
        expected_score_range=(8, 10),
        target_skills=["syntactic_complexity"],
        notes="Complex sentence structure, embedded clauses",
    ),
    AssessmentTestCase(
        name="discourse_coherence_high",
        context=[{"role": "assistant", "content": "Walk me through your analysis."}],
        user_response="First, we identified the core problem: declining engagement. Second, we analyzed potential causes, focusing on three key metrics. Third, we tested hypotheses through A/B experiments. Finally, based on the data, we implemented targeted changes. The result was a 40% improvement.",
        expected_decision="assess",
        expected_score_range=(8, 10),
        target_skills=["discourse_coherence"],
        notes="Clear structure, logical progression, signposting",
    ),
    AssessmentTestCase(
        name="rhetorical_effectiveness_high",
        context=[{"role": "assistant", "content": "Convince me to support your initiative."}],
        user_response="Imagine wasting 10 hours every week on tasks a machine could do in seconds. That's not hypothetical—it's happening right now in our operations. My initiative eliminates that waste. Not through layoffs, but through liberation. Your team finally has time to think, create, and innovate. The question isn't whether we can afford this change. It's whether we can afford not to make it.",
        expected_decision="assess",
        expected_score_range=(8, 10),
        target_skills=["rhetorical_effectiveness", "persuasiveness"],
        notes="Ethos, pathos, logos all present; strong framing",
    ),
]


def get_all_examples() -> list[AssessmentTestCase]:
    """Return all skill attempt test cases."""
    return SKILL_ATTEMPT_EXAMPLES


def get_examples_by_skill(skill: str) -> list[AssessmentTestCase]:
    """Return examples that test a specific skill."""
    return [ex for ex in SKILL_ATTEMPT_EXAMPLES if skill in ex.target_skills]


def get_examples_by_quality(quality: str) -> list[AssessmentTestCase]:
    """Return examples by quality level (excellent, good, medium, low)."""
    return [ex for ex in SKILL_ATTEMPT_EXAMPLES if ex.name.startswith(quality)]


def get_examples_by_score_range(min_score: int, max_score: int) -> list[AssessmentTestCase]:
    """Return examples within a score range."""
    return [
        ex
        for ex in SKILL_ATTEMPT_EXAMPLES
        if ex.expected_score_range[0] >= min_score and ex.expected_score_range[1] <= max_score
    ]


if __name__ == "__main__":
    print(f"Total skill attempt examples: {len(SKILL_ATTEMPT_EXAMPLES)}")

    print("\nBy quality level:")
    for quality in ["excellent", "good", "medium", "low", "short"]:
        examples = get_examples_by_quality(quality)
        if examples:
            print(f"  - {quality}: {len(examples)}")

    print("\nBy target skill:")
    all_skills = set()
    for ex in SKILL_ATTEMPT_EXAMPLES:
        all_skills.update(ex.target_skills)
    for skill in sorted(all_skills):
        examples = get_examples_by_skill(skill)
        print(f"  - {skill}: {len(examples)}")

    print("\nScore distribution:")
    for low, high in [(1, 3), (4, 6), (7, 10)]:
        examples = [
            ex
            for ex in SKILL_ATTEMPT_EXAMPLES
            if ex.expected_score_range[0] >= low and ex.expected_score_range[1] <= high
        ]
        print(f"  - {low}-{high}: {len(examples)}")

    print("\nAll examples:")
    for ex in SKILL_ATTEMPT_EXAMPLES:
        print(f"  [{ex.expected_score_range[0]}-{ex.expected_score_range[1]}] {ex.name}")
        print(f'       "{ex.user_response[:60]}{"..." if len(ex.user_response) > 60 else ""}"')
