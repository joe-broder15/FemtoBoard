use axum::extract::{Path, State};
use axum::Json;

use crate::{
    error::{AppError, AppResult},
    models::Post,
    state::AppState,
};

pub async fn get_post(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> AppResult<Json<Post>> {
    let post = sqlx::query_as::<_, Post>("SELECT * FROM posts WHERE id = ? AND is_deleted = 0")
        .bind(id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(AppError::NotFound)?;
    Ok(Json(post))
}
