# 🤖 Telegram MCP Server

A high-performance **Model Context Protocol (MCP)** server that exposes the Telegram Bot API as tools for LLM agents — works with **Cursor**, **Claude Desktop**, **Windsurf**, and any MCP-compatible client.

---

## ✨ Features

| Category | Tools |
|---|---|
| **Messaging** | `send_message` · `reply_to_message` · `edit_message` · `delete_message` |
| **Files & Media** | `send_document` · `send_photo` · `send_video` · `download_file` · `get_file_link` |
| **Management** | `create_group`* · `create_channel`* · `add_member` · `kick_member` · `pin_message` |
| **Information** | `get_me` · `get_updates` · `get_chat_id` |

> \* Group/channel creation is not supported by the standard Bot API — these tools exist for forward-compatibility and return helpful error messages.

**Built-in safeguards:**
- 🔒 HTML parse_mode by default for rich text formatting
- 📁 File size validation (warns >50 MB, blocks >2 GB)
- ⏱️ 30s timeout on HTTP calls to prevent IDE hangs
- 📝 Structured logging to stderr for debugging
- 🛡️ Graceful error handling for rate limits, timeouts, and permission errors

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
cd "Telegram-MCP Server"
pip install -e .
```

Or install directly:

```bash
pip install "mcp[cli]" python-telegram-bot python-dotenv aiohttp
```

### 2. Configure credentials

Copy the template and fill in your values:

```bash
cp .env.example .env
```

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...    # From @BotFather
DEFAULT_CHAT_ID=987654321                # Your chat ID (use @userinfobot)
LOG_LEVEL=INFO                           # DEBUG for verbose output
```

### 3. Connect to your MCP client

#### Cursor / Claude Desktop

Add to your MCP settings (`.cursor/mcp.json` or Claude config):

```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["c:/Telegram-MCP Server/server.py"],
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
> *"Send a test message to Telegram saying Hello from MCP!"*

---

## 📖 Tool Reference

### Messaging

| Tool | Description |
|---|---|
| `send_message(text, chat_id?, parse_mode?)` | Send a message. HTML formatting by default. |
| `reply_to_message(text, message_id, chat_id?, parse_mode?)` | Reply to a specific message. |
| `edit_message(text, message_id, chat_id?, parse_mode?)` | Edit a bot message. |
| `delete_message(message_id, chat_id?)` | Delete a message. |

### Files & Media

| Tool | Description |
|---|---|
| `send_document(file_path, chat_id?, caption?, parse_mode?)` | Send any file (validates path & size). |
| `send_photo(photo_path, chat_id?, caption?, parse_mode?)` | Send an image. |
| `send_video(video_path, chat_id?, caption?, parse_mode?)` | Send a video. |
| `download_file(file_id, destination_path)` | Download a Telegram file to PC. |
| `get_file_link(file_id)` | Get a temporary download URL. |

### Management

| Tool | Description |
|---|---|
| `add_member(user_id, chat_id?)` | Generate a one-time invite link. |
| `kick_member(user_id, chat_id?)` | Ban a user from a group/channel. |
| `pin_message(message_id, chat_id?, disable_notification?)` | Pin a message in a chat. |

### Information

| Tool | Description |
|---|---|
| `get_me()` | Get bot info (username, ID, capabilities). |
| `get_updates(limit?, offset?)` | Fetch recent incoming messages. |
| `get_chat_id(query)` | Search for a chat ID by name. |

> **Note:** All `chat_id` parameters are optional if `DEFAULT_CHAT_ID` is set in `.env`.

---

## 🔧 Troubleshooting

| Issue | Solution |
|---|---|
| "TELEGRAM_BOT_TOKEN is not set" | Add your token to `.env` or MCP env config |
| "Rate limited" | Wait the specified seconds and retry |
| "File exceeds 50 MB" | Use a local Bot API server or send via `send_document` |
| Tools not showing in Cursor | Restart Cursor after updating `mcp.json` |

---

## 📄 License

MIT
