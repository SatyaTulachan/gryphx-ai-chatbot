# GRYPHX WhatsApp Assistant

A premium AI shopping assistant for **GRYPHX**, delivered directly through
WhatsApp — the channel the brand's customers already use for checkout.

Feels like brand support from Nike/Uniqlo/H&M: short, friendly, structured —
not a wall of AI-generated text. Built with **Flask**, **Twilio's WhatsApp
API**, and **Groq's LLM inference** (Llama 3.3 70B).

# How it works

```
Customer (WhatsApp)
       │
       ▼
  Twilio WhatsApp API  ──webhook──▶  Flask (/whatsapp)
       ▲                                   │
       │                                   ▼
       └──────────── reply ──────  conversation.py
                                    (state machine + Groq LLM)
```

1. A customer messages the brand's WhatsApp number.
2. Twilio forwards it to a Flask webhook.
3. `conversation.py` decides how to respond:
   - **Structured flows** (main menu, step-by-step size guidance) are
     handled by an explicit state machine — so the bot never re-asks a
     question it already has the answer to, and never skips a step.
   - **Free text** ("show me your t-shirts", "do you have black shirts?")
     is classified by a Groq LLM call into one of a fixed set of intents,
     then routed into the same structured flows.
   - **Open-ended product questions** are answered by an LLM call that is
     restricted to the catalog data in `catalog.py` only — it cannot
     invent product details that aren't there.
4. The reply is sent back through Twilio to the customer.

# Project structure

| File | Responsibility |
|---|---|
| `app.py` | Flask app + Twilio webhook (the "wiring") |
| `conversation.py` | State machine, intent routing, message templates |
| `catalog.py` | Product data — the single source of truth |
| `sizing.py` | Height/weight → size recommendation logic |

# Features

- **Numbered main menu** *and* natural free-text understanding — customers
  can tap "1" or type "show me your t-shirts" and land in the same flow.
- **Step-by-step size guidance** — asks height, then weight, one at a time,
  and recommends the closest available size (with a graceful message if
  the customer is outside the available range, while still suggesting the
  closest option).
- **Per-customer state, persisted to disk** — survives server restarts,
  so a customer can pick up mid-conversation.
- **Catalog-grounded answers** — the LLM is only allowed to draw on actual
  product data, so it can't invent colors, sizes, or materials that don't
  exist.
- **Universal "menu" command** to bail out of any flow at any time.
- **Structured logging and error handling.**

# Tech stack

| Component | Choice | Why |
|---|---|---|
| Web framework | Flask | Lightweight, ideal for a single-webhook service |
| Messaging | Twilio WhatsApp API | Fastest path to a real WhatsApp integration |
| LLM inference | Groq (Llama 3.3 70B) | Free tier, very low latency |
| Tunneling (dev) | ngrok | Exposes local Flask server for Twilio webhooks |

# Setup

```bash
git clone <your-repo-url>
cd gryphx-bot
python -m venv venv
source venv/bin/activate      # or venv/bin/activate.fish on fish shell
pip install -r requirements.txt

cp .env.example .env          # then add your GROQ_API_KEY
python app.py
```

In a second terminal, expose the server and wire it to Twilio's sandbox:

```bash
ngrok http 5000
```

Paste the resulting `https://<id>.ngrok-free.app/whatsapp` URL into your
Twilio Sandbox's **"When a message comes in"** webhook field.

# Potential next steps

- Migrate from Twilio Sandbox to Meta's WhatsApp Cloud API for a permanent
  production number (no 72-hour session expiry).
- Replace the JSON file store with a proper database for state + history.
- Add an admin dashboard to review conversations and handle escalations
  (e.g. order-status questions) flagged for a human.
- Deploy to a small VPS or platform like Render/Railway to remove the
  dependency on a locally running ngrok tunnel.

# Disclaimer

This is a personal/portfolio project built for GRYPHX, an independent
streetwear brand. It is not affiliated with or endorsed by Twilio or Groq
beyond standard API usage.