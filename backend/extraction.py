import base64
import json

from groq import AsyncGroq

from core.config import GROQ_API_KEY, GROQ_VISION_MODEL

client = AsyncGroq(api_key=GROQ_API_KEY)

SCHEMA = """{
  "medications": [{"medication": "", "dosage": "", "frequency": "", "notes": ""}],
  "conditions": [{"title": "", "details": ""}],
  "allergies": [{"title": "", "details": ""}],
  "summary": ""
}"""

PROMPT = f"""You are reading a photo of a medical document such as a prescription,
a discharge summary or a medicine packet.

Extract only what is actually written in the image. Never guess a dosage, a
frequency or a drug name. If a field is unreadable or missing, use an empty
string rather than inventing a value. If the image is not a medical document,
return empty lists and say so in the summary.

Put surgeries and diagnoses under conditions. Put anything the document flags as
an allergy under allergies. Write the summary as one or two plain sentences a
patient would understand.

Return only JSON in exactly this shape:
{SCHEMA}"""


class ExtractionError(Exception):
    pass


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def normalise(payload):
    medications = []
    for item in payload.get("medications") or []:
        if not isinstance(item, dict):
            continue

        name = clean(item.get("medication"))
        if not name:
            continue

        medications.append(
            {
                "medication": name,
                "dosage": clean(item.get("dosage")),
                "frequency": clean(item.get("frequency")),
                "notes": clean(item.get("notes")),
            }
        )

    def entries(key, category):
        found = []
        for item in payload.get(key) or []:
            if isinstance(item, str):
                item = {"title": item}

            if not isinstance(item, dict):
                continue

            title = clean(item.get("title"))
            if not title:
                continue

            found.append(
                {"category": category, "title": title, "details": clean(item.get("details"))}
            )

        return found

    return {
        "medications": medications,
        "records": entries("conditions", "condition") + entries("allergies", "allergy"),
        "summary": clean(payload.get("summary")),
    }


async def extract_from_image(image_bytes: bytes, content_type: str) -> dict:
    encoded = base64.b64encode(image_bytes).decode()

    try:
        response = await client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{content_type};base64,{encoded}"},
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=1500,
        )
    except Exception as error:
        raise ExtractionError(f"The vision model could not read the image: {error}")

    raw = response.choices[0].message.content or ""

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise ExtractionError("The vision model did not return usable JSON.")

    if not isinstance(payload, dict):
        raise ExtractionError("The vision model did not return usable JSON.")

    return normalise(payload)
