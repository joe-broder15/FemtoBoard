const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080/api";

export interface Board {
  id: number;
  slug: string;
  name: string;
  description: string;
  nsfw: boolean;
  thread_limit: number;
  bump_limit: number;
  created_at: string;
}

export interface Post {
  id: number;
  thread_id: number;
  board_id: number;
  parent_id: number | null;
  body: string;
  author_name: string;
  tripcode: string | null;
  created_at: string;
  is_deleted: boolean;
}

export interface Thread {
  id: number;
  board_id: number;
  subject: string;
  created_at: string;
  bumped_at: string;
  is_pinned: boolean;
  is_locked: boolean;
  is_archived: boolean;
}

export interface ThreadWithPosts extends Thread {
  posts: Post[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listBoards: () => request<Board[]>("/boards"),
  getBoard: (slug: string) => request<Board>(`/boards/${slug}`),
  listThreads: (slug: string) => request<Thread[]>(`/boards/${slug}/threads`),
  createThread: (slug: string, body: { subject?: string; body: string; author_name?: string }) =>
    request<ThreadWithPosts>(`/boards/${slug}/threads`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getThread: (id: number, since?: number) =>
    request<ThreadWithPosts>(`/threads/${id}${since ? `?since=${since}` : ""}`),
  createReply: (threadId: number, body: { body: string; author_name?: string }) =>
    request<Post>(`/threads/${threadId}/posts`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
