"""
RingTrace — Explainer Agent

Takes raw graph-detection output (cycles, fan-outs, shared-device clusters)
and turns it into a plain-English or Hindi explanation a bank analyst or
end user can actually understand — the "why was this flagged" layer.

Uses Groq's free-tier Llama 3.3 70B (same pattern as FarmSense).
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a fraud analyst assistant for RingTrace, a UPI fraud-ring
detection tool. You are given structured graph-detection results (cycles, fan-out
patterns, shared-device clusters) found in transaction data. Explain clearly and
concisely WHY the flagged accounts look suspicious, in plain language a bank
analyst or non-technical user can understand. Be specific: name account IDs,
describe the pattern (e.g. "money looped through 4 accounts and returned to the
sender"), and rate risk as LOW/MEDIUM/HIGH. If asked to respond in Hindi, respond
naturally in Hindi. Do not invent details not present in the data."""


def explain_findings(findings: dict, language: str = "english") -> str:
    lang_instruction = "Respond in Hindi." if language.lower() == "hindi" else "Respond in English."

    user_prompt = f"""
Graph detection results:

Cyclic laundering rings found: {findings.get('cycles', [])}

Fan-out mule patterns found: {findings.get('fanout', [])}

Shared-device/phone clusters found: {findings.get('shared_device', [])}

{lang_instruction}
Explain what was found, why each pattern is suspicious, and give an overall
risk assessment. Keep it under 200 words.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=500,
    )
    return response.choices[0].message.content


def explain_account(account_id: str, context: dict, language: str = "english") -> str:
    lang_instruction = "Respond in Hindi." if language.lower() == "hindi" else "Respond in English."

    user_prompt = f"""
Account {account_id} transaction context: {context}

{lang_instruction}
In under 100 words, assess whether this specific account's transaction pattern
looks suspicious and why, based only on the data given.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return response.choices[0].message.content
