import json
import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from openai import OpenAI


OPTIONS_FILE = Path("/data/options.json")
CONVERSATION_FILE = Path("/data/conversation.json")
HTML_DIR = Path(__file__).resolve().parent / "www"

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


def load_options():
    """Liest die Add-on-Einstellungen."""
    if not OPTIONS_FILE.exists():
        return {}

    try:
        with OPTIONS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        app.logger.exception(
            "Fehler beim Lesen von options.json"
        )
        return {}


def get_client():
    """Erstellt den OpenAI-Client."""
    options = load_options()
    api_key = options.get(
        "openai_api_key",
        ""
    ).strip()

    if not api_key:
        raise RuntimeError(
            "OpenAI API-Key ist nicht konfiguriert."
        )

    return OpenAI(api_key=api_key)


def get_model():
    """Liefert das konfigurierte OpenAI-Modell."""
    options = load_options()

    return options.get(
        "openai_model",
        "gpt-5.6-luna"
    ).strip()


def get_mcp_url():
    """Liefert die konfigurierte Home-Assistant-MCP-URL."""
    options = load_options()

    return options.get(
        "ha_mcp_url",
        ""
    ).strip()


def get_assistant_name():
    """Liefert den konfigurierten Namen des Assistenten."""
    options = load_options()
    return options.get("assistant_name", "GPT").strip() or "GPT"


def get_user_name():
    """Liefert den konfigurierten Namen des Benutzers."""
    options = load_options()
    return options.get("user_name", "User").strip() or "User"


def get_instructions():
    """Liefert den konfigurierten Instruction-Prompt."""
    options = load_options()
    instructions = options.get("instructions", "").strip()
    if instructions:
        return instructions
    return (
        "Du bist der persönliche Assistent des Benutzers. "
        "Antworte auf Deutsch, sei hilfreich und präzise."
    )


def load_conversation_id():
    """Lädt GPTs gespeicherte OpenAI Conversation-ID."""

    if not CONVERSATION_FILE.exists():
        return None

    try:
        with CONVERSATION_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        conversation_id = data.get(
            "conversation_id"
        )

        if conversation_id:
            return str(conversation_id)

    except Exception:
        app.logger.exception(
            "Fehler beim Lesen der GPT Conversation-ID"
        )

    return None


def save_conversation_id(conversation_id):
    """Speichert GPTs OpenAI Conversation-ID."""

    try:
        with CONVERSATION_FILE.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                {
                    "conversation_id": conversation_id
                },
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception:
        app.logger.exception(
            "Fehler beim Speichern der GPT Conversation-ID"
        )

        raise


def get_or_create_conversation(client):
    """Lädt GPTs Conversation oder erstellt eine neue."""

    conversation_id = load_conversation_id()

    if conversation_id:
        return conversation_id

    app.logger.info(
        "Keine GPT Conversation vorhanden. "
        "Erstelle eine neue OpenAI Conversation."
    )

    conversation = client.conversations.create()

    conversation_id = getattr(
        conversation,
        "id",
        None
    )

    if not conversation_id:
        raise RuntimeError(
            "OpenAI hat keine Conversation-ID geliefert."
        )

    save_conversation_id(
        conversation_id
    )

    app.logger.info(
        "Neue GPT Conversation erstellt: %s",
        conversation_id
    )

    return conversation_id

@app.get("/api/config")
def config():
    """Liefert die für die Oberfläche benötigten Namen."""
    return jsonify({
        "assistant_name": get_assistant_name(),
        "user_name": get_user_name()
    })


@app.get("/api/greeting")
def greeting():
    """Erzeugt eine kurze, wechselnde Begrüßung."""
    try:
        client = get_client()
        assistant_name = get_assistant_name()
        user_name = get_user_name()

        response = client.responses.create(
            model=get_model(),
            instructions=(
                get_instructions()
                + "\n\n"
                + f"Du heißt {assistant_name}. Der Benutzer heißt {user_name}. "
                + "Erzeuge für das neu geöffnete Chatfenster eine kurze, wechselnde Begrüßung. "
                + "Sie soll natürlich wirken, maximal 2 kurze Sätze haben und nicht mit dem Namen des Benutzers beginnen, "
                + "weil der Name bereits oberhalb angezeigt wird. Keine Anführungszeichen."
            ),
            input="Erzeuge jetzt eine kurze Begrüßung."
        )

        text = (response.output_text or "").strip()
        if not text:
            text = f"Na, {user_name}. Was ist denn jetzt schon wieder kaputt?"

        return jsonify({"text": text})

    except Exception as error:
        app.logger.exception("Fehler bei Begrüßung")
        return jsonify({"error": str(error)}), 500


@app.get("/")
def index():
    """Lädt die Oberfläche."""
    local_html = HTML_DIR / "gpt-chat.html"

    if local_html.exists():
        return send_from_directory(
            str(HTML_DIR),
            "gpt-chat.html"
        )

    return """
    <h1>MCP-GPT-Chat</h1>
    <p>
        Die Datei www/gpt-chat.html wurde
        im App-Container nicht gefunden.
    </p>
    """, 404


@app.get("/health")
def health():
    """Gesundheitsprüfung der App."""

    return jsonify({
        "status": "ok",
        "app_name": "MCP-GPT-Chat",
        "mcp_configured": bool(
            get_mcp_url()
        ),
        "model": get_model(),
        "assistant_name": get_assistant_name(),
        "user_name": get_user_name(),
        "conversation_configured": bool(
            load_conversation_id()
        )
    })


@app.post("/api/chat")
def chat():
    """Verarbeitet eine Chat-Anfrage."""

    try:
        payload = request.get_json(
            silent=True
        ) or {}

        messages = payload.get(
            "messages",
            []
        )

        if not isinstance(messages, list):
            return jsonify({
                "error": "messages muss eine Liste sein."
            }), 400

        if not messages:
            return jsonify({
                "error": "Keine Nachrichten erhalten."
            }), 400

        mcp_url = get_mcp_url()

        if not mcp_url:
            return jsonify({
                "error": "Keine MCP-URL konfiguriert."
            }), 500

        client = get_client()

        conversation_id = get_or_create_conversation(
            client
        )

        tools = [
            {
                "type": "mcp",
                "server_label": "home_assistant",
                "server_url": mcp_url,
                "require_approval": "never"
            }
        ]

        model = get_model()


        latest_user_message = None

        for message in reversed(messages):
            if (
                isinstance(message, dict)
                and message.get("role") == "user"
            ):
                latest_user_message = message
                break

        if not latest_user_message:
            return jsonify({
                "error": "Keine Benutzernachricht gefunden."
            }), 400

        app.logger.info(
            "GPT startet OpenAI-Anfrage mit Modell %s",
            model
        )

        app.logger.info(
            "GPT verwendet Conversation %s",
            conversation_id
        )

        response = client.responses.create(
            model=model,
            conversation=conversation_id,
            tools=tools,
            input=[
                latest_user_message
            ],
            instructions=(
                get_instructions()
                + "\n\n"
                + f"Dein Name ist {get_assistant_name()}. Der Benutzer heißt {get_user_name()}. "
                + "Verwende diese Namen passend und natürlich im Gespräch."
            )
        )

        response_text = response.output_text or ""

        if not response_text.strip():

            output_debug = []

            for item in response.output:
                output_debug.append({
                    "type": getattr(
                        item,
                        "type",
                        None
                    ),
                    "name": getattr(
                        item,
                        "name",
                        None
                    ),
                    "status": getattr(
                        item,
                        "status",
                        None
                    ),
                    "id": getattr(
                        item,
                        "id",
                        None
                    )
                })

            response_id = getattr(
                response,
                "id",
                "unbekannt"
            )

            app.logger.error(
                "GPT erhielt keinen Antworttext. "
                "Response-ID: %s",
                response_id
            )

            return jsonify({
                "error": (
                    "OpenAI hat keinen Antworttext geliefert."
                ),
                "response_id": getattr(
                    response,
                    "id",
                    None
                ),
                "status": getattr(
                    response,
                    "status",
                    None
                ),
                "output": output_debug
            }), 502

        response_id = getattr(
            response,
            "id",
            "unbekannt"
        )

        app.logger.info(
            "GPT-Antwort erhalten. Response-ID: %s",
            response_id
        )

        return jsonify({
            "response_id": getattr(
                response,
                "id",
                None
            ),
            "conversation_id": conversation_id,
            "text": response_text
        })

    except Exception as error:

        app.logger.exception(
            "Fehler bei GPT-Anfrage"
        )

        return jsonify({
            "error": str(error)
        }), 500