"""Tool catalog for the clinic voice agent.

CORE_TOOLS are what the agent actually handles. EXTRA_TOOLS are realistic
hospital-system tools used to grow the action set (up to Jev's 255-option cap)
so the scaling benchmark measures real latency against a large tool list.
"""

CORE_TOOLS = {
    "book_appointment": "Schedule a new appointment with a doctor or clinic service.",
    "reschedule_appointment": "Move an existing appointment to a different date or time.",
    "cancel_appointment": "Cancel an existing appointment.",
    "prescription_refill": "Request a refill or renewal of an existing prescription.",
    "billing_question": "Questions about a bill, charge, copay, refund or payment.",
    "insurance_check": "Check whether an insurance plan is accepted or what it covers.",
    "clinic_info": "Opening hours, address, parking, directions or general clinic information.",
    "small_talk": "Greetings, thanks, confirmations or chit-chat that need no action.",
}

REPLIES = {
    "book_appointment": "Sure, I can book that for you. Which day and time work best?",
    "reschedule_appointment": "No problem. What's the date of your current appointment, and when would you like to move it to?",
    "cancel_appointment": "I can cancel that. Can you confirm your full name and the appointment date?",
    "prescription_refill": "I'll send a refill request to your doctor. Which medication is it for?",
    "billing_question": "Let me pull up your account. Can you tell me the date on the bill you're asking about?",
    "insurance_check": "Happy to check. Which insurance provider and plan do you have?",
    "clinic_info": "We're open 8 AM to 6 PM on weekdays at 42 Maple Street, with free parking behind the building.",
    "small_talk": "You're welcome! Is there anything else I can help you with?",
}
ESCALATE_REPLY = "I'm connecting you to a member of our staff right now. Please stay on the line."
WAIT_REPLY = "Mm-hm, go on."

_DEPTS = ["cardiology", "dermatology", "radiology", "pediatrics", "orthopedics", "neurology",
          "oncology", "physiotherapy", "ophthalmology", "dental", "maternity", "psychiatry",
          "urology", "gastroenterology", "endocrinology", "pulmonology", "rheumatology",
          "ent", "allergy", "nutrition", "sleep_lab", "vaccination", "lab_tests",
          "pharmacy", "home_care"]
_ACTIONS = {
    "referral_status": "Check the status of a referral to the {d} department.",
    "lab_results": "Retrieve or explain test results issued by the {d} department.",
    "waitlist_join": "Add the patient to the {d} department waitlist.",
    "prep_instructions": "Give preparation instructions before a {d} procedure.",
    "records_request": "Request copies of medical records from the {d} department.",
    "specialist_directory": "Look up which specialists work in the {d} department.",
    "equipment_rental": "Arrange rental of medical equipment prescribed by {d}.",
    "second_opinion": "Request a second-opinion consultation in {d}.",
    "group_class": "Enroll the patient in a {d} education or support class.",
    "telehealth_link": "Send a video-visit link for a {d} telehealth session.",
}
EXTRA_TOOLS = {f"{d}_{a}": desc.format(d=d.replace("_", " "))
               for a, desc in _ACTIONS.items() for d in _DEPTS}

MAX_TOOLS = 250


def build_tools(n: int) -> dict[str, str]:
    n = max(len(CORE_TOOLS), min(int(n), MAX_TOOLS))
    extra = dict(list(EXTRA_TOOLS.items())[: n - len(CORE_TOOLS)])
    return {**CORE_TOOLS, **extra}


def reply_for(tool: str | None, escalate: float | None, end_of_turn: float | None) -> str:
    if escalate is not None and escalate >= 0.5:
        return ESCALATE_REPLY
    if end_of_turn is not None and end_of_turn < 0.5:
        return WAIT_REPLY
    return REPLIES.get(tool or "", "Let me route you to the right team for that.")
