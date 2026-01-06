# Deep Research Prompt — ResilienceOS (S‑Tier)

Copy this as the **single prompt** into Google / Deep Research / Perplexity / NotebookLM.

## Evidence Rules (mandatory)
For every claim, include **at least one** of:
- Official docs (preferred)
- Official GitHub repo + release notes
- App store listing + privacy policy
- Independent benchmark / reproducible test steps

Reject recommendations if any of these are true:
- Requires cloud to function (no offline fallback)
- Unknown / incompatible license for redistribution
- Telemetry/analytics cannot be disabled (or unclear)
- No reproducible install path (no clear steps, no checksums/signatures)
- Not actively maintained (no updates in ~12 months) without a strong reason

## Glossary (short)
- **Public Base:** Open-source repo with code+templates only. No personal data.
- **Private Ops:** Local machine data (identity, exports, logs, reports). Never pushed.
- **Core Mode:** Must work offline with low power + minimal UI friction.
- **Admin Mode:** Advanced tools (terminal) for setup/maintenance.
- **Drill:** 15-minute validation exercise to prove a recommendation works.

---

# Research Auftrag: ResilienceOS — Offline‑First, GDPR‑safe, Industrial/Military‑grade

You are the research lead for an offline-first “ResilienceOS”. The system must be usable under stress with small context windows and no internet.

## 1) Source of Truth (current state)
We operate with two layers:

### A) Public Base (GDPR-safe, open source)
- Repo: `https://github.com/Jedimind369/Resilience-OS-BASE`
- Must contain: dashboard, watchdog, backups, example configs, docs, privacy preflight.

### B) Private Ops (local only)
- Identity + financial exports + private documents live locally and must remain out of Git.

## 2) Threat Model (evaluate everything against these)
- 72h power outage (winter, city)
- Evacuation (30 min notice)
- Internet + cellular down
- Medical emergency offline
- 3–7 day isolation

## 3) KPIs (quantified)
For each recommendation: provide numbers or explicit measurement steps.
- Boot to “critical info visible”: <3 seconds
- RAM (Core Mode): <100 MB
- Storage (Core): <50 MB (excluding maps/ZIM/models)
- Battery drain (Phone Mode): <5%/hour active use
- Offline: 0 outbound calls in Core Mode (verify method)
- Usability under stress: ≤5 actions from start → SitRep entry

## 4) Research Questions (prioritized)

### P0 — Survival-critical
1) Best offline medical knowledge stack (ZIMs + curated refs):
   - Compare WikiMed / “Where There Is No Doctor” / other offline med bundles.
   - Include licensing + update cadence + footprint.
2) Comms without internet/cellular:
   - Briar / Meshtastic / LoRa / SDR receive-only options.
   - Legal constraints in Germany (license requirements).
3) Offline maps & routing:
   - OsmAnd vs Organic Maps vs alternatives.
   - Storage size for Germany + navigation quality + battery usage.

### P1 — System effectiveness
4) Is “terminal-first” optimal?
   - Evaluate terminal-first vs touch-first vs paper-hybrid vs audio-first.
   - Recommend a dual-mode approach if needed: “Touch Core / Terminal Admin”.
5) Offline sync between devices:
   - Syncthing/rsync/git-bundle/sneakernet.
   - Provide a minimal “field kit” approach.

### P2 — Quality-of-life and drills
6) Training/gamification/drills:
   - What works to keep routines alive without cloud?

## 5) Search Playbook (query pack)
Use these query styles:
- `site:github.com <tool> offline` + `license` + `telemetry`
- `site:docs.* <tool> privacy policy telemetry disable`
- `"offline" "no internet" <tool> battery drain`
- `<tool> "reproducible build"` / `<tool> signatures checksum`

Starter queries:
- `offline maps routing android ios osmand organic maps comparison battery`
- `briar messenger offline bluetooth wifi direct threat model`
- `meshtastic germany legal lora license`
- `rtl-sdr emergency broadcast receive offline`
- `kiwix wikimed zim size update cadence license`
- `on-device ocr offline open source ios android`
- `playwright vs selenium reliability offline automation`
- `syncthing local only no relay config`

## 6) Comparison protocol (for every candidate)
Fill this table (one per candidate):
- Name + license + last update
- Offline capability (what exactly works offline)
- Footprint: RAM / storage / CPU (measured or cited)
- Battery impact (measured or cited)
- Install steps (copy/paste)
- Privacy: telemetry? logs? can disable?
- Maintenance burden (how often to update)
- Fit to scenarios (which scenario it improves)

## 7) Output (strict)
Deliver:
1) Executive summary (≤1 page): Top 3 gaps + Top 3 quick wins (<2h)
2) Scenario coverage table (% coverage, critical gap, fix)
3) Keep/Replace/Add table for each subsystem (UI, maps, comms, knowledge, LLM, backup/sync)
4) Build vs buy with clear rationale
5) Implementation plan:
   - Phase 1 (today, 2h)
   - Phase 2 (week, 8h)
   - Phase 3 (month, 20h)
6) Drill protocol (15 min) to validate the #1 recommendation
7) Sources list: verified links only

## 8) Integration deliverables (required)
For each top recommendation, output:
- A GitHub Issue title
- A short acceptance criteria list (“Done when …”)
- Which files/docs/scripts must change in the Public Base repo
- A smoke test / drill to prove it works offline

## 9) Constraints / anti-goals
- No illegal instructions; obey local laws
- No weapon/attack guidance
- Avoid vendor lock-in; prefer open source
- No “pretty UI” that reduces robustness
- No personal data in the public repo

