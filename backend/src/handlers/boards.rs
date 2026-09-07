use axum::{
    extract::{Path, State},
    Json,
};
use sea_orm::{ActiveModelTrait, ColumnTrait, EntityTrait, QueryFilter, QueryOrder, Set};

use crate::{
    dto::CreateBoard,
    entities::{boards, prelude::Boards},
    error::{AppError, AppResult},
    state::AppState,
};

pub async fn list_boards(State(state): State<AppState>) -> AppResult<Json<Vec<boards::Model>>> {
    let boards = Boards::find()
        .order_by_asc(boards::Column::Slug)
        .all(&state.db)
        .await?;
    Ok(Json(boards))
}

pub async fn create_board(
    State(state): State<AppState>,
    Json(input): Json<CreateBoard>,
) -> AppResult<Json<boards::Model>> {
    if input.slug.trim().is_empty() || input.name.trim().is_empty() {
        return Err(AppError::BadRequest("slug and name are required".into()));
    }

    let board = boards::ActiveModel {
        slug: Set(input.slug),
        name: Set(input.name),
        description: Set(input.description),
        nsfw: Set(input.nsfw),
        ..Default::default()
    }
    .insert(&state.db)
    .await?;

    Ok(Json(board))
}

pub async fn get_board(
    State(state): State<AppState>,
    Path(slug): Path<String>,
) -> AppResult<Json<boards::Model>> {
    let board = Boards::find()
        .filter(boards::Column::Slug.eq(slug))
        .one(&state.db)
        .await?
        .ok_or(AppError::NotFound)?;
    Ok(Json(board))
}
