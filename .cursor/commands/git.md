---
name: Git: Add, Commit & Push
description: Stage all changes, prompt for commit message, commit, and push to remote
shortcut: ctrl+alt+c  # Optional: Cursor will suggest this
---

```bash
git add . && read -p "Commit message: " msg && git commit -m "$msg" && git push