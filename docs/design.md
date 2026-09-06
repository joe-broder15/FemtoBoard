# Homelab Imageboard — Design Doc (v0.2)

## 1. Goals

- Generic, self-hostable imageboard/BBS software (4chan/vichan-style): boards, threads, replies, image attachments.
- Deployable two ways from the same source: **Docker** (docker-compose, single command) and **Nix flake** (`nix run`, NixOS module, or `nix build` → OCI image via `dockerTools`).
- No third-party CAPTCHA — a self-hosted **proof-of-work hash puzzle** gates posting.
- **Admin portal**: board management, post/thread deletion, bans, report queue, per-board moderator roles.
- UI: plain, fast, no-JS-required core browsing (progressive enhancement for posting/puzzle/live updates).

## 2. Non-goals (v0.1)

- Federation/ActivityPub.
- Multi-tenant SaaS (this is single-instance, single admin org, self-hosted).
- Built-in CDN/object storage — local disk by default, pluggable storage trait for later.

## 3. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Rust, **Axum** | async, small binary, easy static linking (`musl`) for minimal container/Nix closure |
| DB | **SQLite** via `sqlx` | single file, trivial backup (`cp board.db board.db.bak`), WAL mode for concurrent reads |
| Frontend | **React + Vite**, **Tailwind CSS** (utility classes, no component library) | CSR SPA; admin routes live in the same app, gated by role |
| Sessions/Auth | Signed cookie sessions (`tower-sessions` or similar) + Argon2 password hashing for admin/mod accounts | no OAuth dependency, works offline in a homelab |
| Image handling | `image` crate for thumbnailing; store original + thumb on disk | dedup by content hash (see §7) |
| Packaging | Docker (multi-stage build) **and** Nix flake (`crane`/`naersk` for Rust build, `dockerTools.buildLayeredImage` for image parity) | one source of truth, two output paths |

**Decision:** Axum over Actix-web, confirmed. Smaller dependency surface, cleaner `tower` middleware integration (rate limiting, sessions) for this app's size.

## 4. Data Model (SQLite)

```
boards        (id, slug, name, description, nsfw bool, thread_limit, bump_limit, created_at)
threads       (id, board_id, subject, created_at, bumped_at, is_pinned, is_locked, is_archived)
posts         (id, thread_id, board_id, parent_id nullable, body, author_name, tripcode,
               ip_hash, session_id nullable, file_id nullable, created_at, is_deleted)
files         (id, sha256, orig_filename, mime, width, height, size_bytes, path, thumb_path)
bans          (id, ip_hash_or_cidr, board_id nullable, reason, created_by, expires_at)
reports       (id, post_id, reason, created_at, resolved bool, resolved_by)
mod_accounts  (id, username, password_hash, role enum[admin, mod], created_at)
mod_board_acl (mod_account_id, board_id)   -- which boards a mod can act on
mod_actions   (id, mod_account_id, action, target_post_id, board_id, created_at, note)
puzzle_challenges (id, nonce, difficulty, issued_at, expires_at, used bool)
```

Notes:
- `ip_hash` stores a salted hash of the poster's IP, not the raw IP — enough for ban/report correlation without holding raw IPs indefinitely. Salt rotates per configurable interval; you lose historical ban matching on rotation, which is a deliberate privacy/retention trade-off worth flagging as configurable.
- `files.sha256` dedups identical uploads across the whole instance (classic imageboard behavior — re-uploads reuse the stored file).
- `posts.session_id` added (see §11 decision on rate limiting) — a non-identifying, rotating per-browser cookie value, used only as a secondary spam-velocity signal alongside `ip_hash`. Not a login session; unrelated to `mod_accounts` auth sessions.

The full schema above is created in a single initial migration even though v0.1 (Milestone 1) only implements handlers for `boards`/`threads`/`posts` — this avoids churn from incremental migrations once moderation/auth land in later milestones.

## 5. Roles & Moderation

- **admin**: full access — create/delete boards, manage all mod accounts, global bans, site config.
- **mod (janitor)**: scoped to boards listed in `mod_board_acl` — delete posts/threads, issue board-scoped bans, resolve reports on their boards only.
- All destructive actions write to `mod_actions` (audit trail, visible to admin only).
- Report queue: any visitor can report a post (no login) → lands in a queue filtered by board for the relevant mods.

## 6. Hash Puzzle (anti-spam, replaces CAPTCHA)

Flow:
1. Client requests a challenge: `GET /api/puzzle` → server returns `{nonce, difficulty}`, stores it in `puzzle_challenges` with short expiry (e.g. 2 min).
2. Client (JS, runs in a Web Worker so the page doesn't freeze) brute-forces a `solution` such that `SHA256(nonce + solution)` has `difficulty` leading zero bits.
3. On `POST /api/posts`, client includes `{nonce, solution}`; server re-hashes and verifies, marks the challenge `used = true` (one-time use, prevents replay).
4. `difficulty` is adjustable per board/globally in admin config — raise it during spam waves, lower it for normal traffic. Optionally auto-scale difficulty based on recent post velocity from a given `ip_hash`.

This requires no external service and no image/audio dataset to maintain — just CPU time, which is exactly the friction you want against bots without the accessibility problems of image CAPTCHAs. Falls back gracefully: if JS is disabled, posting simply isn't available (read-only browsing still works — see §8).

## 7. File Uploads

- Accepted types allow-listed by config (default: jpg/png/gif/webp, optionally webm/mp4 with a size cap).
- On upload: compute SHA-256 → check `files` table for existing match → if found, link to existing file (no duplicate storage); else store original + generate thumbnail.
- Storage is behind a small trait (`FileStore`) so local-disk is the default impl but S3/MinIO can be added later without touching handler code.
- **Hash-based blocklist hook**: expose a pluggable check (e.g. against a locally-maintained hash list of known-bad content, such as those used for CSAM detection like PhotoDNA-style perceptual hashing) that runs before a file is accepted. This is a standard piece of imageboard infrastructure and should be a first-class extension point rather than an afterthought, even though the default distribution ships with no external hash list configured — that's an operator responsibility to plug in.

## 8. Frontend (React SPA)

- Read path (board index, catalog, thread view) works with plain server-rendered data fetched on load — kept visually minimal: monospace/system font, simple table-and-post-cell layout reminiscent of classic imageboards, styled with Tailwind utility classes (no component library, no custom design system) so the look stays plain and the styling stays fast to iterate on.
- Posting UI: form + puzzle-solving indicator (spinner while the Web Worker grinds the hash).
- Live thread updates: simple polling (`GET /api/threads/:id?since=<post_id>`) every N seconds rather than WebSockets — fewer moving parts for a homelab deploy, easy to reason about, upgradeable later.
- `/admin` routes: board CRUD, ban list, report queue, mod account management — same app, role-gated via the session, so there's one binary/one container to run.

## 9. Deployment

**Docker path:**
- Multi-stage `Dockerfile`: stage 1 builds the Rust binary (`cargo build --release`) and the Vite frontend (`npm run build`), stage 2 is a minimal runtime image (`distroless` or `scratch` + musl binary) that serves the API and the built static frontend from one process.
- `docker-compose.yml` for the common case: one service, a volume for the SQLite file + uploads dir, env-file for config.

**Nix path:**
- `flake.nix` exposes:
  - `devShells.default` — Rust toolchain, sqlx-cli, node/npm for frontend dev.
  - `packages.default` — the built binary (via `crane` or `naersk`), with frontend assets embedded (e.g. `rust-embed`) or shipped alongside.
  - `packages.dockerImage` — `pkgs.dockerTools.buildLayeredImage` wrapping `packages.default`, so the *same* Nix build produces the OCI image used by the Docker path — one build definition, not two.
  - `nixosModules.default` — a NixOS module (`services.imageboard.enable = true; ...`) for people who want it as a systemd unit instead of a container at all.
- This means: Docker users get `docker compose up`, Nix users get `nix run`, NixOS users get a module — all from one Nix build graph.

## 10. Configuration

Single `config.toml` (or env var overrides, 12-factor style) covering: listen address, SQLite path, upload dir + size limits, allowed mime types, puzzle difficulty defaults, session secret, salt-rotation interval for IP hashing, per-board defaults (thread limit, bump limit, NSFW flag).

## 11. Resolved Decisions (was: Open Questions)

- **Rate limiting signal:** both. Primary key is `ip_hash`; a lightweight, non-identifying per-browser `session_id` cookie (rotated on expiry, not tied to login) is tracked alongside it as a secondary velocity signal. This catches IP-rotating spammers without adding friction for normal users, and doesn't require a login. Reflected in §4 (`posts.session_id`) and will inform the rate-limiter middleware design in a later milestone.
- **Tripcodes:** in scope for v0.1. The `posts.tripcode` column already exists in the schema and the classic `Name#password` → derived pseudonymous ID feature is cheap to implement (a salted hash of the password segment, base64/base62-encoded, no persistent secret storage needed) — no reason to defer it to a later milestone.
- **Public JSON API:** kept private/internal to the bundled frontend for v0.1. The `/api/*` routes exist only to serve the SPA; no stability/versioning guarantees are made yet. Opening a documented, stable read-only API for third-party clients/archivers is a candidate for a post-v0.1 milestone once the shape of the data has settled.

## 12. Milestones (suggested)

1. Core schema + Axum skeleton + board/thread/post CRUD (no auth, no puzzle) — prove the data model. **(current)**
2. Hash puzzle + file upload/dedup.
3. Admin portal (auth, board mgmt, deletion, bans).
4. Mod roles + report queue + audit log.
5. Docker + Nix packaging, NixOS module.
6. Polish: catalog view, thread auto-refresh, config docs.
