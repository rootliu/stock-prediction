---
name: sync-obsidian
description: Sync Obsidian vault to GitHub private repo with auto-commit and push, supporting multi-machine sync.
user_invocable: true
---

# Obsidian Vault GitHub Sync

Commit and push Obsidian vault changes to a private GitHub repo for cross-machine synchronization. Handles git init, remote setup, conflict resolution, and incremental sync.

## Usage

`/sync-obsidian` — commit all changes and push to GitHub
`/sync-obsidian pull` — pull latest changes from remote (for syncing from another machine)
`/sync-obsidian setup` — first-time setup: init repo, create GitHub remote, initial push

## Prerequisites

- A GitHub Personal Access Token (PAT) with `repo` scope
- The token should be stored or provided when prompted
- Obsidian vault path (auto-detected from `~/.obsidian` search)

## Workflow

### Phase 0: Discover Vault

```bash
# Auto-detect Obsidian vault location
find /Users -name ".obsidian" -type d 2>/dev/null | head -10
```

Store the vault path. Default: `/Users/rootliu/Documents/Obsidian Vault`

### Phase 1: Setup (first-time only, or `/sync-obsidian setup`)

#### 1.1 Initialize Git

```bash
cd "<vault_path>"

# Check if already a git repo
git rev-parse --is-inside-work-tree 2>/dev/null

# If not, initialize
git init
```

#### 1.2 Create .gitignore

Write a `.gitignore` to exclude Obsidian transient files:

```
# Obsidian workspace (changes per-device, causes conflicts)
.obsidian/workspace.json
.obsidian/workspace-mobile.json

# Plugin runtime data (regenerated on load)
.obsidian/plugins/*/data.json

# Trash and OS files
.trash/
.DS_Store
```

#### 1.3 Create GitHub Private Repo

Use the GitHub API (since `gh` CLI may have auth issues):

```bash
# Create private repo
GIT_SSL_NO_VERIFY=1 curl -s -X POST \
  -H "Authorization: token <PAT>" \
  -H "Content-Type: application/json" \
  https://api.github.com/user/repos \
  -d '{"name":"obsidian-vault","private":true,"description":"Personal Obsidian knowledge base"}'
```

**Note:** `GIT_SSL_NO_VERIFY=1` may be needed if the machine is behind a corporate proxy or VPN with TLS interception.

#### 1.4 Add Remote and Initial Push

```bash
cd "<vault_path>"
git remote add origin https://<PAT>@github.com/<username>/obsidian-vault.git
git add -A
git commit -m "feat: initial Obsidian vault sync"
GIT_SSL_NO_VERIFY=1 git push -u origin main
```

### Phase 2: Sync Push (`/sync-obsidian` or `/sync-obsidian push`)

#### 2.1 Check Status

```bash
cd "<vault_path>"
git status -s
```

If no changes, report "Already up to date" and exit.

#### 2.2 Auto-Commit

```bash
cd "<vault_path>"
git add -A

# Generate a descriptive commit message
git diff --cached --stat
```

Analyze the staged changes and generate a commit message:

```bash
git commit -m "$(cat <<'EOF'
sync: update <N> files — <brief description>

Changed: <list of changed files or categories>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

**Commit message heuristics:**
- If only journal files changed: `sync: update daily journals`
- If paper notes changed: `sync: update paper notes (<category>)`
- If mixed: `sync: update <N> files — journals, papers, topics`
- Include date in message if it helps: `sync: 2026-04-14 updates`

#### 2.3 Push

```bash
cd "<vault_path>"
GIT_SSL_NO_VERIFY=1 git push 2>&1
```

If push fails with "fetch first":

```bash
GIT_SSL_NO_VERIFY=1 git pull --rebase 2>&1
GIT_SSL_NO_VERIFY=1 git push 2>&1
```

### Phase 3: Sync Pull (`/sync-obsidian pull`)

For pulling changes made on another machine:

```bash
cd "<vault_path>"

# Stash any local changes first
git stash 2>/dev/null

# Pull latest
GIT_SSL_NO_VERIFY=1 git pull --rebase 2>&1

# Restore local changes
git stash pop 2>/dev/null
```

If there are merge conflicts:
1. List conflicted files
2. For `.md` files, prefer the version with more content (longer file)
3. For `.obsidian/` config files, prefer the local version
4. Ask user for confirmation on any ambiguous conflicts

### Phase 4: Report

Show summary:

```
Obsidian Vault Sync Complete
├── Vault: /Users/rootliu/Documents/Obsidian Vault
├── Remote: github.com/rootliu/obsidian-vault (private)
├── Action: push/pull
├── Files changed: N
├── Commit: <hash> <message>
└── Status: ✓ synced
```

## Key Lessons & Gotchas

1. **Sandbox restrictions**: The Obsidian vault is in `~/Documents/` which requires `dangerouslyDisableSandbox: true` for git operations. The user can use `/sandbox` to manage restrictions.

2. **TLS certificate issues**: Behind proxies/VPNs, GitHub API and git push may fail with TLS errors. Always use `GIT_SSL_NO_VERIFY=1` as a prefix for git and curl commands to GitHub.

3. **Token in remote URL**: The PAT is embedded in the remote URL (`https://<PAT>@github.com/...`). This avoids interactive auth prompts. The remote URL is stored in `.git/config` which is gitignored by the system.

4. **workspace.json conflicts**: Obsidian's `workspace.json` changes on every app focus/layout change. It MUST be in `.gitignore` to avoid constant conflicts across machines.

5. **Plugin data.json**: Each plugin's `data.json` stores runtime state. Syncing it causes conflicts. Gitignore it; each machine will regenerate its own.

6. **Obsidian Git plugin alternative**: If the user wants automatic periodic sync without Claude, recommend the "Obsidian Git" community plugin. But for on-demand sync with smart commit messages, this skill is superior.

7. **Merge conflicts in .md files**: When the same note is edited on two machines, prefer the longer version or use `git diff` to show both versions and let the user choose.

8. **Large binary files**: If the vault contains images or PDFs, consider adding them to `.gitignore` or using Git LFS. GitHub has a 100MB file size limit.

9. **gh CLI unreliable**: The `gh` CLI may have keyring/auth issues. Always fall back to direct `curl` API calls with the PAT for GitHub operations.

10. **First-time setup on new machine**: Clone the repo, then point Obsidian to the cloned directory as the vault:
    ```bash
    GIT_SSL_NO_VERIFY=1 git clone https://<PAT>@github.com/<user>/obsidian-vault.git "/Users/<user>/Documents/Obsidian Vault"
    ```
    Then open Obsidian → "Open folder as vault" → select that directory.
