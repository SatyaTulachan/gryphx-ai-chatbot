
import json
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

from groq import Groq

from catalog import PRODUCTS, SOCIAL
from sizing import recommend_tshirt_size, recommend_pants_size, height_to_cm

MODEL = "llama-3.3-70b-versatile"


class Stage(str, Enum):
    MAIN_MENU = "main_menu"
    SIZE_ASK_PRODUCT = "size_ask_product"
    SIZE_ASK_HEIGHT = "size_ask_height"
    SIZE_ASK_WEIGHT = "size_ask_weight"
    POST_PRODUCTS_OFFER_SIZE_HELP = "post_products_offer_size_help"


@dataclass
class CustomerState:
    stage: str = Stage.MAIN_MENU.value
    pending_product_type: Optional[str] = None  # "tshirt" | "pants"
    height_cm: Optional[float] = None
    history: list = field(default_factory=list)  # raw chat turns for the LLM

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "CustomerState":
        return CustomerState(**d)


STATE_FILE = Path("customer_states.json")


def load_states() -> dict:
    if STATE_FILE.exists():
        try:
            raw = json.loads(STATE_FILE.read_text())
            return {k: CustomerState.from_dict(v) for k, v in raw.items()}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def save_states(states: dict) -> None:
    STATE_FILE.write_text(
        json.dumps({k: v.to_dict() for k, v in states.items()}, indent=2)
    )


_states: dict[str, CustomerState] = load_states()


def get_state(sender: str) -> CustomerState:
    if sender not in _states:
        _states[sender] = CustomerState()
    return _states[sender]


def persist():
    save_states(_states)


GREETING = (
    "👋 Welcome to GRYPHX!\n\n"
    "I'm your virtual shopping assistant. How can I help you today?"
)

MAIN_MENU = (
    "Please choose one of the following:\n\n"
    "1️⃣ View Available Products\n"
    "2️⃣ Size Guidance\n"
    "3️⃣ Product Information\n"
    "4️⃣ Contact Support\n\n"
    "Or just tell me what you're looking for 🙂"
)

CONTACT_SUPPORT = (
    "📩 Need more help?\n\n"
    "You can contact our team directly.\n\n"
    f"Instagram: {SOCIAL['instagram']}\n"
    f"WhatsApp: {SOCIAL['whatsapp']}"
)

DIDNT_UNDERSTAND = "I'm sorry, I didn't quite understand that."


def format_products() -> str:
    lines = []
    for p in PRODUCTS.values():
        lines.append(f"*{p['name']}*")
        lines.append("Colors: " + ", ".join(p["colors"]))
        lines.append("Sizes: " + ", ".join(p["sizes"]))
        lines.append("")
    lines.append("Would you like help choosing the right size?")
    return "\n".join(lines)


INTENT_SYSTEM_PROMPT = """You classify a customer's WhatsApp message into ONE intent.
Reply with ONLY the intent label, nothing else.

Intents:
- view_products: wants to see products, e.g. "show me your shirts", "what t-shirts do you have"
- size_guidance: wants help picking a size, e.g. "help me find my size", "what size should I get"
- product_info: asking about material, colors, what makes the brand different, general questions
- contact_support: wants to talk to a human, or asks for Instagram/contact info
- greeting: hi/hello/hey with nothing else
- thanks: thank you messages
- goodbye: bye/goodbye messages
- menu: wants to go back to main menu
- yes: affirmative response
- no: negative response
- other: anything else, including specific product questions you can't classify confidently
"""


def classify_intent(client: Groq, message: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=20,
        )
        label = response.choices[0].message.content.strip().lower()
        valid = {
            "view_products", "size_guidance", "product_info", "contact_support",
            "greeting", "thanks", "goodbye", "menu", "yes", "no", "other",
        }
        return label if label in valid else "other"
    except Exception:
        return "other"


def answer_product_question(client: Groq, message: str) -> str:
    """Answers open-ended product questions using ONLY catalog data."""
    catalog_text = json.dumps(PRODUCTS, indent=2)
    system = (
        "You are GRYPHX's WhatsApp shopping assistant. Brand tone: friendly, "
        "professional, warm, never robotic. Keep replies under 4 short lines, "
        "mobile-friendly, minimal emoji.\n\n"
        "Answer the customer's question using ONLY this product data:\n"
        f"{catalog_text}\n\n"
        "If the answer isn't in this data, say exactly: "
        "\"I don't have that information yet. Please contact our team for more details.\" "
        "Never invent details not present above."
    )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            temperature=0.4,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "I don't have that information yet. Please contact our team for more details."



def parse_height(text: str) -> Optional[float]:
    text = text.strip().lower()

    # feet'inches  e.g. 5'9 5'9" 5 ft 9 in
    m = re.search(r"(\d)\s*(?:'|ft|feet)\s*(\d{1,2})?", text)
    if m:
        feet = int(m.group(1))
        inches = int(m.group(2)) if m.group(2) else 0
        if 3 <= feet <= 7:
            return height_to_cm(feet, inches)

    # cm e.g. 175cm, 175 cm, 175
    m = re.search(r"(\d{2,3})\s*cm", text)
    if m:
        return float(m.group(1))

    m = re.search(r"^\d{2,3}$", text)
    if m:
        val = float(m.group(0))
        if 100 <= val <= 230:  # plausible cm range
            return val

    return None


def parse_weight(text: str) -> Optional[float]:
    text = text.strip().lower()
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:kg|kgs|kilograms?)?", text)
    if m:
        val = float(m.group(1))
        if 30 <= val <= 200:
            return val
    return None


def handle_message(client: Groq, sender: str, message: str) -> str:
    state = get_state(sender)
    message_stripped = message.strip()
    lower = message_stripped.lower()

    if lower == "menu":
        state.stage = Stage.MAIN_MENU.value
        state.pending_product_type = None
        persist()
        return MAIN_MENU

    if state.stage == Stage.SIZE_ASK_PRODUCT.value:
        if "linen" in lower or "pant" in lower or lower in ("2", "linen pant"):
            state.pending_product_type = "pants"
        elif "shirt" in lower or "tshirt" in lower or "t-shirt" in lower or lower == "1":
            state.pending_product_type = "tshirt"
        else:
            return "Please let me know — T-Shirt or Linen Pant?"
        state.stage = Stage.SIZE_ASK_HEIGHT.value
        persist()
        return "What is your height? (e.g. 5'9\" or 175cm)"

    if state.stage == Stage.SIZE_ASK_HEIGHT.value:
        height_cm = parse_height(message_stripped)
        if height_cm is None:
            return "Sorry, I didn't catch that — could you share your height? (e.g. 5'9\" or 175cm)"
        state.height_cm = height_cm
        state.stage = Stage.SIZE_ASK_WEIGHT.value
        persist()
        return "Got it 👍 And what is your weight? (in kg)"

    if state.stage == Stage.SIZE_ASK_WEIGHT.value:
        weight_kg = parse_weight(message_stripped)
        if weight_kg is None:
            return "Sorry, could you share your weight in kg? (e.g. 68)"

        if state.pending_product_type == "tshirt":
            size, small, large = recommend_tshirt_size(state.height_cm, weight_kg)
            if small:
                reply = (
                    "At the moment, our smallest available size is L (42) — "
                    "that'll be your best fit. 👌"
                )
            elif large:
                reply = (
                    "Currently our largest available size is 2XL (46) — "
                    "that'll be your best fit. 👌"
                )
            else:
                reply = f"Based on your details, I'd recommend size *{size}* for our t-shirts. 👌"
        else:
            size, small, large = recommend_pants_size(state.height_cm, weight_kg)
            reply = f"Based on your details, I'd recommend size *{size}* for our linen pants. 👌"

        state.stage = Stage.MAIN_MENU.value
        state.pending_product_type = None
        state.height_cm = None
        persist()
        return reply + "\n\nType *menu* anytime to go back to the main menu."

    if state.stage == Stage.POST_PRODUCTS_OFFER_SIZE_HELP.value:
        if lower in ("yes", "y", "yeah", "sure"):
            state.stage = Stage.SIZE_ASK_PRODUCT.value
            persist()
            return "Great! What product are you buying?\n\n• T-Shirt\n• Linen Pant"
        if lower in ("no", "n", "nope"):
            state.stage = Stage.MAIN_MENU.value
            persist()
            return "No problem! " + MAIN_MENU
        # fall through to intent classification if they typed something else

    if lower in ("hi", "hello", "hey", "hi!", "hello!"):
        state.stage = Stage.MAIN_MENU.value
        persist()
        return GREETING + "\n\n" + MAIN_MENU

    if lower == "1":
        state.stage = Stage.POST_PRODUCTS_OFFER_SIZE_HELP.value
        persist()
        return format_products()

    if lower == "2":
        state.stage = Stage.SIZE_ASK_PRODUCT.value
        persist()
        return "Great! What product are you buying?\n\n• T-Shirt\n• Linen Pant"

    if lower == "3":
        return "Sure — what would you like to know? (material, colors, sizes, etc.)"

    if lower == "4":
        return CONTACT_SUPPORT

    intent = classify_intent(client, message_stripped)

    if intent == "greeting":
        state.stage = Stage.MAIN_MENU.value
        persist()
        return GREETING + "\n\n" + MAIN_MENU
    if intent == "view_products":
        state.stage = Stage.POST_PRODUCTS_OFFER_SIZE_HELP.value
        persist()
        return format_products()
    if intent == "size_guidance":
        state.stage = Stage.SIZE_ASK_PRODUCT.value
        persist()
        return "Great! What product are you buying?\n\n• T-Shirt\n• Linen Pant"
    if intent == "contact_support":
        return CONTACT_SUPPORT
    if intent == "thanks":
        return "You're very welcome! 😊 Anything else I can help with?"
    if intent == "goodbye":
        return "Thanks for stopping by GRYPHX! 👋 Have a great day."
    if intent == "menu":
        state.stage = Stage.MAIN_MENU.value
        persist()
        return MAIN_MENU
    if intent == "product_info":
        return answer_product_question(client, message_stripped)

   
    answer = answer_product_question(client, message_stripped)
    if "don't have that information" in answer.lower():
        return DIDNT_UNDERSTAND + "\n\n" + MAIN_MENU
    return answer