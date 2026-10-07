"""Build the fine-tuning set for Iteration 2: labeled caller turns for the clinic agent.

Written separately from bench/eval_set.json (the 40-turn test set, which is never
trained on). Phrasings are combined from templates and fillers; any line that matches
a test-set turn is dropped. Output: bench/train_set.json

    python bench/make_train_set.py
"""
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(7)

DOCS = ["Dr. Lee", "Dr. Gomez", "Dr. Chen", "Dr. Okafor", "the nurse practitioner", "my usual doctor", "a pediatrician"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "next week", "this afternoon", "the 21st", "Saturday morning"]
MEDS = ["metformin", "my thyroid medication", "lisinopril", "my allergy pills", "my asthma inhaler", "my cholesterol meds", "my insulin"]
INS = ["Cigna", "UnitedHealthcare", "Kaiser", "Humana", "Medicaid", "my employer's plan", "a Blue Shield HMO"]
WHY = ["a sore throat", "back pain", "a follow-up on my bloodwork", "a rash that won't go away", "my yearly physical", "knee pain", "a vaccine"]

T = {
    "book_appointment": [
        "I need to come in and see {doc} about {why}.",
        "Could you fit me in {day}? It's for {why}.",
        "I'd like to make an appointment, I've had {why} for a week.",
        "Is {doc} taking new patients? I'd like to book a visit.",
        "My son needs to be seen for {why}, when's the next opening?",
        "Can I schedule a visit with {doc} {day}?",
        "I want to set up an appointment for {why}.",
        "Hi, yes, I'm calling to book a time to see someone about {why}.",
    ],
    "reschedule_appointment": [
        "I have an appointment {day} but I need a different time.",
        "Could we shift my visit with {doc} to {day}?",
        "My appointment clashes with work, can I move it to {day}?",
        "I need to change my booking from {day} to later that week.",
        "Can you bump my appointment with {doc} back a few days?",
        "I'm booked for {day}, is there anything earlier instead?",
        "Please move my check-up to {day}, the current slot doesn't work.",
    ],
    "cancel_appointment": [
        "I won't make it {day}, please cancel my appointment.",
        "Cancel my visit with {doc}, I don't need it anymore.",
        "I'd like to call off my appointment {day}.",
        "Go ahead and drop my booking with {doc}, I'm going elsewhere.",
        "I need to cancel, I'm traveling {day}.",
        "Please remove my {day} appointment from the calendar.",
    ],
    "prescription_refill": [
        "I'm running low on {med}, can the doctor renew it?",
        "Can you call in a refill for {med}?",
        "My {med} prescription ran out, I need more.",
        "Could you send a new script for {med} to my pharmacy?",
        "I need {med} refilled before the weekend.",
        "The pharmacy said {med} needs a new authorization from the doctor.",
    ],
    "billing_question": [
        "There's a charge on my statement I don't recognize.",
        "I think I was overbilled for my visit {day}.",
        "How much do I still owe on my account?",
        "Can I pay my bill over the phone?",
        "My insurance paid but you still sent me an invoice.",
        "Why was I charged a no-show fee? I came to the appointment.",
        "I'd like a refund for the double payment I made.",
    ],
    "insurance_check": [
        "Are you in network with {ins}?",
        "Do you accept {ins}?",
        "Will {ins} cover a visit for {why}?",
        "I'm on {ins}, can I still be seen at your clinic?",
        "Does my {ins} plan cover lab work there?",
        "What insurance plans do you take? I have {ins}.",
    ],
    "clinic_info": [
        "What are your hours {day}?",
        "Where do I park when I come in?",
        "What's the address of the clinic?",
        "How early do you open in the morning?",
        "Is the clinic wheelchair accessible?",
        "Are you closed on public holidays?",
        "Which floor is the clinic on?",
    ],
    "small_talk": [
        "Thanks, that's really helpful.",
        "Hi there, how are you?",
        "Perfect, that's everything, bye.",
        "Okay great, appreciate it.",
        "Hello, is this the clinic?",
        "Alright, thank you, have a good one.",
    ],
}
ESCALATE = [
    "My wife fainted and won't wake up.",
    "I think I'm having a stroke, my face feels numb.",
    "I can't breathe properly and my lips are turning blue.",
    "Put me through to a real person, I'm done with this machine.",
    "I want to speak to the office manager now.",
    "You've gotten this wrong four times, let me talk to someone.",
    "My child swallowed a bunch of pills.",
    "There's a lot of bleeding and it won't stop.",
    "Can I talk to a human please?",
    "I'm having thoughts of hurting myself.",
    "My husband has severe chest pain and is sweating.",
    "This isn't working, transfer me to a staff member.",
]
TRAIL = [
    "I was hoping to, um, maybe",
    "So my doctor told me that I should",
    "Hang on, let me just grab my",
    "Okay so the reason I'm calling is",
    "I wanted to ask about the, uh, the thing with my",
    "Right, so, last time I was there I",
    "Could you, actually, wait one second, I",
    "My appointment, the one on, um",
    "I'm calling because my mom needs",
    "Yes, so I got a letter saying that",
]


def fill(t):
    return t.format(doc=rng.choice(DOCS), day=rng.choice(DAYS), med=rng.choice(MEDS),
                    ins=rng.choice(INS), why=rng.choice(WHY))


def main():
    test = {c["caller"].strip().lower() for c in json.load(open(os.path.join(HERE, "eval_set.json")))["cases"]}
    rows, seen = [], set()

    def add(text, tool, esc, eot):
        k = text.strip().lower()
        if k in test or k in seen:
            return
        seen.add(k)
        rows.append({"caller": text, "gold": {"tool": tool, "escalate": esc, "end_of_turn": eot}})

    for tool, temps in T.items():
        for _ in range(60):
            add(fill(rng.choice(temps)), tool, False, True)
    for t in ESCALATE:
        add(t, None, True, True)
    for t in TRAIL:
        add(t, None, False, False)
    # trailing-off versions of real requests: tool still known, but the caller isn't finished
    for tool in ("book_appointment", "prescription_refill", "insurance_check", "billing_question"):
        for _ in range(4):
            s = fill(rng.choice(T[tool])).rstrip(".?!")
            add(" ".join(s.split()[: max(4, len(s.split()) - 3)]) + ", um", tool, False, False)

    rng.shuffle(rows)
    json.dump({"description": "Fine-tuning set for Iteration 2. Disjoint from eval_set.json.", "rows": rows},
              open(os.path.join(HERE, "train_set.json"), "w"), indent=1)
    by = {}
    for r in rows:
        by[r["gold"]["tool"] or ("escalate" if r["gold"]["escalate"] else "trail-off")] = by.get(
            r["gold"]["tool"] or ("escalate" if r["gold"]["escalate"] else "trail-off"), 0) + 1
    print(len(rows), "rows", by)


if __name__ == "__main__":
    main()
