use std::net::SocketAddr;

use femtoboard_backend::{config::Config, migrator::Migrator, routes, state::AppState};
use sea_orm::Database;
use sea_orm_migration::MigratorTrait;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .init();

    let config = Config::from_env();

    let db = Database::connect(&config.database_url).await?;
    Migrator::up(&db, None).await?;

    let listen_addr: SocketAddr = config.listen_addr.parse()?;
    let state = AppState { db, config };
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
