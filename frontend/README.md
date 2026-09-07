# FemtoBoard frontend

React + Vite + Tailwind SPA. See the [repo root README](../README.md) and
[docs/design.md](../docs/design.md) for the project overview.

## Development

```sh
npm install
cp .env.example .env   # adjust VITE_API_BASE if the backend isn't on :8080
npm run dev
```

## API types

The API's request/response shapes are generated from [`../openapi.yaml`](../openapi.yaml)
— that file is the single source of truth for the HTTP contract, not
`src/api.ts`. After changing a route on the backend (`backend/src/routes.rs`),
update `openapi.yaml` to match, then regenerate:

```sh
npm run gen:api
```

This runs [`openapi-typescript`](https://openapi-ts.dev/) and writes
`src/api/schema.d.ts` (generated — do not hand-edit). `src/api.ts` wraps that
schema with [`openapi-fetch`](https://openapi-ts.dev/openapi-fetch/) to get a
fully-typed client: request bodies, path/query params, and responses are all
checked against the spec at compile time.

## Build

```sh
npm run build
```
