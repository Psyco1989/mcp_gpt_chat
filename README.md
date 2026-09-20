# MCP-AI-Chat

A Home Assistant app that provides a web-based AI chat interface with Home Assistant MCP integration.

The app supports multiple AI providers and allows you to switch between them directly in the Home Assistant app configuration.

## Oberfläche

![MCP-AI-Chat Oberfläche](https://raw.githubusercontent.com/Psyco1989/mcp_gpt_chat/refs/heads/main/Screenshot.png)

## Features

- OpenAI Responses API
- Persistent OpenAI Conversation state using OpenAI `conversation_id`
- Anthropic / Claude support
- Persistent Claude conversation history
- Home Assistant MCP integration
- Provider selection via Home Assistant configuration dropdown
- Configurable AI model
- Configurable assistant name
- Configurable user name
- Configurable instruction prompt
- Optional speech input
- Browser text-to-speech for voice-originated requests
- Home Assistant Ingress support
- AMD64 and ARM64 support
- Health endpoint for basic application status
- Separate conversation state for OpenAI and Claude

## Supported AI Providers

### OpenAI

The app uses the OpenAI Responses API together with the OpenAI Conversations API.

The OpenAI conversation is stored server-side by OpenAI. The app only stores the `conversation_id` in `/data/conversation.json`.

This means the complete OpenAI conversation does not have to be stored locally by the app.

### Anthropic / Claude

Claude uses the Anthropic Messages API together with Anthropic's MCP Connector.

Because the Anthropic Messages API does not provide the same conversation-ID mechanism as OpenAI, the Claude conversation history is stored locally in `/data/conversation.json`.

The OpenAI and Claude conversation histories are kept completely separate.

## Requirements

- Home Assistant
- An OpenAI API account and API key if using OpenAI
- An Anthropic API account and API key if using Claude
- A reachable Home Assistant MCP server
- Internet access from the Home Assistant host for API requests

For Claude MCP integration, the configured MCP server must be reachable by Anthropic's MCP connector.

## Configuration

The app exposes the following options:

| Option | Description |
|---|---|
| `provider` | AI provider: OpenAI or Anthropic / Claude |
| `openai_api_key` | OpenAI API key |
| `openai_model` | OpenAI model name |
| `anthropic_api_key` | Anthropic API key |
| `anthropic_model` | Anthropic / Claude model name |
| `ha_mcp_url` | Home Assistant MCP server URL |
| `assistant_name` | Name shown for the assistant |
| `user_name` | User name used by the assistant |
| `instructions` | Custom instruction prompt |

The provider can be selected from the Home Assistant configuration UI.

## Conversation State

Conversation state is handled differently depending on the selected provider.

### OpenAI

OpenAI uses a persistent Conversation ID:

```text
OpenAI
    ↓
Responses API
    ↓
Conversation ID
    ↓
Home Assistant MCP
```

The Conversation ID is stored in:

```text
/data/conversation.json
```

The actual conversation remains managed by OpenAI.

### Claude

Claude uses a locally stored message history:

```text
Claude
    ↓
Messages API
    ↓
Local History
    ↓
Home Assistant MCP
```

The Claude history is stored separately from the OpenAI Conversation ID.

Example:

```json
{
  "openai": {
    "conversation_id": "conv_..."
  },
  "anthropic": {
    "messages": []
  }
}
```

Switching between OpenAI and Claude therefore does not delete or overwrite the conversation of the other provider.

## Home Assistant MCP

The app can connect the selected AI provider to a Home Assistant MCP server.

The MCP server can provide access to Home Assistant entities, states and actions.

The permissions available through MCP depend on the configuration of the MCP server.

Only expose the Home Assistant functionality you want the AI assistant to be able to access.

## Security

API keys and MCP URLs are configured through the Home Assistant app configuration and must not be committed to source control.

Do not publish:

- API keys
- Access tokens
- MCP URLs containing secrets
- Conversation IDs
- `/data/conversation.json`
- Home Assistant configuration files
- Logs containing credentials or private information
- Backups containing credentials

If an API key or token is accidentally exposed, revoke it and create a new one.

Because the app can use Home Assistant MCP to perform actions, carefully review the permissions provided by the MCP server.

## Privacy and Costs

When OpenAI is selected, requests are sent to the configured OpenAI API.

When Anthropic / Claude is selected, requests are sent to the configured Anthropic API.

API usage may incur costs according to the respective provider's current pricing.

The app does not require a third-party database.

OpenAI conversation state is managed by OpenAI using the Conversation API.

Claude conversation history is stored locally under:

```text
/data/conversation.json
```

## Architecture

```text
                    MCP-AI-Chat
                         │
                 Provider Selection
                         │
              ┌──────────┴──────────┐
              │                     │
           OpenAI                Claude
              │                     │
       Responses API          Messages API
              │                     │
       Conversation ID        Local History
              │                     │
              └──────────┬──────────┘
                         │
                    MCP Connector
                         │
                  Home Assistant
```

## Installation

Add the GitHub repository as a custom Home Assistant app repository:

```text
https://github.com/Psyco1989/mcp_gpt_chat
```

Then install **MCP-AI-Chat** from the Home Assistant App Store.

After installation, configure:

1. AI provider
2. API key for the selected provider
3. AI model
4. Home Assistant MCP URL
5. Assistant name
6. User name
7. Instructions

Start the app and open it through Home Assistant.

## License

MIT. See [LICENSE](LICENSE).
