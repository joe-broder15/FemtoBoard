{ lib, python3 }:

python3.pkgs.buildPythonApplication {
  pname = "femtoboard";
  version = "0.1.0";
  pyproject = true;

  src = lib.cleanSourceWith {
    src = ../.;
    filter =
      path: type:
      let
        base = baseNameOf path;
      in
      !(
        lib.hasSuffix ".pyc" path
        || base == "__pycache__"
        || base == ".venv"
        || base == "node_modules"
        || base == "data"
        || base == ".mypy_cache"
        || base == ".ruff_cache"
        || base == ".pytest_cache"
      );
  };

  build-system = [ python3.pkgs.hatchling ];

  dependencies = with python3.pkgs; [
    django
    pillow
    argon2-cffi
    django-stubs-ext
    gunicorn
  ];

  # No PyPI/network access during the sandboxed build, and the app has
  # no compiled extensions of its own to exercise here; the real test
  # suite runs as a separate flake check (see flake.nix `checks.tests`)
  # against a full dev environment, not this minimal runtime closure.
  doCheck = false;

  meta = {
    description = "Lightweight anonymous imageboard";
    mainProgram = "femtoboard-manage";
  };
}
