use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub listen_addr: String,
    pub database_url: String,
    pub ip_hash_salt: String,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            listen_addr: env::var("FEMTOBOARD_LISTEN_ADDR")
                .unwrap_or_else(|_| "0.0.0.0:8080".to_string()),
            // `mode=rwc` creates the file if it doesn't exist yet (sea-orm's
            // sqlx-sqlite backend doesn't expose a separate create_if_missing
            // option — it's a connection-string query param instead).
            database_url: env::var("DATABASE_URL")
                .unwrap_or_else(|_| "sqlite://femtoboard.db?mode=rwc".to_string()),
            ip_hash_salt: env::var("FEMTOBOARD_IP_HASH_SALT")
                .unwrap_or_else(|_| "dev-insecure-salt-change-me".to_string()),
        }
    }
}
