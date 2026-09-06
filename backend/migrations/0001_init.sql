-- Full schema per docs/design.md §4.
-- Milestone 1 only implements handlers for boards/threads/posts; the rest
-- of the tables are created now so later milestones don't need churny
-- incremental migrations.

CREATE TABLE boards (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    slug         TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    nsfw         INTEGER NOT NULL DEFAULT 0,
    thread_limit INTEGER NOT NULL DEFAULT 100,
    bump_limit   INTEGER NOT NULL DEFAULT 300,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE threads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id    INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    subject     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    bumped_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    is_pinned   INTEGER NOT NULL DEFAULT 0,
    is_locked   INTEGER NOT NULL DEFAULT 0,
    is_archived INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_threads_board_bumped ON threads(board_id, bumped_at DESC);

CREATE TABLE files (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256         TEXT NOT NULL UNIQUE,
    orig_filename  TEXT NOT NULL,
    mime           TEXT NOT NULL,
    width          INTEGER,
    height         INTEGER,
    size_bytes     INTEGER NOT NULL,
    path           TEXT NOT NULL,
    thumb_path     TEXT
);

CREATE TABLE posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id   INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    board_id    INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    parent_id   INTEGER REFERENCES posts(id) ON DELETE SET NULL,
    body        TEXT NOT NULL DEFAULT '',
    author_name TEXT NOT NULL DEFAULT 'Anonymous',
    tripcode    TEXT,
    ip_hash     TEXT NOT NULL,
    session_id  TEXT,
    file_id     INTEGER REFERENCES files(id),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    is_deleted  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_posts_thread ON posts(thread_id, id);
CREATE INDEX idx_posts_ip_hash ON posts(ip_hash, created_at);

CREATE TABLE bans (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_hash_or_cidr TEXT NOT NULL,
    board_id       INTEGER REFERENCES boards(id) ON DELETE CASCADE,
    reason         TEXT NOT NULL DEFAULT '',
    created_by     INTEGER,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    expires_at     TEXT
);

CREATE TABLE reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id     INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    reason      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    resolved    INTEGER NOT NULL DEFAULT 0,
    resolved_by INTEGER
);

CREATE TABLE mod_accounts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'mod')),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE mod_board_acl (
    mod_account_id INTEGER NOT NULL REFERENCES mod_accounts(id) ON DELETE CASCADE,
    board_id       INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    PRIMARY KEY (mod_account_id, board_id)
);

CREATE TABLE mod_actions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mod_account_id INTEGER NOT NULL REFERENCES mod_accounts(id),
    action         TEXT NOT NULL,
    target_post_id INTEGER REFERENCES posts(id),
    board_id       INTEGER REFERENCES boards(id),
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    note           TEXT NOT NULL DEFAULT ''
);

CREATE TABLE puzzle_challenges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nonce       TEXT NOT NULL UNIQUE,
    difficulty  INTEGER NOT NULL,
    issued_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    expires_at  TEXT NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0
);
