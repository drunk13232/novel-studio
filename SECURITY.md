# Security / 安全说明

Current candidate: 2.24.0 Custom Workflows Preview / PARTIAL. Maintainer: drunk13232. No long-term support or comprehensive security certification is promised.

## Private vulnerability reporting

The selected security channel is GitHub private vulnerability reporting for the intended repository `drunk13232/novel-studio`:

https://github.com/drunk13232/novel-studio/security/advisories/new

This is currently a local review candidate. The repository/reporting channel has not been created, enabled or tested by this task. Before publication, the owner must enable private vulnerability reporting in repository settings and verify “Report a vulnerability” is available. If the private form is unavailable, do not post exploitable details or secrets in public Issues. No alternative email address or guaranteed response time is invented.

安全反馈采用 GitHub 私密漏洞报告。仓库正式建立并由所有者开启该功能后才可使用上面的地址；当前不声称渠道已启用。请勿把漏洞利用细节、私人小说、密钥或未脱敏日志贴在公开 Issue。

Include the affected version, impact and minimal fictional reproduction. Never attach full API keys, auth.json, config.toml, private manuscripts, databases or backups. Credential holders should revoke/rotate exposed credentials; removing a current file does not erase Git history.

## Existing boundaries

System credential storage or session-only secrets; no plaintext key retrieval through normal APIs. Backups exclude keys. The backend binds to loopback and checks local session/origin constraints. Codex MCP and character interfaces reuse controlled Actions, project isolation, immutable proposals, approval and receipts. Ordinary text APIs receive no arbitrary Shell/SQL/filesystem privileges. Final, Canon, State and Knowledge remain protected. Model scope and cost remain under author control.

Third-party services, optional plugins/models and private assets require their own review. A checksum, dependency scan or antivirus note is not a safety guarantee. Current build/acceptance limits are recorded in docs/oss/INSTALL-VERIFICATION.md. No real credential leak is alleged without evidence.
