# Femtoboard

A lightweight, anonymous imageboard built with Django, server-rendered
templates, and Tailwind CSS. See the design document in this repository's
history for the full specification; the summary below covers day-to-day
development.

## Quick start (development)

With [`uv`](https://docs.astral.sh/uv/) and Python 3.11+:

```sh
uv pip install -e ".[dev]"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Or, with Nix:

```sh
nix develop
python manage.py migrate
python manage.py runserver
```

The dev settings module (`femtoboard.settings.dev`, the `manage.py`
default) uses a local SQLite database under `data/db/` and local media
storage under `data/media/`. Two staff groups, **Administrators** and
**Janitors**, and the three initial boards (`/g/`, `/b/`, `/meta/`) are
created automatically by migrations. Create a superuser and add it to
the *Administrators* group (via `/staff/django-admin/`) to access the
staff dashboard at `/staff/`.

### Frontend assets

Tailwind CSS is compiled from `frontend/src/input.css` into
`static/css/site.css`. To rebuild after changing templates or the
Tailwind config:

```sh
cd frontend
npm install
npm run build      # or: npm run watch
```

### Tests and checks

```sh
ruff format --check .
ruff check .
mypy .
python manage.py check
pytest
```

All of the above are wired into `nix flake check`.

## Project layout

See design doc section 79 / `pyproject.toml` for the full app
breakdown: `boards`, `posts`, `moderation`, `antispam`, `mediafiles`,
and `accounts` are independent Django apps under `femtoboard/`
(the project's settings/urls/wsgi package).

## Deployment

`flake.nix` exposes `packages.femtoboard` (a `gunicorn`-served WSGI
application, `femtoboard-serve`) and `nixosModules.femtoboard`. A
consuming NixOS configuration should apply `overlays.default` (or set
`services.femtoboard.package` explicitly) and provide a `secretsDir`
containing `django-secret-key` and `tripcode-key` files outside the Nix
store:

```nix
{
  imports = [ femtoboard.nixosModules.femtoboard ];
  services.femtoboard = {
    enable = true;
    domain = "board.example.org";
    secretsDir = "/run/secrets/femtoboard";
    nginx.enable = true;
  };
}
```

The Nix packaging/module layer has not been exercised against a real
Nix evaluation in this environment; treat it as a first draft to
validate with `nix flake check` / `nixos-rebuild build-vm` before
relying on it.
