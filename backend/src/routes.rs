use axum::{
    routing::{get, post},
    Router,
};
use tower_http::{cors::CorsLayer, trace::TraceLayer};

use crate::{handlers, state::AppState};

pub fn build_router(state: AppState) -> Router {
    let api = Router::new()
        .route("/boards", get(handlers::boards::list_boards).post(handlers::boards::create_board))
        .route("/boards/:slug", get(handlers::boards::get_board))
        .route(
            "/boards/:slug/threads",
            get(handlers::threads::list_threads).post(handlers::threads::create_thread),
        )
        .route("/threads/:id", get(handlers::threads::get_thread))
        .route("/threads/:id/posts", post(handlers::threads::create_reply))
        .route("/posts/:id", get(handlers::posts::get_post));

    Router::new()
        .nest("/api", api)
        .route("/healthz", get(|| async { "ok" }))
        .layer(TraceLayer::new_for_http())
        .layer(CorsLayer::permissive())
        .with_state(state)
}
