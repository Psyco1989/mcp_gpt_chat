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
        with OPTIONS_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception:
        app.logger.exception(
            "Fehler beim Lesen von options.json"
        )
        return {}


def get_provider():
    """Liefert den ausgewählten KI-Anbieter."""

    options = load_options()

    provider = str(
        options.get(
            "provider",
            "openai"
        )
    ).strip().lower()

    if provider not in (
        "openai",
        "anthropic"
    ):
        provider = "openai"

    return provider


# ============================================================
# OpenAI
# ============================================================

def get_client():
    """Erstellt den OpenAI-Client."""

    options = load_options()

    api_key = options.get(
        "openai_api_key",
        ""
    )

    api_key = str(api_key).strip()

    if not api_key:
        raise RuntimeError(
            "OpenAI API-Key ist nicht konfiguriert."
        )

    return OpenAI(
        api_key=api_key
    )


def get_model():
    """Liefert das konfigurierte OpenAI-Modell."""

    options = load_options()

    return str(
        options.get(
            "openai_model",
            "gpt-5.6-luna"
        )
    ).strip()


# ============================================================
# Anthropic / Claude
# ============================================================

def get_anthropic_client():
    """Erstellt den Anthropic-Client."""

    options = load_options()

    api_key = options.get(
        "anthropic_api_key",
        ""
    )

    api_key = str(api_key).strip()

    if not api_key:
        raise RuntimeError(
            "Anthropic API-Key ist nicht konfiguriert."
        )

    return Anthropic(
        api_key=api_key
    )


def get_anthropic_model():
    """Liefert das konfigurierte Claude-Modell."""

    options = load_options()

    return str(
        options.get(
            "anthropic_model",
            "claude-sonnet-5"
        )
    ).strip()


# ============================================================
# Allgemeine Einstellungen
# ============================================================

def get_mcp_url():
    """Liefert die konfigurierte Home-Assistant-MCP-URL."""

    options = load_options()

    return str(
        options.get(
            "ha_mcp_url",
            ""
        )
    ).strip()


def get_assistant_name():
    """Liefert den konfigurierten Namen des Assistenten."""

    options = load_options()

    return (
        str(
            options.get(
                "assistant_name",
                "Assist"
            )
        ).strip()
        or "Assist"
    )


def get_user_name():
    """Liefert den konfigurierten Namen des Benutzers."""

    options = load_options()

    return (
        str(
            options.get(
                "user_name",
                "User"
            )
        ).strip()
        or "User"
    )


def get_instructions():
    """Liefert den konfigurierten Instruction-Prompt."""

    options = load_options()

    instructions = str(
        options.get(
            "instructions",
            ""
        )
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
    Lädt GPTs gespeicherte OpenAI Conversation-ID.

    Das alte Format bleibt vollständig kompatibel:

    {
        "conversation_id": "conv_..."
    }
    """

    if not CONVERSATION_FILE.exists():
        return None

    try:
        with CONVERSATION_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        # Altes / bestehendes OpenAI-Format
        conversation_id = data.get(
            "conversation_id"
        )

        if conversation_id:
            return str(
                conversation_id
            )

        # Neues Provider-Format
        conversation_id = (
            data
            .get("openai", {})
            .get("conversation_id")
        )

        if conversation_id:
            return str(
                conversation_id
            )

    except Exception:
        app.logger.exception(
            "Fehler beim Lesen der OpenAI Conversation-ID"
        )

    return None


def save_conversation_id(
    conversation_id
):
    """
    Speichert die OpenAI Conversation-ID.

    Bestehende Claude-Daten bleiben erhalten.
    """

    try:

        data = {}

        if CONVERSATION_FILE.exists():

            try:

                with CONVERSATION_FILE.open(
                    "r",
                    encoding="utf-8"
                ) as file:
                    existing_data = json.load(
                        file
                    )

                if isinstance(
                    existing_data,
                    dict
                ):
                    data = existing_data

            except Exception:
                app.logger.warning(
                    "Bestehende conversation.json "
                    "konnte nicht gelesen werden."
                )

        # Falls bisher das alte Format verwendet wurde,
        # wird es sauber in das Provider-Format überführt.
        old_conversation_id = data.pop(
            "conversation_id",
            None
        )

        if "openai" not in data:
            data["openai"] = {}

        data["openai"][
            "conversation_id"
        ] = conversation_id

        # Bestehende Claude-Daten nicht überschreiben
        if "anthropic" not in data:
            data["anthropic"] = {
                "messages": []
            }

        # Alte ID nur dann übernehmen,
        # wenn keine neue vorhanden wäre.
        if (
            old_conversation_id
            and not data["openai"].get(
                "conversation_id"
            )
        ):
            data["openai"][
                "conversation_id"
            ] = old_conversation_id

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


def get_or_create_conversation(
    client
):
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


# ============================================================
# Claude Conversation
# ============================================================

def load_anthropic_messages():
    """
    Lädt den lokalen Claude-Gesprächsverlauf.

    OpenAI wird davon nicht beeinflusst.
    """

    if not CONVERSATION_FILE.exists():
        return []

    try:

        with CONVERSATION_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(
                file
            )

        # Neues Provider-Format
        if isinstance(
            data,
            dict
        ):

            anthropic_data = data.get(
                "anthropic",
                {}
            )

            if isinstance(
                anthropic_data,
                dict
            ):

                messages = anthropic_data.get(
                    "messages",
                    []
                )

                if isinstance(
                    messages,
                    list
                ):
                    return messages

    except Exception:
        app.logger.exception(
            "Fehler beim Lesen des Claude-Verlaufs"
        )

    return []


def save_anthropic_messages(
    messages
):
    """Speichert den Claude-Gesprächsverlauf."""

    try:

        data = {}

        if CONVERSATION_FILE.exists():

            try:

                with CONVERSATION_FILE.open(
                    "r",
                    encoding="utf-8"
                ) as file:
                    existing_data = json.load(
                        file
                    )

                if isinstance(
                    existing_data,
                    dict
                ):
                    data = existing_data

            except Exception:
                app.logger.warning(
                    "Bestehende conversation.json "
                    "konnte nicht gelesen werden."
                )

        # Altes OpenAI-Format gegebenenfalls übernehmen
        old_conversation_id = data.get(
            "conversation_id"
        )

        if old_conversation_id:

            data.setdefault(
                "openai",
                {}
            )

            data["openai"][
                "conversation_id"
            ] = old_conversation_id

            data.pop(
                "conversation_id",
                None
            )

        # OpenAI-Bereich erhalten
        if "openai" not in data:
            data["openai"] = {}

        # Claude-Bereich schreiben
        data["anthropic"] = {
            "messages": messages
        }

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
            "Fehler beim Speichern des Claude-Verlaufs"
        )
        raise


def serialize_anthropic_block(
    block
):
    """
    Konvertiert einen Anthropic-Content-Block
    in ein JSON-kompatibles Dictionary.

    MCP-Tool-Use und MCP-Tool-Result werden dabei
    ebenfalls erhalten.
    """

    if isinstance(
        block,
        dict
    ):
        return block

    try:

        if hasattr(
            block,
            "model_dump"
        ):

            return block.model_dump(
                exclude_none=True
            )

    except Exception:
        pass

    try:

        if hasattr(
            block,
            "to_dict"
        ):

            return block.to_dict()

    except Exception:
        pass

    result = {}

    block_type = getattr(
        block,
        "type",
        None
    )

    if block_type:
        result["type"] = block_type

    # Häufige Anthropic-Content-Felder
    fields = (
        "text",
        "id",
        "name",
        "server_name",
        "tool_use_id",
        "input",
        "content",
        "is_error",
        "thinking",
        "signature"
    )

    for field in fields:

        value = getattr(
            block,
            field,
            None
        )

        if value is None:
            continue

        try:

            json.dumps(
                value
            )

            result[field] = value

        except TypeError:

            try:

                if hasattr(
                    value,
                    "model_dump"
                ):

                    result[field] = value.model_dump(
                        exclude_none=True
                    )

                else:

                    result[field] = str(
                        value
                    )

            except Exception:

                result[field] = str(
                    value
                )

    return result


def serialize_anthropic_response(
    response
):
    """
    Speichert die komplette Claude-Antwort.

    Dadurch bleiben auch MCP-Content-Blöcke
    im Gesprächsverlauf erhalten.
    """

    content = getattr(
        response,
        "content",
        []
    )

    result = []

    if not isinstance(
        content,
        list
    ):
        return result

    for block in content:

        serialized = serialize_anthropic_block(
            block
        )

        if serialized:
            result.append(
                serialized
            )

    return result


def get_anthropic_text(
    response
):
    """Extrahiert den sichtbaren Text aus einer Claude-Antwort."""

    text_parts = []

    content = getattr(
        response,
        "content",
        []
    )

    if not isinstance(
        content,
        list
    ):
        return ""

    for block in content:

        block_type = getattr(
            block,
            "type",
            None
        )

        if isinstance(
            block,
            dict
        ):
            block_type = block.get(
                "type"
            )

        if block_type != "text":
            continue

        if isinstance(
            block,
            dict
        ):
            text = block.get(
                "text",
                ""
            )
        else:
            text = getattr(
                block,
                "text",
                ""
            )

        if text:
            text_parts.append(
                str(text)
            )

    return "\n".join(
        text_parts
    ).strip()


# ============================================================
# API Config
# ============================================================

@app.get("/api/config")
def config():
    """Liefert die für die Oberfläche benötigten Namen."""

    provider = get_provider()

    if provider == "openai":

        model = get_model()

    else:

        model = get_anthropic_model()

    return jsonify({
        "provider": provider,
        "assistant_name": get_assistant_name(),
        "user_name": get_user_name(),
        "model": model
    })


# ============================================================
# Begrüßung
# ============================================================

@app.get("/api/greeting")
def greeting():
    """Erzeugt eine kurze, wechselnde Begrüßung."""

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

        # ----------------------------------------------------
        # OpenAI
        # ----------------------------------------------------

        if provider == "openai":

            client = get_client()

            response = client.responses.create(
                model=get_model(),
                instructions=greeting_instructions,
                input="Erzeuge jetzt eine kurze Begrüßung."
            )

            text = (
                response.output_text
                or ""
            ).strip()

        # ----------------------------------------------------
        # Anthropic
        # ----------------------------------------------------

        else:

            client = get_anthropic_client()

            response = client.beta.messages.create(
                model=get_anthropic_model(),
                max_tokens=300,
                system=greeting_instructions,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Erzeuge jetzt eine kurze Begrüßung."
                        )
                    }
                ]
            )

            text = get_anthropic_text(
                response
            )

        if not text:

            text = (
                f"Na, {user_name}. "
                "Was ist denn jetzt schon wieder kaputt?"
            )

        return jsonify({
            "text": text
        })

    except Exception as error:

        app.logger.exception(
            "Fehler bei Begrüßung"
        )

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

        conversation_configured = bool(
            load_conversation_id()
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

        conversation_configured = bool(
            load_anthropic_messages()
        )

    return jsonify({
        "status": "ok",
        "app_name": "MCP-AI-Chat",
        "provider": provider,
        "api_configured": api_configured,
        "mcp_configured": bool(
            get_mcp_url()
        ),
        "model": model,
        "assistant_name": get_assistant_name(),
        "user_name": get_user_name(),
        "conversation_configured": conversation_configured,
        "openai_conversation_id": bool(
            load_conversation_id()
        ),
        "anthropic_messages": len(
            load_anthropic_messages(response_id = getattr(
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
