# WP1 execution rulings

- Scope: WP1 integration only, not WP2 learned runner/API implementation.
- Use a new B integration branch in the existing checkout; no new worktree or change to source branches.
- Preserve B 971f221 task-board decisions where A contains older awaiting-review states; import A original handoffs/receipts separately.
- Preserve B sibling legacy asset layout in configs/legacy_assets.json; A internal ignored-package layout does not exist on this machine. No legacy assets changed.
- Existing API worker/service merged byte-identically to current B fixes; no new production behavior introduced.
- C merge: keep B latest acceptance states; take C-N3 in_progress from C; replace obsolete package-lock request with existing pnpm lock validation.
- Frontend source identity: 55 files differ from Git blobs only by Windows core.autocrlf checkout; normalized source matches C. No frontend source changes or lock changes.
