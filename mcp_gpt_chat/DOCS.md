# MCP-AI-Chat — Documentation

## Installation

Install **MCP-AI-Chat** through a Home Assistant app repository or build it locally for development.

After installation, open the app configuration and set the options required for the selected AI provider:

1. AI provider
2. API key for the selected provider
3. AI model
4. Home Assistant MCP URL
5. Assistant name
6. User name
7. Instruction prompt

Save the configuration and restart the app.

## AI Providers

The app supports:

- OpenAI
- Anthropic / Claude

The provider can be selected directly in the Home Assistant app configuration.

Each provider has its own API key and model configuration.

## OpenAI Conversation State

OpenAI uses the Responses API together with the OpenAI Conversations API.

The app does not store the complete OpenAI conversation locally. Instead, it stores only the OpenAI `conversation_id` in:

```text
/data/conversation.json
```

The actual conversation state is managed by OpenAI.

This allows the conversation to persist across app requests and restarts without maintaining a separate local message database.

## Anthropic / Claude Conversation State

Claude uses the Anthropic Messages API.

Because the Messages API does not use the same OpenAI-style persistent `conversation_id`, the app stores the Claude message history locally in:

```text
/data/conversation.json
```

The OpenAI and Claude conversation states are stored separately.

Switching the provider therefore does not overwrite the conversation state of the other provider.

## Assistant Identity

`assistant_name` controls the assistant name displayed in the user interface and supplied to the model.

`user_name` controls the user's name supplied to the model.

`instructions` is the base instruction prompt sent with chat requests. It can be customized completely.

The instruction prompt can define language, tone, behavior, Home Assistant rules and other requirements for the assistant.

## Home Assistant MCP

The configured MCP endpoint must be reachable by the application and must expose the Home Assistant functionality the assistant is allowed to use.

The permissions available to the assistant depend on the MCP server configuration.

Only expose the Home Assistant functionality that is actually required.

For actions such as controlling devices, make sure the MCP permissions are configured appropriately.

## Voice Input

Voice input uses the browser's Web Speech API when supported.

Voice-originated requests can be answered using browser text-to-speech.

Support depends on the browser or WebView being used. Some embedded Android WebViews may not expose all speech APIs.

If voice input does not work, test the application in a current browser such as Chrome.

## Configuration

The main configuration options are:

| Option | Description |
|---|---|
| `provider` | Selected AI provider |
| `openai_api_key` | OpenAI API key |
| `openai_model` | OpenAI model |
| `anthropic_api_key` | Anthropic API key |
| `anthropic_model` | Anthropic / Claude model |
| `ha_mcp_url` | Home Assistant MCP endpoint |
| `assistant_name` | Assistant display name |
| `user_name` | User name |
| `instructions` | Base instruction prompt |

All options defined under `options:` in `config.yaml` should also have a corresponding entry under `schema:`.

## Troubleshooting

### Configuration resets or options are missing

Check `config.yaml`.

Every option defined under:

```yaml
options:
```

should have a matching entry under:

```yaml
schema:
```

Also verify that the YAML syntax is valid.

### MCP connection problems

Verify:

- The `ha_mcp_url` is correct.
- The MCP endpoint is reachable from the Home Assistant environment.
- The MCP endpoint is valid and available.
- The MCP server exposes the required Home Assistant functionality.
- The MCP server permissions allow the requested operation.

For Anthropic / Claude, the MCP endpoint must also be reachable by Anthropic's MCP connector.

### OpenAI errors

Verify:

- The OpenAI API key is valid.
- The selected model is available to the configured OpenAI account.
- The Home Assistant host has internet access.
- The OpenAI API is reachable.
- The configured model name is correct.

### Anthropic / Claude errors

Verify:

- The Anthropic API key is valid.
- The selected Claude model is available to the configured Anthropic account.
- The Home Assistant host has internet access.
- The Anthropic API is reachable.
- The configured model name is correct.
- The MCP endpoint is reachable by Anthropic's MCP connector when MCP functionality is used.

### Conversation problems

For OpenAI, check that `/data/conversation.json` contains a valid `conversation_id`.

For Claude, check that the local conversation data is present in `/data/conversation.json`.

Do not publish the contents of this file because it may contain private conversation data.

If necessary, the conversation state can be reset by removing the stored conversation data and restarting the app. This starts a new conversation state for the affected provider.

## Health Endpoint

The application provides a health endpoint:

```text
/health
```

It reports basic application status such as:

- Selected provider
- API configuration status
- MCP configuration status
- Selected model
- Assistant and user names
- Conversation state information

The endpoint should not be treated as a replacement for checking the actual Home Assistant or provider logs.

## Security

Never include real credentials in:

- GitHub issues
- Screenshots
- Source code
- Git commits
- Public documentation
- Public logs

Do not publish:

- OpenAI API keys
- Anthropic API keys
- Access tokens
- MCP URLs containing secrets
- Conversation IDs
- `/data/conversation.json`
- Home Assistant configuration files
- Backups containing credentials

If an API key or token is accidentally exposed, revoke it and create a new one.

Because the application can use Home Assistant MCP to perform actions, carefully review the permissions provided by the MCP server.

## Updates

The app slug should remain unchanged when publishing updates:

```text
mcp-gpt-chat
```

The displayed application name can be changed independently.

When releasing a new version, increase the `version` value in `config.yaml`.

Home Assistant can then detect the new version when the repository metadata and app version have been updated correctly.

## Development

The application consists of a Flask web application served through Gunicorn.

The main components are:

```text
config.yaml
Dockerfile
run.sh
app.py
requirements.txt
www/
```

The web interface is located in:

```text
www/gpt-chat.html
```

Application data is stored under:

```text
/data/
```

The Docker image supports:

- `amd64`
- `aarch64`

## Privacy and Costs

When OpenAI is selected, requests are sent to the configured OpenAI API.

When Anthropic / Claude is selected, requests are sent to the configured Anthropic API.

API usage may incur costs according to the respective provider's current pricing and account settings.

OpenAI conversation state is managed by OpenAI.

Claude conversation history is stored locally by the application.

The application does not require a separate third-party database.

