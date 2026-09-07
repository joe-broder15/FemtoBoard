import createClient from "openapi-fetch";
import type { components, paths } from "./api/schema";

// Request/response types are generated from ../openapi.yaml — the single
// source of truth for the API's shape. Run `npm run gen:api` after editing
// that file (see frontend/README.md).
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080/api";

const client = createClient<paths>({ baseUrl: API_BASE });

export type Board = components["schemas"]["Board"];
export type Thread = components["schemas"]["Thread"];
export type Post = components["schemas"]["Post"];
export type ThreadWithPosts = components["schemas"]["ThreadWithPosts"];

function unwrap<T>({ data, error }: { data?: T; error?: { error?: string } }): T {
  if (error) throw new Error(error.error ?? "request failed");
  return data as T;
}

export const api = {
  listBoards: async () => unwrap(await client.GET("/boards")),

  getBoard: async (slug: string) =>
    unwrap(await client.GET("/boards/{slug}", { params: { path: { slug } } })),

  listThreads: async (slug: string) =>
    unwrap(await client.GET("/boards/{slug}/threads", { params: { path: { slug } } })),

  createThread: async (
    slug: string,
    body: { subject?: string; body: string; author_name?: string },
  ) =>
    unwrap(
      await client.POST("/boards/{slug}/threads", {
        params: { path: { slug } },
        body,
      }),
    ),

  getThread: async (id: number, since?: number) =>
    unwrap(
      await client.GET("/threads/{id}", {
        params: { path: { id }, query: since ? { since } : undefined },
      }),
    ),

  createReply: async (threadId: number, body: { body: string; author_name?: string }) =>
    unwrap(
      await client.POST("/threads/{id}/posts", {
        params: { path: { id: threadId } },
        body,
      }),
    ),
};
