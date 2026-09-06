use std::net::SocketAddr;

use axum::{
    extract::{ConnectInfo, Path, Query, State},
    Json,
};
use serde::Deserialize;

use crate::{
    error::{AppError, AppResult},
    identity::{derive_tripcode, hash_ip},
    models::{Board, CreatePost, CreateThread, Post, Thread, ThreadWithPosts},
    state::AppState,
};

pub async fn list_threads(
    State(state): State<AppState>,
    Path(slug): Path<String>,
) -> AppResult<Json<Vec<Thread>>> {
    let board = sqlx::query_as::<_, Board>("SELECT * FROM boards WHERE slug = ?")
        .bind(&slug)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(AppError::NotFound)?;

    let threads = sqlx::query_as::<_, Thread>(
        "SELECT * FROM threads WHERE board_id = ? AND is_archived = 0 \
         ORDER BY is_pinned DESC, bumped_at DESC",
    )
    .bind(board.id)
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(threads))
}

pub async fn create_thread(
    State(state): State<AppState>,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    Path(slug): Path<String>,
    Json(input): Json<CreateThread>,
) -> AppResult<Json<ThreadWithPosts>> {
    if input.body.trim().is_empty() {
        return Err(AppError::BadRequest("body is required".into()));
    }

    let board = sqlx::query_as::<_, Board>("SELECT * FROM boards WHERE slug = ?")
        .bind(&slug)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(AppError::NotFound)?;

    let mut tx = state.pool.begin().await?;

    let thread_id = sqlx::query("INSERT INTO threads (board_id, subject) VALUES (?, ?)")
        .bind(board.id)
        .bind(&input.subject)
        .execute(&mut *tx)
        .await?
        .last_insert_rowid();

    let ip_hash = hash_ip(&addr.ip().to_string(), &state.config.ip_hash_salt);
    let (author_name, tripcode) = derive_tripcode(
        input.author_name.as_deref().unwrap_or("Anonymous"),
        &state.config.ip_hash_salt,
    );

    sqlx::query(
        "INSERT INTO posts (thread_id, board_id, body, author_name, tripcode, ip_hash) \
         VALUES (?, ?, ?, ?, ?, ?)",
    )
    .bind(thread_id)
    .bind(board.id)
    .bind(&input.body)
    .bind(&author_name)
    .bind(&tripcode)
    .bind(&ip_hash)
    .execute(&mut *tx)
    .await?;

    tx.commit().await?;

    let thread = sqlx::query_as::<_, Thread>("SELECT * FROM threads WHERE id = ?")
        .bind(thread_id)
        .fetch_one(&state.pool)
        .await?;
    let posts = sqlx::query_as::<_, Post>(
        "SELECT * FROM posts WHERE thread_id = ? ORDER BY id ASC",
    )
    .bind(thread_id)
    .fetch_all(&state.pool)
    .await?;

    Ok(Json(ThreadWithPosts { thread, posts }))
}

#[derive(Debug, Deserialize)]
pub struct SinceQuery {
    pub since: Option<i64>,
}

pub async fn get_thread(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Query(q): Query<SinceQuery>,
) -> AppResult<Json<ThreadWithPosts>> {
    let thread = sqlx::query_as::<_, Thread>("SELECT * FROM threads WHERE id = ?")
        .bind(id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(AppError::NotFound)?;

    let posts = sqlx::query_as::<_, Post>(
        "SELECT * FROM posts WHERE thread_id = ? AND id > ? AND is_deleted = 0 ORDER BY id ASC",
    )
    .bind(id)
    .bind(q.since.unwrap_or(0))
    .fetch_all(&state.pool)
    .await?;

    Ok(Json(ThreadWithPosts { thread, posts }))
}

pub async fn create_reply(
    State(state): State<AppState>,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    Path(id): Path<i64>,
    Json(input): Json<CreatePost>,
) -> AppResult<Json<Post>> {
    if input.body.trim().is_empty() {
        return Err(AppError::BadRequest("body is required".into()));
    }

    let thread = sqlx::query_as::<_, Thread>("SELECT * FROM threads WHERE id = ?")
        .bind(id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(AppError::NotFound)?;

    if thread.is_locked {
        return Err(AppError::BadRequest("thread is locked".into()));
    }

    let ip_hash = hash_ip(&addr.ip().to_string(), &state.config.ip_hash_salt);
    let (author_name, tripcode) = derive_tripcode(
        input.author_name.as_deref().unwrap_or("Anonymous"),
        &state.config.ip_hash_salt,
    );

    let mut tx = state.pool.begin().await?;

    let post_id = sqlx::query(
        "INSERT INTO posts (thread_id, board_id, body, author_name, tripcode, ip_hash) \
         VALUES (?, ?, ?, ?, ?, ?)",
    )
    .bind(thread.id)
    .bind(thread.board_id)
    .bind(&input.body)
    .bind(&author_name)
    .bind(&tripcode)
    .bind(&ip_hash)
    .execute(&mut *tx)
    .await?
    .last_insert_rowid();

    sqlx::query("UPDATE threads SET bumped_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?")
        .bind(thread.id)
        .execute(&mut *tx)
        .await?;

    tx.commit().await?;

    let post = sqlx::query_as::<_, Post>("SELECT * FROM posts WHERE id = ?")
        .bind(post_id)
        .fetch_one(&state.pool)
        .await?;
    Ok(Json(post))
}
