"""
Deldey Employment Agency — Telegram Registration Bot
Stack: FastAPI + aiogram (webhook mode) + Google Sheets via gspread
Deployment: Vercel Serverless
"""

import os
import json
import logging
from typing import Any

import gspread
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment variables (set these in Vercel dashboard or .env locally)
# ---------------------------------------------------------------------------
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET: str = os.environ["WEBHOOK_SECRET"]          # X-Telegram-Bot-Api-Secret-Token
GOOGLE_SHEET_ID: str = os.environ["GOOGLE_SHEET_ID"]        # The spreadsheet ID from the URL
GOOGLE_CREDENTIALS_JSON: str = os.environ["GOOGLE_CREDENTIALS_JSON"]  # Full JSON string of service account

# ---------------------------------------------------------------------------
# Bot & Dispatcher
# ---------------------------------------------------------------------------
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Deldey Employment Agency Bot")

# ---------------------------------------------------------------------------
# Google Sheets helper
# ---------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_sheet():
    """Authenticate and return the first worksheet of the configured spreadsheet."""
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    return spreadsheet.sheet1


def append_applicant(data: dict) -> None:
    """Append one row with applicant data to the Google Sheet."""
    sheet = get_sheet()
    row = [
        data.get("full_name"),
        data.get("age"),
        data.get("profession"),
        data.get("education"),
        data.get("experience"),
        data.get("primary_phone"),
        data.get("secondary_phone"),
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    logger.info("Appended row to Google Sheet: %s", row)


# ---------------------------------------------------------------------------
# Conversation State Machine
# ---------------------------------------------------------------------------
class Registration(StatesGroup):
    full_name       = State()
    age             = State()
    profession      = State()
    education       = State()
    experience      = State()
    primary_phone   = State()
    secondary_phone = State()


# ---------------------------------------------------------------------------
# Guard: reject non-text messages gracefully
# ---------------------------------------------------------------------------
async def reject_non_text(message: types.Message) -> bool:
    """
    Returns True if the message is acceptable (has text).
    Sends a polite nudge and returns False otherwise.
    """
    if message.text:
        return True
    await message.answer(
        "🙏 Please provide the requested information in *text format*.",
        parse_mode="Markdown",
    )
    return False


# ---------------------------------------------------------------------------
# /start — entry point
# ---------------------------------------------------------------------------
@dp.message(F.text.startswith("/start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Registration.full_name)
    await message.answer(
        "👋 Welcome to *Deldey Employment Agency*!\n\n"
        "We're excited to have you register with us. "
        "I'll collect a few details to get your profile set up.\n\n"
        "Let's begin — what is your *Full Name*?",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Step 1 — Full Name
# ---------------------------------------------------------------------------
@dp.message(Registration.full_name)
async def step_full_name(message: types.Message, state: FSMContext) -> None:
    if not await reject_non_text(message):
        return
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Registration.age)
    await message.answer("Great! How old are you? Please enter your *Age*.", parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Step 2 — Age
# ---------------------------------------------------------------------------
@dp.message(Registration.age)
async def step_age(message: types.Message, state: FSMContext) -> None:
    if not await reject_non_text(message):
        return
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Please enter a valid numeric age (e.g. *28*).", parse_mode="Markdown")
        return
    await state.update_data(age=message.text.strip())
    await state.set_state(Registration.profession)
    await message.answer("What is your *Profession* or Job Title?", parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Step 3 — Profession
# ---------------------------------------------------------------------------
@dp.message(Registration.profession)
async def step_profession(message: types.Message, state: FSMContext) -> None:
    if not await reject_non_text(message):
        return
    await state.update_data(profession=message.text.strip())
    await state.set_state(Registration.education)
    await message.answer(
        "What is your highest level of *Education*?\n_(e.g. BSc Computer Science, HND Accounting)_",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Step 4 — Education
# ---------------------------------------------------------------------------
@dp.message(Registration.education)
async def step_education(message: types.Message, state: FSMContext) -> None:
    if not await reject_non_text(message):
        return
    await state.update_data(education=message.text.strip())
    await state.set_state(Registration.experience)
    await message.answer(
        "How many *Years of Experience* do you have in your field?",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Step 5 — Experience
# ---------------------------------------------------------------------------
@dp.message(Registration.experience)
async def step_experience(message: types.Message, state: FSMContext) -> None:
    if not await reject_non_text(message):
        return
    await state.update_data(experience=message.text.strip())
    await state.set_state(Registration.primary_phone)
    await message.answer(
        "Please enter your *Primary Phone Number* (with country code, e.g. +234XXXXXXXXXX).",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Step 6 — Primary Phone
# ---------------------------------------------------------------------------
@dp.message(Registration.primary_phone)
async def step_primary_phone(message: types.Message, state: FSMContext) -> None:
    if not await reject_non_text(message):
        return
    await state.update_data(primary_phone=message.text.strip())
    await state.set_state(Registration.secondary_phone)
    await message.answer(
        "Almost done! Please enter your *Secondary / WhatsApp Phone Number*.\n"
        "_(Type *skip* if you don't have one.)_",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Step 7 — Secondary Phone (final step)
# ---------------------------------------------------------------------------
@dp.message(Registration.secondary_phone)
async def step_secondary_phone(message: types.Message, state: FSMContext) -> None:
    if not await reject_non_text(message):
        return

    secondary = message.text.strip()
    if secondary.lower() == "skip":
        secondary = "N/A"

    await state.update_data(secondary_phone=secondary)
    data = await state.get_data()
    await state.clear()

    # Persist to Google Sheets
    try:
        append_applicant(data)
        success = True
    except Exception as exc:
        logger.error("Failed to write to Google Sheets: %s", exc)
        success = False

    if success:
        await message.answer(
            "✅ *Registration Complete!*\n\n"
            "Thank you for registering with *Deldey Employment Agency*. "
            "Our team will review your profile and reach out to you shortly.\n\n"
            "Good luck! 🌟",
            parse_mode="Markdown",
        )
    else:
        await message.answer(
            "⚠️ Your information was received, but we encountered a technical issue saving it. "
            "Please contact our support team directly. We apologise for the inconvenience."
        )


# ---------------------------------------------------------------------------
# Catch-all: handle stickers, voice notes, files, etc. outside a state
# ---------------------------------------------------------------------------
@dp.message()
async def catch_all(message: types.Message) -> None:
    if not message.text:
        await message.answer(
            "Please provide the requested information in text format."
        )
        return
    await message.answer(
        "👋 Send /start to begin your registration with *Deldey Employment Agency*.",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
    # ── Security: validate the secret token ──────────────────────────────
    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret_header != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: invalid secret token")

    # ── Acknowledge Telegram immediately (must be fast) ───────────────────
    body: Any = await request.json()

    async def process_update() -> None:
        update = Update(**body)
        await dp.feed_update(bot=bot, update=update)

    background_tasks.add_task(process_update)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "Deldey Employment Agency Bot is running 🚀"}