[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://github.com/proshangite-x/telegram-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/proshangite-x/telegram-mcp-server/actions/workflows/ci.yml)

# Telegram MCP Server

A high-performance [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that exposes the Telegram Bot API as tools for LLM agents. Works with Cursor, Claude Desktop, Windsurf, and any MCP-compatible client.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Tool Reference](#tool-reference)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Category | Tools |
|---|---|
| Messaging | `send_message`, `reply_to_message`, `edit_message`, `delete_message`, `forward_message` |
| Files & Media | `send_document`, `send_photo`, `send_video`, `send_audio`, `send_voice`, `download_file`, `get_file_link` |
| Interactive | `send_poll` |
| Management | `create_invite_link`, `kick_member`, `pin_message` |
| Information | `get_me`, `get_updates`, `get_chat_id`, `get_chat_info` |

Built-in safeguards:

- HTML `parse_mode` by default for rich text formatting
- File size validation (warns >50 MB, blocks >2 GB)
- 30-second timeout on HTTP calls to prevent IDE hangs
- Proactive rate limiting (30 msg/sec global, 20 msg/min per chat)
- Custom connection pool (100 connections, 60s timeouts)
- Structured logging to stderr for debugging
- Graceful error handling for rate limits, timeouts, and permission errors

---

## Quick Start

### 1. Install dependencies

```bash
cd telegram-mcp-server
pip install -e .
```

Or install directly:

```bash
pip install "mcp[cli]" python-telegram-bot python-dotenv aiohttp
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your values (see [Configuration](#configuration) below).

### 3. Connect to your MCP client

Add to your MCP settings (`.cursor/mcp.json` or Claude Desktop config):

```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/telegram-mcp-server",
      "env": {
        "TELEGRAM_BOT_TOKEN": "your_token_here",
        "DEFAULT_CHAT_ID": "your_chat_id_here"
      }
    }
  }
}
```

### 4. Test it

Ask your AI assistant:

> "Send a test message to Telegram saying Hello from MCP!"

---

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from [@BotFather](https://t.me/BotFather) |
| `DEFAULT_CHAT_ID` | No | — | Fallback chat ID when `chat_id` is omitted |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

> [!TIP]
> Send a message to [@userinfobot](https://t.me/userinfobot) on Telegram to find your chat ID.

---

## Tool Reference

### Messaging

| Tool | Description |
|---|---|
| `send_message(text, chat_id?, parse_mode?)` | Send a message (HTML formatting by default) |
| `reply_to_message(text, message_id, chat_id?, parse_mode?)` | Reply to a specific message |
| `edit_message(text, message_id, chat_id?, parse_mode?)` | Edit a bot message |
| `delete_message(message_id, chat_id?)` | Delete a message |
| `forward_message(from_chat_id, message_id, chat_id?)` | Forward a message between chats |

### Files & Media

| Tool | Description |
|---|---|
| `send_document(file_path, chat_id?, caption?, parse_mode?)` | Send any file (validates path & size) |
| `send_photo(photo_path, chat_id?, caption?, parse_mode?)` | Send an image |
| `send_video(video_path, chat_id?, caption?, parse_mode?)` | Send a video |
| `send_audio(audio_path, chat_id?, caption?, parse_mode?)` | Send an audio file with built-in player |
| `send_voice(voice_path, chat_id?, caption?, parse_mode?)` | Send a voice message (OGG/OPUS) |
| `download_file(file_id, destination_path)` | Download a Telegram file to local disk |
| `get_file_link(file_id)` | Get a temporary download URL |

### Interactive

| Tool | Description |
|---|---|
| `send_poll(question, options, chat_id?, is_anonymous?, poll_type?, ...)` | Send a poll or quiz with anonymous voting and multiple answers |

### Management

| Tool | Description |
|---|---|
| `create_invite_link(user_id, chat_id?)` | Create a one-time invite link |
| `kick_member(user_id, chat_id?)` | Ban a user from a group or channel |
| `pin_message(message_id, chat_id?, disable_notification?)` | Pin a message in a chat |

### Information

| Tool | Description |
|---|---|
| `get_me()` | Get bot info (username, ID, capabilities) |
| `get_updates(limit?, offset?)` | Fetch recent incoming messages |
| `get_chat_id(query)` | Search for a chat ID by name |
| `get_chat_info(chat_id?)` | Get chat details: member count, description, invite link, admin list |

> [!NOTE]
> All `chat_id` parameters are optional if `DEFAULT_CHAT_ID` is set in your environment.

---

## Known Limitations

> [!WARNING]
> **`create_group` / `create_channel`** — The standard Bot API does not support group or channel creation. These tools exist in the code for forward-compatibility but will always return an error. Use a userbot library (Telethon or Pyrogram) for this functionality.

> [!WARNING]
> **`get_updates` + Webhook conflict** — If your bot has a webhook set, `get_updates` will fail with a conflict error. Delete the webhook first by calling `https://api.telegram.org/bot<TOKEN>/deleteWebhook`.

> [!NOTE]
> **File uploads > 50 MB** — The standard Bot API limits uploads to 50 MB. For larger files (up to 2 GB), run a [local Bot API server](https://core.telegram.org/bots/api#using-a-local-bot-api-server).

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `TELEGRAM_BOT_TOKEN is not set` | Add your token to `.env` or the MCP env config |
| Rate limited | Wait the specified seconds and retry |
| File exceeds 50 MB | Use a local Bot API server or compress the file |
| Tools not showing in Cursor | Restart Cursor after updating `mcp.json` |
| `get_updates` returns conflict error | Delete your webhook first (see Known Limitations) |

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

---

## License

[MIT](LICENSE)
