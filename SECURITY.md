# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.1.x | Yes |
| < 1.1 | No |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do not open a public issue.** Instead, email the maintainer directly or use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) feature on this repository.

Please include:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

You should receive a response within 48 hours. We will work with you to understand the issue and coordinate a fix before any public disclosure.

## Known Security Considerations

- **Bot token handling** — The bot token is read from environment variables and is never logged. However, `get_file_link` returns a URL that contains the token (this is standard Telegram Bot API behavior). The tool response includes a warning about this.
- **File path validation** — `send_document`, `send_photo`, `send_video`, `send_audio`, and `send_voice` validate that the provided file path exists and check file sizes before uploading.
