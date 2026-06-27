import logging
import os

from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq

from conversation import handle_message

// Configuration

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("gryphx-bot")

groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

groq_client = Groq(api_key=groq_api_key)
app = Flask(__name__)


def get_ai_reply(sender: str, user_message: str) -> str:
    try:
        reply = handle_message(groq_client, sender, user_message)
        logger.info("Replied to %s", sender)
        return reply
    except Exception:
        logger.exception("Failed to handle message from %s", sender)
        return "Sorry, something went wrong on our end. Please try again shortly."


// Routes

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")

    if not incoming_msg:
        return str(MessagingResponse())

    ai_reply = get_ai_reply(sender, incoming_msg)

    twiml = MessagingResponse()
    twiml.message(ai_reply)
    return str(twiml)


@app.route("/", methods=["GET"])
def health_check():
    return "GRYPHX WhatsApp assistant is running."


if __name__ == "__main__":
    app.run(port=5000, debug=True)