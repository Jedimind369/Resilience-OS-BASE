# Publish to GitHub (safe workflow)

Recommended: publish this base as its **own repo** (clean history).

If you must publish into an existing repo, publish into a **new branch** (do not overwrite `main` blindly):

1) Verify:
   - `python3 OS/01_SCRIPTS/verify_public_export.py .`
2) Create and push branch:
   - `git checkout -b public-base`
   - `git add .`
   - `git commit -m "ResilienceOS Base (public)"`
   - `git push -u origin public-base`

Then set the default branch on GitHub to `public-base` (optional).
