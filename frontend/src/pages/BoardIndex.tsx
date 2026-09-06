import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Board } from "../api";

export default function BoardIndex() {
  const [boards, setBoards] = useState<Board[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listBoards().then(setBoards).catch((e) => setError(String(e.message ?? e)));
  }, []);

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-4 text-2xl font-bold">FemtoBoard</h1>
      {error && <p className="text-red-600">{error}</p>}
      <ul className="divide-y divide-zinc-300 dark:divide-zinc-700 border border-zinc-300 dark:border-zinc-700 rounded">
        {boards.map((b) => (
          <li key={b.id} className="p-3 hover:bg-zinc-200 dark:hover:bg-zinc-800">
            <Link to={`/${b.slug}`} className="font-semibold">
              /{b.slug}/ — {b.name}
            </Link>
            {b.description && (
              <p className="text-sm text-zinc-600 dark:text-zinc-400">{b.description}</p>
            )}
          </li>
        ))}
        {boards.length === 0 && !error && (
          <li className="p-3 text-zinc-500">No boards yet.</li>
        )}
      </ul>
    </div>
  );
}
