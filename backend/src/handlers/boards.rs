use axum::{
    extract::{Path, State},
    Json,
};

use crate::{
    error::{AppError, AppResult},
    models::{Board, CreateBoard},
    state::AppState,
};

pub async fn list_boards(State(state): State<AppState>) -> AppResult<Json<Vec<Board>>> {
    let boards = sqlx::query_as::<_, Board>("SELECT * FROM boards ORDER BY slug ASC")
        .fetch_all(&state.pool)
        .await?;
    Ok(Json(boards))
}

pub async fn create_board(
    State(state): State<AppState>,
    Json(input): Json<CreateBoard>,
) -> AppResult<Json<Board>> {
    if input.slug.trim().is_empty() || input.name.trim().is_empty() {
        return Err(AppError::BadRequest("slug and name are required".into()));
    }

    let id = sqlx::query(
        "INSERT INTO boards (slug, name, description, nsfw) VALUES (?, ?, ?, ?)",
    )
    .bind(&input.slug)
    .bind(&input.name)
    .bind(&input.description)
    .bind(input.nsfw)
    .execute(&state.pool)
    .await?
    .last_insert_rowid();

    let board = sqlx::query_as::<_, Board>("SELECT * FROM boards WHERE id = ?")
        .bind(id)
        .fetch_one(&state.pool)
        .await?;
    Ok(Json(board))
}

pub async fn get_board(
    State(state): State<AppState>,
    Path(slug): Path<String>,
) -> AppResult<Json<Board>> {
    let board = sqlx::query_as::<_, Board>("SELECT * FROM boards WHERE slug = ?")
        .bind(&slug)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(AppError::NotFound)?;
    Ok(Json(board))
}
