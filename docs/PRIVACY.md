# Privacy / GDPR Boundary

This repository is intended to be safe to publish publicly.

## Never commit
- Personal identity (names, addresses, phone numbers, IDs)
- Bank / PayPal exports, transaction logs
- Private documents (`Sources/`, `Psychotherapie/`, `SYSTEM_CONTEXT/`, reports)
- AI model files (`*.gguf`, `*.safetensors`, `*.bin`, `*.pt`, …)
- Kiwix / Wikipedia `.zim` files

## Preflight (required)
Run before any push:
```bash
python3 OS/01_SCRIPTS/verify_public_export.py .
```

## Optional: your own extra checks (local only)
Create `OS/00_PRIVATE/verify_patterns.txt` with one regex per line, then:
```bash
python3 OS/01_SCRIPTS/verify_public_export.py . --extra-patterns OS/00_PRIVATE/verify_patterns.txt
```
