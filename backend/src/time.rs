use chrono::Utc;

/// Matches the format SQLite's `strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`
/// produces, so timestamps look the same whether set by the schema's
/// column default or by application code (e.g. bumping a thread).
pub fn now_iso8601() -> String {
    Utc::now().format("%Y-%m-%dT%H:%M:%S%.3fZ").to_string()
}
