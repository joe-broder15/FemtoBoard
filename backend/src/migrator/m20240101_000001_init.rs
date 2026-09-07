use sea_orm_migration::prelude::*;

// Full schema per docs/design.md §4, kept as one plain-SQL file (rather than
// SeaORM's table-builder DSL) so it stays a straight copy-paste match with
// the doc. See ../../migrations/0001_init.sql.
const SQL: &str = include_str!("../../migrations/0001_init.sql");

#[derive(DeriveMigrationName)]
pub struct Migration;

#[async_trait::async_trait]
impl MigrationTrait for Migration {
    async fn up(&self, manager: &SchemaManager) -> Result<(), DbErr> {
        let db = manager.get_connection();
        let sql_without_comments: String = SQL
            .lines()
            .filter(|line| !line.trim_start().starts_with("--"))
            .collect::<Vec<_>>()
            .join("\n");
        for statement in sql_without_comments.split(';') {
            let statement = statement.trim();
            if statement.is_empty() {
                continue;
            }
            db.execute_unprepared(statement).await?;
        }
        Ok(())
    }

    async fn down(&self, manager: &SchemaManager) -> Result<(), DbErr> {
        for table in [
            "puzzle_challenges",
            "mod_actions",
            "mod_board_acl",
            "mod_accounts",
            "reports",
            "bans",
            "posts",
            "files",
            "threads",
            "boards",
        ] {
            manager
                .drop_table(Table::drop().table(Alias::new(table)).to_owned())
                .await?;
        }
        Ok(())
    }
}
