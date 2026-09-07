use std::net::SocketAddr;

use axum::{
    extract::{ConnectInfo, Path, Query, State},
    Json,
};
use sea_orm::{ActiveModelTrait, ColumnTrait, EntityTrait, QueryFilter, QueryOrder, Set, TransactionTrait};
use serde::Deserialize;

use crate::{
    dto::{CreatePost, CreateThread, PostOut, ThreadWithPosts},
    entities::{
        boards, posts,
        prelude::{Boards, Posts, Threads},
        threads,
    },
    error::{AppError, AppResult},
    identity::{derive_tripcode, hash_ip},
    state::AppState,
    time::now_iso8601,
};

pub async fn list_threads(
    State(state): State<AppState>,
    Path(slug): Path<String>,
) -> AppResult<Json<Vec<threads::Model>>> {
    let board = Boards::find()
        .filter(boards::Column::Slug.eq(slug))
        .one(&state.db)
        .await?
        .ok_or(AppError::NotFound)?;

    let threads = Threads::find()
        .filter(threads::Column::BoardId.eq(board.id))
        .filter(threads::Column::IsArchived.eq(false))
        .order_by_desc(threads::Column::IsPinned)
        .order_by_desc(threads::Column::BumpedAt)
        .all(&state.db)
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

    let board = Boards::find()
        .filter(boards::Column::Slug.eq(slug))
        .one(&state.db)
        .await?
        .ok_or(AppError::NotFound)?;

    let txn = state.db.begin().await?;

    let thread = threads::ActiveModel {
        board_id: Set(board.id),
        subject: Set(input.subject),
        ..Default::default()
    }
    .insert(&txn)
    .await?;

    let ip_hash = hash_ip(&addr.ip().to_string(), &state.config.ip_hash_salt);
    let (author_name, tripcode) = derive_tripcode(
        input.author_name.as_deref().unwrap_or("Anonymous"),
        &state.config.ip_hash_salt,
    );

    let post = posts::ActiveModel {
        thread_id: Set(thread.id),
        board_id: Set(board.id),
        body: Set(input.body),
        author_name: Set(author_name),
        tripcode: Set(tripcode),
        ip_hash: Set(ip_hash),
        ..Default::default()
    }
    .insert(&txn)
    .await?;

    txn.commit().await?;

    Ok(Json(ThreadWithPosts {
        thread,
        posts: vec![post.into()],
    }))
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
    let thread = Threads::find_by_id(id)
        .one(&state.db)
        .await?
        .ok_or(AppError::NotFound)?;

    let posts = Posts::find()
        .filter(posts::Column::ThreadId.eq(id))
        .filter(posts::Column::Id.gt(q.since.unwrap_or(0)))
        .filter(posts::Column::IsDeleted.eq(false))
        .order_by_asc(posts::Column::Id)
        .all(&state.db)
        .await?
        .into_iter()
        .map(Into::into)
        .collect();

    Ok(Json(ThreadWithPosts { thread, posts }))
}

pub async fn create_reply(
    State(state): State<AppState>,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    Path(id): Path<i64>,
    Json(input): Json<CreatePost>,
) -> AppResult<Json<PostOut>> {
    if input.body.trim().is_empty() {
        return Err(AppError::BadRequest("body is required".into()));
    }

    let thread = Threads::find_by_id(id)
        .one(&state.db)
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

    let txn = state.db.begin().await?;

    let post = posts::ActiveModel {
        thread_id: Set(thread.id),
        board_id: Set(thread.board_id),
        body: Set(input.body),
        author_name: Set(author_name),
        tripcode: Set(tripcode),
        ip_hash: Set(ip_hash),
        ..Default::default()
    }
    .insert(&txn)
    .await?;

    let mut thread_update: threads::ActiveModel = thread.into();
    thread_update.bumped_at = Set(now_iso8601());
    thread_update.update(&txn).await?;

    txn.commit().await?;

    Ok(Json(post.into()))
}
