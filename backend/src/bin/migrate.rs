use femtoboard_backend::migrator::Migrator;
use sea_orm_migration::cli;

#[tokio::main]
async fn main() {
    cli::run_cli(Migrator).await;
}
