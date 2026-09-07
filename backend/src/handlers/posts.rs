use axum::extract::{Path, State};
use axum::Json;
use sea_orm::{ColumnTrait, EntityTrait, QueryFilter};

use crate::{
    dto::PostOut,
    entities::{posts, prelude::Posts},
    error::{AppError, AppResult},
    state::AppState,
};

pub async fn get_post(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> AppResult<Json<PostOut>> {
    let post = Posts::find_by_id(id)
        .filter(posts::Column::IsDeleted.eq(false))
        .one(&state.db)
        .await?
        .ok_or(AppError::NotFound)?;
    Ok(Json(post.into()))
}
