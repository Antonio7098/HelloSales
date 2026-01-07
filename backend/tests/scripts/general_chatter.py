"""
General Chatter Test Cases
--------------------------
Test cases that should be SKIPPED by triage (general conversation, not skill practice).

These responses are conversational but NOT attempts at practicing a skill.
The triage service should classify these as "general" and skip assessment.

Usage:
    pytest backend/tests/scripts/general_chatter.py -v
    python backend/tests/scripts/general_chatter.py  # standalone
"""

from dataclasses import dataclass


@dataclass
class TriageTestCase:
    """A test case for triage classification."""

    name: str
    context: list[dict]  # Previous conversation turns
    user_response: str
    expected_decision: str  # "skip" or "assess"
    notes: str | None = None


GENERAL_CHATTER_EXAMPLES: list[TriageTestCase] = [
    # ─────────────────────────────────────────────────────────────────────────
    # GREETINGS & SMALL TALK
    # ─────────────────────────────────────────────────────────────────────────
    TriageTestCase(
        name="greeting_simple",
        context=[],
        user_response="Hey, how are you today?",
        expected_decision="skip",
        notes="Simple greeting, no skill practice intent",
    ),
    TriageTestCase(
        name="greeting_with_name",
        context=[],
        user_response="Hi there! I'm excited to practice today.",
        expected_decision="skip",
        notes="Greeting with enthusiasm, but not actually practicing yet",
    ),
    TriageTestCase(
        name="small_talk_weather",
        context=[{"role": "assistant", "content": "Welcome back! Ready to practice?"}],
        user_response="It's so rainy outside today, kind of gloomy.",
        expected_decision="skip",
        notes="Off-topic small talk",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # QUESTIONS ABOUT THE APP
    # ─────────────────────────────────────────────────────────────────────────
    TriageTestCase(
        name="question_about_skills",
        context=[{"role": "assistant", "content": "Welcome! I'm your speech coach."}],
        user_response="What kind of skills can you help me with?",
        expected_decision="skip",
        notes="Asking about app functionality",
    ),
    TriageTestCase(
        name="question_about_levels",
        context=[{"role": "assistant", "content": "You're currently at level 4 in Clarity."}],
        user_response="How does the leveling system work exactly?",
        expected_decision="skip",
        notes="Meta-question about the system",
    ),
    TriageTestCase(
        name="question_about_practice",
        context=[{"role": "assistant", "content": "Let's practice your presentation skills."}],
        user_response="What topics work best for practice?",
        expected_decision="skip",
        notes="Asking for guidance, not practicing",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # META CONVERSATION (ABOUT THE PRACTICE ITSELF)
    # ─────────────────────────────────────────────────────────────────────────
    TriageTestCase(
        name="meta_not_ready",
        context=[
            {"role": "assistant", "content": "Let's practice. Pitch me on your startup idea."}
        ],
        user_response="Actually, can we do something different? I'm not ready for that.",
        expected_decision="skip",
        notes="Declining to practice",
    ),
    TriageTestCase(
        name="meta_change_topic",
        context=[
            {"role": "assistant", "content": "Great job! Ready for another pitch?"},
            {"role": "user", "content": "I think I want to try something else."},
        ],
        user_response="Can we work on explaining things instead of pitching?",
        expected_decision="skip",
        notes="Negotiating practice content",
    ),
    TriageTestCase(
        name="meta_take_break",
        context=[{"role": "assistant", "content": "Let's try that one more time."}],
        user_response="I need a quick break, my throat is getting dry.",
        expected_decision="skip",
        notes="Taking a break from practice",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # SHORT ACKNOWLEDGMENTS
    # ─────────────────────────────────────────────────────────────────────────
    TriageTestCase(
        name="acknowledgment_okay",
        context=[{"role": "assistant", "content": "Try to be more concise in your explanation."}],
        user_response="Okay, got it.",
        expected_decision="skip",
        notes="Simple acknowledgment, no content to assess",
    ),
    TriageTestCase(
        name="acknowledgment_thanks",
        context=[{"role": "assistant", "content": "Good improvement on reducing filler words!"}],
        user_response="Thanks! That's helpful feedback.",
        expected_decision="skip",
        notes="Thanking for feedback",
    ),
    TriageTestCase(
        name="acknowledgment_ready",
        context=[{"role": "assistant", "content": "Ready to try again?"}],
        user_response="Yes, let's go.",
        expected_decision="skip",
        notes="Ready signal, not practice content",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # CLARIFICATION REQUESTS
    # ─────────────────────────────────────────────────────────────────────────
    TriageTestCase(
        name="clarification_audience",
        context=[{"role": "assistant", "content": "Now pitch me on renewable energy investment."}],
        user_response="Wait, do you want me to pretend I'm talking to investors or just explain the concept?",
        expected_decision="skip",
        notes="Asking for clarification before practicing",
    ),
    TriageTestCase(
        name="clarification_format",
        context=[{"role": "assistant", "content": "Explain your project."}],
        user_response="Should I give like a 30-second elevator pitch or a longer explanation?",
        expected_decision="skip",
        notes="Asking about format",
    ),
    TriageTestCase(
        name="clarification_context",
        context=[{"role": "assistant", "content": "Defend your position on remote work."}],
        user_response="Am I arguing for or against? What's the scenario?",
        expected_decision="skip",
        notes="Requesting scenario details",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # OFF-TOPIC TANGENTS
    # ─────────────────────────────────────────────────────────────────────────
    TriageTestCase(
        name="off_topic_random",
        context=[
            {"role": "assistant", "content": "That was a good attempt! Your structure was clear."}
        ],
        user_response="Random question - do you know any good podcasts about public speaking?",
        expected_decision="skip",
        notes="Off-topic question",
    ),
    TriageTestCase(
        name="off_topic_personal",
        context=[{"role": "assistant", "content": "Ready for the next exercise?"}],
        user_response="Actually I just realized I have a meeting in 10 minutes, ugh.",
        expected_decision="skip",
        notes="Personal tangent",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # FEEDBACK ON FEEDBACK
    # ─────────────────────────────────────────────────────────────────────────
    TriageTestCase(
        name="feedback_discussion",
        context=[{"role": "assistant", "content": "Your opening had too many filler words."}],
        user_response="I know, I always say 'um' when I'm nervous. Any tips for that specifically?",
        expected_decision="skip",
        notes="Discussing feedback, not practicing",
    ),
    TriageTestCase(
        name="feedback_disagreement",
        context=[{"role": "assistant", "content": "You scored a 4 on clarity."}],
        user_response="Hmm, I thought that was pretty clear actually. What specifically wasn't clear?",
        expected_decision="skip",
        notes="Discussing assessment, not practicing",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # INCOMPLETE / FALSE STARTS
    # ─────────────────────────────────────────────────────────────────────────
    TriageTestCase(
        name="false_start_restart",
        context=[{"role": "assistant", "content": "Go ahead, pitch your idea."}],
        user_response="Wait, let me start over.",
        expected_decision="skip",
        notes="False start, requesting restart",
    ),
    TriageTestCase(
        name="incomplete_thinking",
        context=[{"role": "assistant", "content": "Explain the benefits of your approach."}],
        user_response="Hmm, let me think about how to phrase this...",
        expected_decision="skip",
        notes="Still thinking, not actual attempt",
    ),
]


def get_all_examples() -> list[TriageTestCase]:
    """Return all general chatter test cases."""
    return GENERAL_CHATTER_EXAMPLES


def get_examples_by_category(category_prefix: str) -> list[TriageTestCase]:
    """Return examples matching a category prefix in their name."""
    return [ex for ex in GENERAL_CHATTER_EXAMPLES if ex.name.startswith(category_prefix)]


if __name__ == "__main__":
    print(f"Total general chatter examples: {len(GENERAL_CHATTER_EXAMPLES)}")
    print("\nCategories:")
    categories = {}
    for ex in GENERAL_CHATTER_EXAMPLES:
        cat = ex.name.split("_")[0]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count}")

    print("\nAll examples:")
    for ex in GENERAL_CHATTER_EXAMPLES:
        print(f"  [{ex.expected_decision.upper()}] {ex.name}")
        print(f'       "{ex.user_response[:60]}{"..." if len(ex.user_response) > 60 else ""}"')
