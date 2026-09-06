use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct Board {
    pub id: i64,
    pub slug: String,
    pub name: String,
    pub description: String,
    pub nsfw: bool,
    pub thread_limit: i64,
    pub bump_limit: i64,
    pub created_at: String,
}

#[derive(Debug, Deserialize)]
pub struct CreateBoard {
    pub slug: String,
    pub name: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub nsfw: bool,
}

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct Thread {
    pub id: i64,
    pub board_id: i64,
    pub subject: String,
    pub created_at: String,
    pub bumped_at: String,
    pub is_pinned: bool,
    pub is_locked: bool,
    pub is_archived: bool,
}

#[derive(Debug, Serialize)]
pub struct ThreadWithPosts {
    #[serde(flatten)]
    pub thread: Thread,
    pub posts: Vec<Post>,
}

#[derive(Debug, Deserialize)]
pub struct CreateThread {
    #[serde(default)]
    pub subject: String,
    pub body: String,
    #[serde(default)]
    pub author_name: Option<String>,
}

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct Post {
    pub id: i64,
    pub thread_id: i64,
    pub board_id: i64,
    pub parent_id: Option<i64>,
    pub body: String,
    pub author_name: String,
    pub tripcode: Option<String>,
    pub created_at: String,
    pub is_deleted: bool,
}

#[derive(Debug, Deserialize)]
pub struct CreatePost {
    pub body: String,
    #[serde(default)]
    pub author_name: Option<String>,
}
