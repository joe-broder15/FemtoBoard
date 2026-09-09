{
  pkgs,
  python3,
}:

let
  devPython = python3.withPackages (
    ps: with ps; [
      django
      pillow
      argon2-cffi
      django-stubs-ext
      django-stubs
      mypy
      pytest
      pytest-django
    ]
  );
in
pkgs.mkShell {
  packages = [
    devPython
    pkgs.uv
    pkgs.sqlite
    pkgs.nodejs_22
    pkgs.ffmpeg-headless
    pkgs.ruff
  ];

  shellHook = ''
    export DJANGO_SETTINGS_MODULE=femtoboard.settings.dev
    export UV_PYTHON=${devPython}/bin/python3
    mkdir -p data/db data/media/images data/media/videos data/media/thumbs
    echo "femtoboard dev shell: python=$(python3 --version), node=$(node --version), ffmpeg=$(ffmpeg -version | head -n1)"
    echo "Run 'manage.py runserver' or 'cd frontend && npm install && npm run build' as needed."
  '';
}
