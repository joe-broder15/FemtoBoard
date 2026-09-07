use serde::{Deserialize, Serialize};

use crate::entities::{posts, threads};

/// Public view of a post. Deliberately narrower than `posts::Model`: that
/// entity carries `ip_hash` and `session_id`, which exist for ban/report
/// correlation (see docs/design.md §4) and must never reach API responses.
#[derive(Debug, Serialize)]
pub struct PostOut {
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

impl From<posts::Model> for PostOut {
    fn from(post: posts::Model) -> Self {
        Self {
            id: post.id,
            thread_id: post.thread_id,
            board_id: post.board_id,
            parent_id: post.parent_id,
            body: post.body,
            author_name: post.author_name,
            tripcode: post.tripcode,
            created_at: post.created_at,
            is_deleted: post.is_deleted,
        }
    }
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

#[derive(Debug, Deserialize)]
pub struct CreateThread {
    #[serde(default)]
    pub subject: String,
    pub body: String,
    #[serde(default)]
    pub author_name: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreatePost {
    pub body: String,
    #[serde(default)]
    pub author_name: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ThreadWithPosts {
    #[serde(flatten)]
    pub thread: threads::Model,
    pub posts: Vec<PostOut>,
}
