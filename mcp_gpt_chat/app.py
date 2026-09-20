import json
import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from openai import OpenAI
from anthropic import Anthropic


OPTIONS_FILE = Path("/data/options.json")
CONVERSATION_FILE = Path("/data/conversation.json")
HTML_DIR = Path(__file__).resolve().parent / "www"

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


# ============================================================
# Einstellungen
# ============================================================

def load_options():
    """Liest die Add-on-Einstellungen."""

    if not OPTIONS_FILE.exists():
        return {}

    try:
        with OPTIONS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        app.logger.exception("Fehler beim Lesen von options.json")
        return {}


def get_provider():
    """Liefert den ausgewählten KI-Anbieter."""

    options = load_options()

    provider = str(
        options.get("provider", "openai")
    ).strip().lower()

    if provider not in ("openai", "anthropic"):
        provider = "openai"

    return provider


# ============================================================
# OpenAI
# ============================================================

def get_client():
    """Erstellt den OpenAI-Client."""

    options = load_options()
    api_key = str(options.get("openai_api_key", "")).strip()

    if not api_key:
        raise RuntimeError("OpenAI API-Key ist nicht konfiguriert.")

    return OpenAI(api_key=api_key)


def get_model():
    """Liefert das konfigurierte OpenAI-Modell."""

    options = load_options()

    return str(
        options.get("openai_model", "gpt-5.6-luna")
    ).strip()


# ============================================================
# Anthropic / Claude
# ============================================================

def get_anthropic_client():
    """Erstellt den Anthropic-Client."""

    options = load_options()
    api_key = str(options.get("anthropic_api_key", "")).strip()

    if not api_key:
        raise RuntimeError("Anthropic API-Key ist nicht konfiguriert.")

    return Anthropic(api_key=api_key)


def get_anthropic_model():
    """Liefert das konfigurierte Claude-Modell."""

    options = load_options()

    return str(
        options.get("anthropic_model", "claude-sonnet-4-5")
    ).strip()


# ============================================================
# Allgemeine Einstellungen
# ============================================================

def get_mcp_url():
    """Liefert die konfigurierte Home-Assistant-MCP-URL."""

    options = load_options()

    return str(
        options.get("ha_mcp_url", "")
    ).strip()


def get_assistant_name():
    """Liefert den konfigurierten Namen des Assistenten."""

    options = load_options()

    return (
        str(options.get("assistant_name", "Assist")).strip()
        or "Assist"
    )


def get_user_name():
    """Liefert den konfigurierten Namen des Benutzers."""

    options = load_options()

    return (
        str(options.get("user_name", "User")).strip()
        or "User"
    )


def get_instructions():
    """Liefert den konfigurierten Instruction-Prompt."""

    options = load_options()

    instructions = str(
        options.get("instructions", "")
    ).strip()

    if instructions:
        return instructions

    return (
        "Du bist der persönliche Assistent des Benutzers. "
        "Antworte auf Deutsch, sei hilfreich und präzise."
    )


def get_full_instructions():
    """Erweitert die Instructions um die konfigurierten Namen."""

    return (
        get_instructions()
        + "\n\n"
        + f"Dein Name ist {get_assistant_name()}. "
        + f"Der Benutzer heißt {get_user_name()}. "
        + "Verwende diese Namen passend und natürlich im Gespräch."
    )


# ============================================================
# OpenAI Conversation
# ============================================================

def load_conversation_id():
    """
    Lädt die gespeicherte OpenAI Conversation-ID.

    Das alte Format bleibt vollständig kompatibel:

    {
        "conversation_id": "conv_..."
    }
    """

    if not CONVERSATION_FILE.exists():
        return None

    try:
        with CONVERSATION_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        conversation_id = data.get("conversation_id")

        if conversation_id:
            return str(conversation_id)

        conversation_id = (
            data.get("openai", {})
            .get("conversation_id")
        )

        if conversation_id:
            return str(conversation_id)

    except Exception:
        app.logger.exception(
            "Fehler beim Lesen der OpenAI Conversation-ID"
        )

    return None


def save_conversation_id(conversation_id):
    """Speichert die OpenAI Conversation-ID."""

    try:
        data = {}

        if CONVERSATION_FILE.exists():
            try:
                with CONVERSATION_FILE.open(
                    "r",
                    encoding="utf-8"
                ) as file:
                    existing_data = json.load(file)

                if isinstance(existing_data, dict):
                    data = existing_data

            except Exception:
                app.logger.warning(
                    "Bestehende conversation.json konnte nicht gelesen werden."
                )

        old_conversation_id = data.pop(
            "conversation_id",
            None
        )

        if "openai" not in data or not isinstance(data["openai"], dict):
            data["openai"] = {}

        if conversation_id:
            data["openai"]["conversation_id"] = conversation_id
        elif old_conversation_id:
            data["openai"]["conversation_id"] = old_conversation_id

        if "anthropic" not in data:
            data["anthropic"] = {"messages": []}

        with CONVERSATION_FILE.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception:
        app.logger.exception(
            "Fehler beim Speichern der OpenAI Conversation-ID"
        )
        raise


def get_or_create_conversation(client):
    """Lädt eine bestehende OpenAI Conversation oder erstellt eine neue."""

    conversation_id = load_conversation_id()

    if conversation_id:
        return conversation_id

    app.logger.info(
        "Keine OpenAI Conversation vorhanden. Erstelle eine neue."
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

    save_conversation_id(conversation_id)

    app.logger.info(
        "Neue OpenAI Conversation erstellt: %s",
        conversation_id
    )

    return conversation_id


# ============================================================
# Claude Conversation
# ============================================================
# Claude wird bewusst zustandslos verwendet. Es wird keine lokale
# Nachrichten-History gespeichert oder an Anthropic gesendet.

# ============================================================
# Anthropic MCP
# ============================================================

def get_anthropic_mcp_servers():
    """Erstellt die MCP-Server-Konfiguration für Claude."""

    mcp_url = get_mcp_url()

    if not mcp_url:
        return []

    return [
        {
            "type": "url",
            "url": mcp_url,
            "name": "home_assistant",
        }
    ]


def get_anthropic_mcp_tools():
    """Erstellt die MCP-Toolset-Konfiguration für Claude."""

    if not get_mcp_url():
        return []

    return [
        {
            "type": "mcp_toolset",
            "mcp_server_name": "home_assistant",
        }
    ]


# ============================================================
# OpenAI MCP
# ============================================================

def get_openai_tools():
    """Erstellt die MCP-Konfiguration für OpenAI."""

    mcp_url = get_mcp_url()

    if not mcp_url:
        return []

    return [
        {
            "type": "mcp",
            "server_label": "home_assistant",
            "server_url": mcp_url,
            "require_approval": "never",
        }
    ]


# ============================================================
# API Config
# ============================================================

@app.get("/api/config")
def config():
    """Liefert die für die Oberfläche benötigten Einstellungen."""

    provider = get_provider()

    if provider == "openai":
        model = get_model()
    else:
        model = get_anthropic_model()

    return jsonify({
        "provider": provider,
        "assistant_name": get_assistant_name(),
        "user_name": get_user_name(),
        "model": model,
    })


# ============================================================
# Begrüßung
# ============================================================

@app.get("/api/greeting")
def greeting():
    """Erzeugt eine kurze Begrüßung."""

    try:
        provider = get_provider()

        assistant_name = get_assistant_name()
        user_name = get_user_name()

        greeting_instructions = (
            get_instructions()
            + "\n\n"
            + f"Du heißt {assistant_name}. "
            + f"Der Benutzer heißt {user_name}. "
            + "Erzeuge für das neu geöffnete Chatfenster "
            + "eine kurze, wechselnde Begrüßung. "
            + "Sie soll natürlich wirken, maximal 2 kurze Sätze "
            + "haben und nicht mit dem Namen des Benutzers beginnen, "
            + "weil der Name bereits oberhalb angezeigt wird. "
            + "Keine Anführungszeichen."
        )

        if provider == "openai":
            client = get_client()

            response = client.responses.create(
                model=get_model(),
                instructions=greeting_instructions,
                input="Erzeuge jetzt eine kurze Begrüßung.",
            )

            text = (
                response.output_text or ""
            ).strip()

        else:
            client = get_anthropic_client()

            kwargs = {
                "model": get_anthropic_model(),
                "max_tokens": 300,
                "system": greeting_instructions,
                "messages": [
                    {
                        "role": "user",
                        "content": "Erzeuge jetzt eine kurze Begrüßung.",
                    }
                ],
            }

            mcp_servers = get_anthropic_mcp_servers()
            mcp_tools = get_anthropic_mcp_tools()

            if mcp_servers:
                kwargs["mcp_servers"] = mcp_servers

            if mcp_tools:
                kwargs["tools"] = mcp_tools

            response = client.beta.messages.create(
                **kwargs
            )

            text = get_anthropic_text(response)

        if not text:
            text = (
                f"Na, {user_name}. "
                "Was ist denn jetzt schon wieder kaputt?"
            )

        return jsonify({"text": text})

    except Exception as error:
        app.logger.exception("Fehler bei Begrüßung")

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# Chat
# ============================================================

@app.post("/api/chat")
def chat():
    """Verarbeitet eine Chat-Anfrage."""

    try:
        payload = request.get_json(silent=True) or {}

        messages = payload.get("messages", [])

        if not isinstance(messages, list):
            return jsonify({
                "error": "messages muss eine Liste sein."
            }), 400

        latest_user_message = None

        for message in reversed(messages):
            if not isinstance(message, dict):
                continue

            if message.get("role") == "user":
                content = message.get("content", "")

                if isinstance(content, str):
                    latest_user_message = content.strip()

                elif content is not None:
                    latest_user_message = str(content).strip()

                break

        if not latest_user_message:
            return jsonify({
                "error": "Keine Benutzernachricht gefunden."
            }), 400

        provider = get_provider()

        # ----------------------------------------------------
        # OpenAI
        # ----------------------------------------------------

        if provider == "openai":
            client = get_client()

            conversation_id = get_or_create_conversation(client)

            tools = get_openai_tools()

            kwargs = {
                "model": get_model(),
                "conversation": conversation_id,
                "instructions": get_full_instructions(),
                "input": [
                    {
                        "role": "user",
                        "content": latest_user_message,
                    }
                ],
            }

            if tools:
                kwargs["tools"] = tools

            response = client.responses.create(
                **kwargs
            )

            text = (
                response.output_text or ""
            ).strip()

            if not text:
                text = "Ich habe leider keine Textantwort erhalten."

            response_id = getattr(
                response,
                "id",
                None
            )

            return jsonify({
                "text": text,
                "provider": "openai",
                "conversation_id": conversation_id,
                "response_id": response_id,
            })

        # ----------------------------------------------------
        # Anthropic / Claude
        # ----------------------------------------------------

        client = get_anthropic_client()

        # Claude wird bewusst ohne Gesprächs-History verwendet.
        # Jede Anfrage startet mit genau der aktuellen Benutzernachricht.
        messages = [{
            "role": "user",
            "content": latest_user_message,
        }]

        # Claude bekommt den Benutzernamen direkt in der ersten Nachricht.
        # Es wird weiterhin keinerlei Gesprächs-History gespeichert.
        first_message = (
            f"Mein Name ist {get_user_name()}. "
            f"Merke dir meinen Namen für diese Unterhaltung.\n\n"
            f"{latest_user_message}"
        )

        kwargs = {
            "model": get_anthropic_model(),
            "max_tokens": 4096,
            "system": get_full_instructions(),
            "messages": [
                {
                    "role": "user",
                    "content": first_message,
                }
            ],
        }

        mcp_servers = get_anthropic_mcp_servers()
        mcp_tools = get_anthropic_mcp_tools()

        if mcp_servers:
            kwargs["mcp_servers"] = mcp_servers

        if mcp_tools:
            kwargs["tools"] = mcp_tools

        response = client.beta.messages.create(
            **kwargs
        )

        text = get_anthropic_text(response)

        response_id = getattr(
            response,
            "id",
            None
        )

        return jsonify({
            "text": text or "Ich habe leider keine Textantwort erhalten.",
            "provider": "anthropic",
            "response_id": response_id,
        })

    except Exception as error:
        app.logger.exception("Fehler bei Chat-Anfrage")

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# Oberfläche
# ============================================================

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
    <h1>MCP-AI-Chat</h1>
    <p>
        Die Datei www/gpt-chat.html wurde
        im App-Container nicht gefunden.
    </p>
    """, 404


# ============================================================
# Health
# ============================================================

@app.get("/health")
def health():
    """Gesundheitsprüfung der App."""

    provider = get_provider()

    if provider == "openai":
        model = get_model()

        api_configured = bool(
            str(
                load_options().get(
                    "openai_api_key",
                    ""
                )
            ).strip()
        )

    else:
        model = get_anthropic_model()

        api_configured = bool(
            str(
                load_options().get(
                    "anthropic_api_key",
                    ""
                )
            ).strip()
        )

    return jsonify({
        "status": "ok",
        "app_name": "MCP-AI-Chat",
        "provider": provider,
        "api_configured": api_configured,
        "mcp_configured": bool(get_mcp_url()),
        "model": model,
        "assistant_name": get_assistant_name(),
        "user_name": get_user_name(),
        "openai_conversation_id": bool(
            load_conversation_id()
        ),
    })


# ============================================================
# Start
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8099,
        debug=False
    )
