# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-03-19

### Added

- `forward_message` tool — forward messages between chats
- `send_audio` tool — send audio files with built-in player (MP3, M4A)
- `send_voice` tool — send voice messages as waveform bubbles (OGG/OPUS)
- `send_poll` tool — send polls and quizzes with anonymous/multi-answer support
- `get_chat_info` tool — get chat details (member count, description, admin list)
- Rate limiting middleware — proactive throttling (30 msg/sec global, 20 msg/min per chat)
- Custom HTTP connection pool — `HTTPXRequest` with 100 connections and 60s timeouts
- Unit tests via pytest for `_ok`, `_err`, `_validate_file`, `_check_file_size`, `_RateLimiter`
- GitHub Actions CI — lint (ruff) + import check + pytest on push/PR
- CHANGELOG.md

### Changed

- Renamed `add_member` to `create_invite_link` for accuracy
- Moved `create_group` / `create_channel` to Known Limitations in README

### Fixed

- Replaced deprecated `reply_to_message_id` with `ReplyParameters` (python-telegram-bot v21+)
- Removed bot token from log output (security)
- Added token-exposure warning to `get_file_link` response
- Fixed space-in-path issue in `mcp_config.json`

### Security

- Bot token no longer logged to stderr
- `get_file_link` response includes warning about token in URL

## [1.0.0] — 2026-03-18

### Added

- Initial release with 16 tools
- Messaging: `send_message`, `reply_to_message`, `edit_message`, `delete_message`
- Files & Media: `send_document`, `send_photo`, `send_video`, `download_file`, `get_file_link`
- Management: `create_group`, `create_channel`, `add_member`, `kick_member`, `pin_message`
- Information: `get_me`, `get_updates`, `get_chat_id`
- HTML `parse_mode` by default
- File size validation (50 MB warn, 2 GB block)
- 30-second HTTP timeout
- Structured stderr logging
- Graceful error handling for rate limits, timeouts, permissions

[1.1.0]: https://github.com/proshangite-x/telegram-mcp-server/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/proshangite-x/telegram-mcp-server/releases/tag/v1.0.0
