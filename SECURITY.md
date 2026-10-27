# Security / 安全说明

Current public version: 2.24.0 Custom Workflows Preview / PARTIAL. Maintainer: drunk13232. No long-term support or comprehensive security certification is promised.

## Private vulnerability reporting

GitHub private vulnerability reporting is enabled for `drunk13232/novel-studio` (verified 2026-10-27). Submit a private report through:

https://github.com/drunk13232/novel-studio/security/advisories/new

安全问题请通过 GitHub 的私密漏洞报告入口反馈。请勿在公开 Issue 中粘贴漏洞利用细节、私人小说、密钥或未脱敏日志。如果私密入口暂不可用，请先保留敏感细节，勿转为公开披露。没有另设或虚构私人邮箱及响应时限。

Include the affected version, impact and a minimal fictional reproduction. Never attach full API keys, auth.json, config.toml, private manuscripts, databases or backups. Credential holders should revoke/rotate exposed credentials; removing a current file does not erase Git history.

## Existing boundaries

System credential storage or session-only secrets; no plaintext key retrieval through normal APIs. Backups exclude keys. The backend binds to loopback and checks local session/origin constraints. Codex MCP and character interfaces reuse controlled Actions, project isolation, immutable proposals, approval and receipts. Ordinary text APIs receive no arbitrary Shell/SQL/filesystem privileges. Final, Canon, State and Knowledge remain protected. Model scope and cost remain under author control.

Third-party services, optional plugins/models and private assets require their own review. A checksum, dependency scan or antivirus note is not a safety guarantee. Current build/acceptance limits are recorded in docs/oss/INSTALL-VERIFICATION.md. No real credential leak is alleged without evidence.
