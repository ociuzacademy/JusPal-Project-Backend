import logging
import time
from typing import Literal

from django.conf import settings
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from adminapp.models import Category

logger = logging.getLogger(__name__)


# Shown by the app under every answer
DISCLAIMER = (
    "JusPal Assistant gives general legal information, not legal advice. "
    "For your specific case, talk to an advocate or your District Legal Services Authority (DLSA)."
)

# Number of previous messages sent to Gemini
HISTORY_LIMIT = 20

# Updated fallback models from your available list
FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]

RETRYABLE_STATUS_CODES = {429, 503, 504}


class ChatbotUnavailable(Exception):
    """The chatbot can't answer right now."""


# Structured answer Gemini must return
class LegalAssistantAnswer(BaseModel):

    reply: str = Field(
        description="The answer shown to the user, in the user's language."
    )

    eligibility: Literal[
        'likely_eligible',
        'possibly_eligible',
        'not_eligible',
        'need_more_info',
        'not_applicable'
    ] = Field(
        description="Free legal aid eligibility under Section 12 of the Legal Services Authorities Act."
    )

    suggested_complaint_type: Literal[
        'Social', 'Personal', 'None'
    ] = Field(
        description="Which JusPal complaint type fits the user's problem, or None."
    )

    suggested_category: str = Field(
        description="Exactly one name from the JusPal departments list, or an empty string."
    )

    is_emergency: bool = Field(
        description="True if someone is in immediate danger."
    )


SYSTEM_INSTRUCTION = """\
You are "JusPal Assistant", the legal aid helper inside the JusPal app, used by people in India
(mainly Kerala). People describe their problem and you help them understand:

1. Whether they are eligible for FREE legal aid.
2. What they should do next.
3. Where to file their complaint (in JusPal and, if needed, outside it).
4. What it may cost.

## Free legal aid eligibility (Section 12, Legal Services Authorities Act, 1987)

A person is entitled to free legal services if they are any of:

- A member of a Scheduled Caste or Scheduled Tribe.
- A victim of human trafficking or begar (forced labour).
- A woman or a child.
- A person with a disability.
- A victim of a mass disaster, ethnic violence, caste atrocity, flood, drought, earthquake or industrial disaster.
- An industrial workman.
- In custody, including a protective home, juvenile home or psychiatric hospital/nursing home.
- A person whose annual income is below the limit fixed by the State Government.

The income limit differs by state and changes over time.
Never state an exact amount. Tell them to confirm with the DLSA.

Free legal aid covers an advocate, court fees and other case expenses.

It is given through the District Legal Services Authority (DLSA),
Taluk Legal Services Committee, State Legal Services Authority
(in Kerala: KELSA) and NALSA helpline 15100.

If you cannot decide, ask ONE short question for the missing fact
and set eligibility to need_more_info.

## Filing in JusPal

JusPal has two complaint types:

- Social: Public or civic problems affecting the community
  (roads, street lights, electricity, water, waste, public safety).
  They are sent to a department officer. The user adds a location and photos.

- Personal: The user's own legal matter
  (family/domestic violence, harassment, property, money,
  employment, criminal accusation, consumer disputes).
  They are sent to an advocate.

JusPal departments (use these exact names for suggested_category):

{categories}

Filing a complaint in JusPal is free.

When relevant, also mention the right outside authority:

- Police station / FIR for crimes.
- Consumer Disputes Redressal Commission for consumer problems.
- Labour Office for wage issues.
- Local body (panchayat / municipality / corporation) or service provider for civic problems.
- Protection Officer or Magistrate for domestic violence.

## Cost

- Eligible for legal aid: Advocate and court fees are free.
- Not eligible: Advocate fees vary by advocate, place and case.
  Court fees depend on the case type and the State's Court Fees Act.

Never invent exact amounts or fee tables.
Explain that costs vary and how to find out.

## Emergencies

If anyone is in immediate danger (violence, threats, a missing child, suicide risk),
set is_emergency to true and put the helplines FIRST in the reply:

- Emergency: 112
- Women helpline: 181
- Child helpline: 1098
- Cyber crime: 1930

Then give the rest of the guidance.

## Style

- Reply in the same language the user writes in (English, Malayalam, Manglish, Hindi...).
- Be warm and plain-spoken.
- Keep it short: a one-line answer first, then up to 5 short bullet points or numbered steps.
- Use plain text with "-" bullets or "1." steps.
- Don't ask for or repeat sensitive details you don't need (Aadhaar number, bank details).
- You only help with legal aid, rights and complaints.
- Politely decline unrelated requests and say what you can help with.
- Never claim to be a lawyer, never promise an outcome,
  and don't make up laws, section numbers or fees.
"""


def _category_names():
    return list(
        Category.objects.order_by('name').values_list('name', flat=True)
    )


def _build_instruction(categories):
    listed = "\n".join(
        f"- {name}" for name in categories
    ) or "- (no departments set up yet)"

    return SYSTEM_INSTRUCTION.replace("{categories}", listed)


def _get_client():
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ChatbotUnavailable(
            "The chatbot is not configured. API key is missing."
        )

    http_options = types.HttpOptions(
        timeout=25000,  # 25 seconds per attempt
    )

    return genai.Client(
        api_key=api_key,
        http_options=http_options,
    )


def _parse_structured_answer(response) -> LegalAssistantAnswer:
    if response is None:
        raise ChatbotUnavailable(
            "The assistant could not generate a response. Please try again."
        )

    answer = getattr(response, "parsed", None)
    if isinstance(answer, LegalAssistantAnswer):
        return answer

    try:
        return LegalAssistantAnswer.model_validate_json(response.text or "")
    except Exception as exc:
        logger.warning(
            "Gemini returned no usable structured answer: %r",
            (response.text or "")[:200],
        )
        raise ChatbotUnavailable(
            "Sorry, I couldn't answer that. Please rephrase your question."
        ) from exc


def ask_legal_assistant(history, message):
    """
    Ask Gemini about the user's message.

    history:
        Earlier messages, oldest first.

    Returns:
        dict with reply, eligibility, suggested_complaint_type,
        suggested_category, is_emergency.

    Raises:
        ChatbotUnavailable if no answer could be produced.
    """
    client = _get_client()

    contents = [
        types.Content(
            role='model' if item['role'] == 'assistant' else 'user',
            parts=[types.Part.from_text(text=item['content'])],
        )
        for item in history[-HISTORY_LIMIT:]
    ]

    contents.append(
        types.Content(
            role='user',
            parts=[types.Part.from_text(text=message)],
        )
    )

    categories = _category_names()

    config = types.GenerateContentConfig(
        system_instruction=_build_instruction(categories),
        response_mime_type='application/json',
        response_schema=LegalAssistantAnswer,
        temperature=0.3,
    )

    primary_model = getattr(settings, "GEMINI_MODEL", None) or "gemini-3.8-flash"
    models_to_try = []
    for model_name in [primary_model, *FALLBACK_MODELS]:
        if model_name and model_name not in models_to_try:
            models_to_try.append(model_name)

    parsed_answer = None
    last_error_msg = "The AI service is temporarily unavailable. Please try again."

    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                parsed_answer = _parse_structured_answer(response)
                break

            except errors.APIError as exc:
                logger.warning(
                    "Gemini API error on model %s (attempt %d/3): %s - %s",
                    model_name,
                    attempt + 1,
                    exc.code,
                    exc.message,
                )

                if exc.code == 429:
                    last_error_msg = "Gemini usage limit reached. Please try again later."
                elif exc.code in (503, 504):
                    last_error_msg = "The AI service is temporarily unavailable. Please try again."
                elif exc.code == 404:
                    last_error_msg = f"Configured model '{model_name}' is not available."
                    break
                else:
                    last_error_msg = "Something went wrong. Please try again."
                    break

                if exc.code in RETRYABLE_STATUS_CODES and attempt < 2:
                    time.sleep(2 ** attempt)  # 1s, 2s backoff
                else:
                    break

            except ChatbotUnavailable as exc:
                last_error_msg = str(exc)
                break

            except Exception:
                logger.exception("Gemini request failed on model %s", model_name)
                last_error_msg = "The assistant could not be reached. Please try again."
                break

        if parsed_answer is not None:
            break

    if parsed_answer is None:
        raise ChatbotUnavailable(last_error_msg)

    category = None
    name = (parsed_answer.suggested_category or '').strip()
    if name:
        match = Category.objects.filter(name__iexact=name).first()
        if match:
            category = {
                'id': match.id,
                'name': match.name,
            }

    complaint_type = parsed_answer.suggested_complaint_type

    return {
        'reply': parsed_answer.reply.strip(),
        'eligibility': parsed_answer.eligibility,
        'suggested_complaint_type': (
            None if complaint_type == 'None' else complaint_type
        ),
        'suggested_category': category,
        'is_emergency': parsed_answer.is_emergency,
    }