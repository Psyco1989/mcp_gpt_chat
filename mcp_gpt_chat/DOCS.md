# MCP GPT Chat — Documentation

## Installation

Install the app through a Home Assistant add-on/app repository or build it locally for development.

After installation, open the app configuration and set:

1. OpenAI API key
2. OpenAI model
3. Home Assistant MCP URL
4. Assistant name
5. User name
6. Instruction prompt

Save the configuration and restart the app.

## Assistant identity

`assistant_name` controls the name displayed in the UI and supplied to the model.

`user_name` controls the user's name supplied to the model.

`instructions` is the base instruction prompt sent with chat requests. It can be completely customized.

## Home Assistant MCP

The configured MCP endpoint must be reachable by the app container and must expose the Home Assistant functionality you want the assistant to use.

The assistant must not be given more permissions than necessary.

## Voice input

Voice input depends on browser/WebView support for the Web Speech API. Browser text-to-speech is used for answers originating from voice input.

Some embedded Android WebViews may not expose all speech APIs.

## Troubleshooting

### Configuration resets

Make sure all options defined under `options:` also have a matching entry under `schema:` in `config.yaml`.

### MCP connection problems

Verify that `ha_mcp_url` is reachable from the Home Assistant environment and that the MCP endpoint is valid.

### OpenAI errors

Verify the API key, selected model, account access, and network connectivity.

## Security

Never include real credentials in GitHub issues, screenshots, source code, or commits.
