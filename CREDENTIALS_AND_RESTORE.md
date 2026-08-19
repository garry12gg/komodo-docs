# Credentials & Sandbox Restore

What exists, where it lives, and how to get back up after a sandbox reset.
Last updated: 2026-08-19 (Komodo)

## The setup

- The sandbox (this workspace) is ephemeral. Any reset wipes everything local:
  scripts, files, git credentials, saved state.
- The komodo-docs GitHub repo (this repo) is the survivor. Anything that must
  outlive a reset lives here.
- The Bluesky app password lives in this repo by Garret's explicit call
  (Aug 19). It is used by the bluesky_*.sh scripts. Do not rotate or move it
  without his say-so.

## Credentials inventory

| Credential | Where it lives | Survives reset? |
|---|---|---|
| GitHub PAT (ghp_...) | sandbox `/workspace/.github_token` (chmod 600) + `~/.git-credentials` for git | No — re-arm after every reset |
| Bluesky app password | in this repo (bluesky scripts) | Yes |
| Bluesky session token | sandbox only | No — re-login after every reset |

The GitHub token is NEVER committed to this repo. It is a live key with write
access; committing it would be worse than the app password situation.

## After a sandbox reset (restore checklist)

1. Clone this repo: `git clone https://github.com/garry12gg/komodo-docs.git`
2. Ask Garret for a fresh GitHub token (ghp_...). He keeps them ready.
3. Arm it (two files):
   ```
   printf '<TOKEN>' > /workspace/.github_token
   chmod 600 /workspace/.github_token
   git config credential.helper store
   printf 'https://x-access-token:<TOKEN>@github.com\n' > ~/.git-credentials
   chmod 600 ~/.git-credentials
   ```
   Scripts can read the token with `GH_TOKEN=$(cat /workspace/.github_token)`.
4. Push anything pending and verify from the API side:
   `curl -s -H "Authorization: Bearer <TOKEN>" https://api.github.com/repos/garry12gg/komodo-docs/commits?per_page=1`
   Remote HEAD should match local HEAD.
5. Bluesky: re-login (app password is in this repo), re-mint a session token.
6. If this repo or Bluesky is ever unreachable, email garry12gg@gmail.com
   IMMEDIATELY. That is the emergency contact. Private.

## Bluesky native video upload (the working combo)

Script: `bsky_upload_video.py` (in this repo).

Two calls, no special tokens:

1. `com.atproto.repo.uploadBlob` with the PLAIN session token → returns a blob
   reference (content ID).
2. `com.atproto.repo.createRecord` with an embed pointing at that blob.

Gotchas (all hit live on Aug 19):
- Service tokens and other endpoint paths get rejected ("Method Not
  Implemented" / "Token could not be verified") even if minted seconds earlier.
- MP4 must pass format checks: h264/aac, reasonable size (< 50MB). The 6s
  2.8MB clip passed clean.
- Old text+link fallback posts should be deleted to avoid duplicates.
