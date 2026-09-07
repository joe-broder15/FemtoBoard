# FemtoBoard

A self-hostable imageboard/BBS (4chan/vichan-style): boards, threads, replies,
image attachments — deployable via Docker or a Nix flake. See
[docs/design.md](docs/design.md) for the full design doc.

## Status

Milestone 1 (see design doc §12): core schema, Axum backend skeleton, and
board/thread/post CRUD. No auth, hash puzzle, or file uploads yet.

## Layout

- `backend/` — Rust/Axum API + SQLite (via `sea-orm`).
- `frontend/` — React/Vite/Tailwind SPA.

## Running locally

Backend (listens on `:8080` by default, creates `femtoboard.db` on first run):

```sh
cd backend
cargo run
```

Migrations run automatically on startup. To manage them by hand (e.g. to
inspect status, or apply/roll back without starting the server), use the
`migrate` binary:

```sh
cd backend
DATABASE_URL="sqlite://femtoboard.db?mode=rwc" cargo run --bin migrate -- status
```

After changing the schema (`backend/migrations/0001_init.sql` — or a new
migration file for future changes) or running the app against a fresh DB,
regenerate the SeaORM entities to match:

```sh
sea-orm-cli generate entity -u "sqlite://femtoboard.db" -o src/entities --with-serde both
```

Frontend (Vite dev server on `:5173`, proxies API calls to `:8080` via
`VITE_API_BASE`):

```sh
cd frontend
npm install
cp .env.example .env   # adjust VITE_API_BASE if needed
npm run dev
```
