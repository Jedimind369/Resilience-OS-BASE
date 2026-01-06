# ResilienceOS — Install (Public Base)

## What you need
- Python 3 (ships with macOS)
- A browser

## Install
1) Clone this repo:
   - `git clone <REPO_URL>`
2) Copy configs from templates:
   - `cp OS/00_CORE_DATA/*.example.json OS/00_CORE_DATA/` (and rename each to drop `.example`)
3) Start:
   - `./OMEGA_ONE_CLICK.command`

## Add your own private context (local only)
Create a local folder like `OS/00_PRIVATE/` and store any identity / financial exports there.
This folder must stay out of Git (already ignored).
