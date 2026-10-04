# MCP-AI-Chat 2.0.2 – Dokumentation

## Architektur

```text
Browser
   ↓
Flask /api/chat
   ↓
Provider-Auswahl
   ├── OpenAI Responses API
   ├── Anthropic Messages API
   └── Kilo Gateway Chat Completions
   ↓
gemeinsamer MCP-Client
   ↓
Home Assistant MCP /api/mcp
```

Der Verlauf wird serverseitig unter `/data/conversation.json` verwaltet. OpenAI verwendet zusätzlich eine OpenAI Conversation-ID. Claude und Kilo verwenden den lokalen Verlauf.

## API-Endpunkte

### `GET /api/config`

Liefert nur die für die Oberfläche benötigte Konfiguration:

- Provider
- Providername
- Modell
- Assistentenname
- Benutzername
- MCP-Status
- Websuche-Status
- Begrüßungsmodus
- Verlaufslimit

Es werden keine Secrets ausgeliefert.

### `GET /api/history`

Liefert den lokalen Verlauf des aktuell konfigurierten Providers.

### `POST /api/chat`

Neue Anfrage. Aktuelles Format:

```json
{
  "message": "Schalte das Wohnzimmerlicht ein."
}
```

Das alte Frontend-Format mit `messages` wird als Rückwärtskompatibilität ebenfalls akzeptiert, intern wird aber nur die letzte Benutzernachricht verwendet.

### `POST /api/reset`

Löscht den Verlauf des aktuell ausgewählten Providers. Bei OpenAI wird zusätzlich die lokale Conversation-ID entfernt.

### `GET /api/greeting`

Erzeugt abhängig von `greeting_mode` eine lokale oder KI-generierte Begrüßung.

### `GET /health`

Basisinformationen zum Laufzeitstatus.

## MCP-Protokoll

Der integrierte MCP-Client verwendet Streamable HTTP und den Legacy-/Session-Pfad des aktuellen MCP-Protokolls. Er führt aus:

```text
initialize
notifications/initialized
tools/list
tools/call
```

Der Home-Assistant-MCP-Endpunkt ist `/api/mcp`; Home Assistant verlangt eine Authentifizierung. ([Home Assistant MCP Server](https://www.home-assistant.io/integrations/mcp_server/); [HA LLM API](https://developers.home-assistant.io/docs/core/llm/))

## OpenAI Tool Loop

OpenAI Responses kann Function Tools zurückgeben. Das Add-on:

1. sendet die User-Nachricht
2. liest `function_call`-Items
3. führt die jeweiligen MCP-Tools aus
4. sendet `function_call_output` zurück
5. wiederholt dies bis zur Textantwort oder bis zum internen Schleifenlimit

OpenAI dokumentiert Responses + Conversations sowie das explizite Management von Tool-Schleifen. ([OpenAI Responses API](https://platform.openai.com/docs/guides/migrate-to-responses))

## Claude Tool Loop

Claude kann `tool_use`-Blöcke liefern. Das Add-on:

1. sendet Verlauf + aktuelle User-Nachricht
2. liest `tool_use`
3. ruft MCP auf
4. hängt `tool_result` an den Request an
5. wiederholt bis zur finalen Textantwort oder zum Schleifenlimit

## Kilo Tool Loop

Kilo verwendet die OpenAI-kompatible Chat-Completions-Schnittstelle. Das Add-on wandelt MCP-Tools in normale Function Tools um und verarbeitet anschließend `tool_calls` und `tool`-Ergebnisnachrichten.

Kilo dokumentiert Chat Completions und Tool Calling direkt für sein Gateway. ([Kilo API Reference](https://kilo.ai/docs/gateway/api-reference); [Kilo SDKs](https://kilo.ai/docs/gateway/sdks-and-frameworks))

## Dateiablage

```text
/data/options.json
/data/conversation.json
```

Die Conversation-Datei wird über eine temporäre Datei und anschließendes `replace()` atomar geschrieben.

## Gesprächslimit

```text
HISTORY_LIMIT = 100
```

Es werden nur `user`- und `assistant`-Nachrichten dauerhaft gespeichert. Tool-Aufrufe bleiben Teil des laufenden Provider-Requests beziehungsweise der OpenAI-Conversation, aber nicht Teil des einfachen lokalen UI-Verlaufs.

## Sicherheit

Secrets werden weder durch `/api/config` noch durch `/health` ausgegeben.

MCP-URLs werden in Logs nur ohne Query-Parameter protokolliert.

Der Benutzer sollte keine echten Credentials in Git committen.

## Sprachsteuerung

Die HTML-Oberfläche verwendet:

```text
SpeechRecognition / webkitSpeechRecognition
speechSynthesis
```

Die erkannte Sprache ist `de-DE`. Nach ungefähr zwei Sekunden unverändertem Transkript wird die Anfrage automatisch abgesendet.

## Deployment

Start über Gunicorn:

```bash
./run.sh
```

Der App-Port ist:

```text
8099
```

Der Container wird für `amd64` und `aarch64` gebaut.
