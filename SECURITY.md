# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| older   | :x:                 |

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Use GitHub's **private vulnerability reporting** on this repository instead:
`Settings → Security → Vulnerability alerting → Report a vulnerability`
(or open the "Security" tab and click "Report a vulnerability").

Include:
- A description of the vulnerability and its impact
- Steps to reproduce (or a minimal proof of concept)
- Affected versions and, if possible, a suggested fix

We will acknowledge reports within **3 business days** and aim to ship a
fix/release within **7 days** for critical issues.

## Security Notes for Users

- **API keys** (e.g. `GLM_API_KEY`) are read from environment variables only —
  never commit them. The `.env`-style configuration is git-ignored.
- The GLM proxy listens on `127.0.0.1` only (local loopback), never on a
  publicly reachable address.
- Token-usage logs record task name + token counts + timestamps only, never
  document content.
