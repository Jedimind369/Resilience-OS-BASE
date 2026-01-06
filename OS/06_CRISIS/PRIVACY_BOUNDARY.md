# Privacy Boundary (GDPR)

This repo is intended to be published publicly.

Never commit:
- Personal identity (names, addresses, IDs, phone, email)
- Bank/PayPal exports and transaction logs
- Private documents (`Sources/`, `Psychotherapie/`, `SYSTEM_CONTEXT/`, reports)
- AI model files (`*.gguf`, `*.safetensors`, `*.bin`, `*.pt`, …)
- Kiwix / Wikipedia `.zim` knowledge vaults

Use `python3 OS/01_SCRIPTS/verify_public_export.py .` as a preflight check.
Optional: add your own patterns:
- `python3 OS/01_SCRIPTS/verify_public_export.py . --extra-patterns OS/00_PRIVATE/verify_patterns.txt`
