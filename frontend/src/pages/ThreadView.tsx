import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Post, type ThreadWithPosts } from "../api";

const POLL_INTERVAL_MS = 5000;

export default function ThreadView() {
  const { id = "" } = useParams();
  const threadId = Number(id);
  const [thread, setThread] = useState<ThreadWithPosts | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lastPostId = useRef(0);

  const [authorName, setAuthorName] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    lastPostId.current = 0;
    setThread(null);

    async function poll() {
      try {
        const data = await api.getThread(threadId, lastPostId.current || undefined);
        if (cancelled) return;
        setThread((prev) => {
          if (!prev) return data;
          return { ...data, posts: [...prev.posts, ...data.posts] };
        });
        if (data.posts.length > 0) {
          lastPostId.current = data.posts[data.posts.length - 1].id;
        }
      } catch (e) {
        if (!cancelled) setError(String((e as Error).message ?? e));
      }
    }

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [threadId]);

  async function submitReply(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const post = await api.createReply(threadId, { body, author_name: authorName || undefined });
      setBody("");
      setThread((prev) => (prev ? { ...prev, posts: [...prev.posts, post] } : prev));
      lastPostId.current = post.id;
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <p className="mb-2">
        <Link to="/" className="text-sm text-zinc-500 hover:underline">
          &larr; boards
        </Link>
      </p>
      <h1 className="mb-4 text-2xl font-bold">{thread?.subject || `Thread #${threadId}`}</h1>

      {error && <p className="text-red-600">{error}</p>}

      <ul className="mb-6 space-y-3">
        {thread?.posts.map((p) => <PostCell key={p.id} post={p} />)}
      </ul>

      <form onSubmit={submitReply} className="space-y-2 rounded border border-zinc-300 dark:border-zinc-700 p-3">
        <input
          className="w-full border border-zinc-300 dark:border-zinc-700 bg-transparent px-2 py-1"
          placeholder="Name#trip (optional)"
          value={authorName}
          onChange={(e) => setAuthorName(e.target.value)}
        />
        <textarea
          className="w-full border border-zinc-300 dark:border-zinc-700 bg-transparent px-2 py-1"
          rows={3}
          placeholder="Reply"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
        <button
          type="submit"
          disabled={submitting}
          className="border border-zinc-400 px-3 py-1 hover:bg-zinc-200 dark:hover:bg-zinc-800 disabled:opacity-50"
        >
          Reply
        </button>
      </form>
    </div>
  );
}

function PostCell({ post }: { post: Post }) {
  return (
    <li className="border border-zinc-300 dark:border-zinc-700 p-3" id={`post-${post.id}`}>
      <div className="text-sm">
        <span className="font-semibold text-emerald-700 dark:text-emerald-400">{post.author_name}</span>
        {post.tripcode && <span className="ml-1 text-zinc-500">{post.tripcode}</span>}
        <span className="ml-2 text-xs text-zinc-500">{post.created_at}</span>
        <span className="ml-2 text-xs text-zinc-500">No.{post.id}</span>
      </div>
      <p className="whitespace-pre-wrap">{post.body}</p>
    </li>
  );
}
