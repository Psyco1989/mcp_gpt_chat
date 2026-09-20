# MCP GPT Chat

A Home Assistant app that provides a web-based GPT chat interface with Home Assistant MCP integration.

## Features

- OpenAI Responses API
- Persistent OpenAI Conversation state
- Home Assistant MCP integration
- Configurable assistant name
- Configurable user name
- Configurable instruction prompt
- Optional speech input
- Browser text-to-speech for voice-originated requests
- Home Assistant Ingress support
- AMD64 and ARM64 support

## Requirements

- Home Assistant
- A supported OpenAI API account and API key
- A reachable Home Assistant MCP server
- Internet access from the Home Assistant host for OpenAI API requests

## Configuration

The app exposes these options:

| Option | Description |
|---|---|
| `openai_api_key` | OpenAI API key |
| `openai_model` | OpenAI model name |
| `ha_mcp_url` | Home Assistant MCP server URL |
| `assistant_name` | Name shown for the assistant |
| `user_name` | User name used by the assistant |
| `instructions` | Custom instruction prompt |

## Security

The OpenAI API key and MCP URL are configured through the Home Assistant app configuration and must not be committed to source control.

This app can use Home Assistant MCP to perform actions in Home Assistant. Only grant the MCP server the permissions you intend the assistant to have.

Do not publish personal API keys, tokens, MCP URLs containing secrets, conversation IDs, backups, logs, or local configuration files.

## Privacy and costs

Requests are sent to the configured OpenAI API. OpenAI API usage may incur costs according to your OpenAI account and current pricing.

The app stores its persistent OpenAI Conversation ID under `/data` inside the app container.

## License

MIT. See [LICENSE](LICENSE).
