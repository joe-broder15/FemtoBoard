mod config;
mod error;
mod handlers;
mod identity;
mod models;
mod routes;
mod state;

use std::net::SocketAddr;

use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions};
use tracing_subscriber::EnvFilter;

use config::Config;
use state::AppState;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .init();

    let config = Config::from_env();

    let connect_options: SqliteConnectOptions = config.database_url.parse::<SqliteConnectOptions>()?
        .create_if_missing(true);
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect_with(connect_options)
        .await?;

    sqlx::migrate!("./migrations").run(&pool).await?;

    let listen_addr: SocketAddr = config.listen_addr.parse()?;
    let state = AppState { pool, config };
    let app = routes::build_router(state);

    tracing::info!("listening on {listen_addr}");
    let listener = tokio::net::TcpListener::bind(listen_addr).await?;
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await?;

    Ok(())
}
