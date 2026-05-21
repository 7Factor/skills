# 7f-slide-generator

Overlay skill that applies the 7Factor brand system on top of Nico Bailon's [`visual-explainer`](https://github.com/nicobailon/visual-explainer) slide-deck workflow. See `SKILL.md` for agent-facing instructions.

## Bundled assets

The PNG logos under `assets/logo/` and the hand-curated content in `references/*.md` were captured from 7Factor's SharePoint marketing library on the date recorded in `assets/MANIFEST.json` (`synced_at`).

`assets/MANIFEST.json` records, for each bundled file: where it came from in SharePoint, its SHA-256 hash, and when it was synced. The skill never reads SharePoint at runtime — the manifest is purely a provenance record.

## Refreshing the assets

There is no automated check against SharePoint (the rclone/Graph paths require an Entra app registration we've chosen not to pursue). Refresh by hand when the brand changes:

1. **Find the source files in SharePoint.** Sign in at https://7factor.sharepoint.com/sites/marketing/ and navigate to **Documents → Branding**. The two folders we care about are:
   - **Logo** (specifically the **PNG** subfolder) — direct share link in `MANIFEST.json` under `sharepoint.folders.logos.share_url`.
   - **Brand Guidelines** — direct share link under `sharepoint.folders.brand_guidelines.share_url`.
2. **Download what you need.** Easiest path: from the Marketing **Documents** root, click the three-dot menu next to **Branding** and choose **Download** — it gives you a zip of the whole Branding directory. Or open each folder and download just the files that look new.
3. **Save the download somewhere outside this repo** (e.g. `~/Downloads/7f-branding-YYYYMMDD/`). Do not unzip into this repo directly.
4. **Ask Claude (or whichever agent) to update the skill.** Open this repo in your agent and say something like:

   > Refresh the 7f-slide-generator brand assets from `~/Downloads/7f-branding-20260712/`. Compare against the manifest, replace any changed PNG logos in `assets/logo/`, propose targeted edits to `references/7factor-brand.md` and `references/7factor-slide-patterns.md` if the brand guide changed, and update `assets/MANIFEST.json` (per-file SHA-256, size, and the top-level `synced_at` / `synced_by` fields).

   The agent has everything it needs: `MANIFEST.json` lists every tracked file and its expected SharePoint path, so it can map your downloaded files onto the right spots and tell you what changed before applying anything.

5. **Review the proposed changes**, accept the ones you want, then commit.

## Maintainer

Scott Pfister — scott.pfister@7factor.io
