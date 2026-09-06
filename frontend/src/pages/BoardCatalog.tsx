import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Board, type Thread } from "../api";

export default function BoardCatalog() {
  const { slug = "" } = useParams();
  const [board, setBoard] = useState<Board | null>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [subject, setSubject] = useState("");
  const [authorName, setAuthorName] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    api.getBoard(slug).then(setBoard).catch((e) => setError(String(e.message ?? e)));
    api.listThreads(slug).then(setThreads).catch((e) => setError(String(e.message ?? e)));
  }

  useEffect(refresh, [slug]);

  async function submitThread(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.createThread(slug, {
        subject: subject || undefined,
        body,
        author_name: authorName || undefined,
      });
      setSubject("");
      setAuthorName("");
      setBody("");
      refresh();
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
      <h1 className="mb-4 text-2xl font-bold">/{slug}/ {board ? `— ${board.name}` : ""}</h1>

      <form onSubmit={submitThread} className="mb-6 space-y-2 rounded border border-zinc-300 dark:border-zinc-700 p-3">
        <div className="flex gap-2">
          <input
            className="flex-1 border border-zinc-300 dark:border-zinc-700 bg-transparent px-2 py-1"
            placeholder="Name#trip (optional)"
            value={authorName}
            onChange={(e) => setAuthorName(e.target.value)}
          />
          <input
            className="flex-1 border border-zinc-300 dark:border-zinc-700 bg-transparent px-2 py-1"
            placeholder="Subject (optional)"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </div>
        <textarea
          className="w-full border border-zinc-300 dark:border-zinc-700 bg-transparent px-2 py-1"
          rows={4}
          placeholder="Comment"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
        <button
          type="submit"
          disabled={submitting}
          className="border border-zinc-400 px-3 py-1 hover:bg-zinc-200 dark:hover:bg-zinc-800 disabled:opacity-50"
        >
          New Thread
        </button>
      </form>

      {error && <p className="text-red-600">{error}</p>}

      <ul className="space-y-2">
        {threads.map((t) => (
          <li key={t.id} className="border border-zinc-300 dark:border-zinc-700 p-3">
            <Link to={`/thread/${t.id}`} className="font-semibold hover:underline">
              {t.subject || `Thread #${t.id}`}
            </Link>
            <span className="ml-2 text-xs text-zinc-500">bumped {t.bumped_at}</span>
          </li>
        ))}
        {threads.length === 0 && <li className="text-zinc-500">No threads yet.</li>}
      </ul>
    </div>
  );
}
