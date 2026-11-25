# Prove It: reference

## Evidence by platform

| Platform | Capture | Notes |
|---|---|---|
| iOS simulator | `xcrun simctl io <udid> screenshot --mask=black <file>`; `xcrun simctl io <udid> recordVideo <file>` for flows | Run `xcrun simctl status_bar <udid> override --time 9:41 --batteryLevel 100` first. `--mask=black` keeps the rounded corners, so you can judge corner clearance. One shot per relevant device and pose. |
| Multi-display (foldable) simulators | Same, with `--display`: `--display=primary` when closed (outer screen), `--display=internal` when open | Without `--display`, a closed device captures the powered-off inner screen and comes out black. The CLI can't change pose; the person changes it in the simulator's controls. |
| iOS logs | `xcrun simctl spawn <udid> log show --last 5m --info --debug --predicate 'category == "javascript"'` | React Native `console.log` only appears with `--info --debug`. A temporary probe log is fine for measuring; remove it before commit. |
| Android emulator | `adb exec-out screencap -p > <file>`; `adb shell screenrecord /sdcard/<file>` | `adb logcat -s ReactNativeJS` for React Native logs. |
| Web | Playwright with `screenshot: 'on'`, `video: 'on'`, `trace: 'on'` for the proof run | `trace.zip` replays every action, request and DOM snapshot (`npx playwright show-trace`). Use `clip` to crop to the criterion. |
| API | `curl -s -o /dev/null -w '%{http_code}'` plus a trimmed body | Load secrets into env vars from your vault; never put them in the command or the report. |
| CI | Job URL plus the exact log line | The line that shows the result, not a summary of it. |

## Publishing

### To a Jira ticket

The Atlassian MCP connector can comment but not attach files, so uploads go through the REST API with an
API token.

1. **Token.** Keep it in Keychain (or your password manager) and read it straight into a variable, e.g.
   `T=$(security find-generic-password -s <keychain-service> -a <email> -w)`. Check it with `${#T}` (length
   only, never the value) and the status of `GET /rest/api/3/myself`. A length of 0 means a blank item was
   stored. To store one, copy the token and run, in Claude Code,
   `! security add-generic-password -U -a <email> -s <keychain-service> -w "$(pbpaste)" && pbcopy < /dev/null`.
   Don't use the interactive `-w` prompt: Claude Code's `!` shell can't take hidden input and saves an
   empty value.
2. **Upload** screenshots and videos as attachments:
   `curl -s -u "<email>:$T" -H "X-Atlassian-Token: no-check" -F "file=@<file>;type=image/png" https://<site>.atlassian.net/rest/api/3/issue/<KEY>/attachments`.
3. **Comment** with the report through `POST /rest/api/2/issue/<KEY>/comment` and a wiki-markup body
   (`{"body": "..."}`). `!<filename>|thumbnail!` shows an attachment inline in a table cell; `(/)` and `(?)`
   render as pass and unproven icons. API v3 needs ADF media IDs instead, which the upload doesn't return.
4. **Link** the comment (`.../browse/<KEY>?focusedCommentId=<id>`) from the PR's test plan.

### To a GitHub PR

GitHub has no API to upload images to a PR, so the screenshots live on an orphan branch, `pr-evidence`, in
the same repo, one folder per PR number, and the PR description embeds them. They never enter the PR's diff.

1. **Push them** from a dedicated worktree, never the feature branch:
   - First time in a repo (no `pr-evidence` on origin): `git worktree add --detach <repo>-worktrees/pr-evidence origin/main`,
     then in it `git switch --orphan pr-evidence` and add a short README.
   - Later: `git worktree add <repo>-worktrees/pr-evidence pr-evidence` (or reuse it), then `git pull --ff-only`.

   Copy the checked PNGs into `<PR#>/`, commit, and push with `git push -u origin pr-evidence:pr-evidence`.
2. **Embed them.** Add a `## Proof` section to the PR body: the criterion table with images pinned to the
   commit SHA, so a later push can't change them:
   `<img src="https://github.com/<owner>/<repo>/blob/<sha>/<PR#>/<file>.png?raw=true" alt="..." width="420">`
   (about 200 wide for a phone shot). Link the ticket comment above the table. Update the body with
   `gh api -X PATCH repos/<owner>/<repo>/pulls/<n> -F body=@<file>`; it needs only `repo` scope, where
   `gh pr edit` can fail on `read:org`.
3. **Check it landed** with `gh api "repos/<owner>/<repo>/contents/<PR#>?ref=<sha>"`. A `curl` of the
   github.com URL returns 404 for a private repo without a browser session, which proves nothing.

Only images that passed the frame check go on the branch: anyone with access to the repo can read it.
Videos, Playwright traces and anything over the ticket's attachment limit stay as CI artifacts, linked from
the ticket comment. Never commit evidence to the PR's own branch; it pollutes the diff.

## When the app can't reach the network

If sign-in fails with `Network Error`, or the logs show "A TLS error caused the secure connection to fail",
check `scutil --proxy` before blaming the app. Simulators use the Mac's system proxy and `curl` ignores it,
so a debugging proxy (Proxyman, Charles) breaks the app while `curl` looks fine. Quit the proxy, or install
its root certificate in the simulator. "Connection error occurred… retrying" alone is usually React DevTools
on port 8097 and can be ignored.
