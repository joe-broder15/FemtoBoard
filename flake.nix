{
  description = "Femtoboard: a lightweight anonymous imageboard";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    let
      systemOutputs = flake-utils.lib.eachDefaultSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          python3 = pkgs.python3;

          femtoboard = pkgs.callPackage ./nix/package.nix { inherit python3; };

          checkPython = python3.withPackages (
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

          src = ./.;

          # Nix store paths are read-only, and each of these tools wants to
          # write somewhere (ruff/mypy caches, __pycache__, tox-style tmp
          # dirs) -- so every check stages a writable copy of the source
          # first rather than operating on `${src}` in place.
          stageSrc = ''
            export HOME=$TMPDIR
            cp -r ${src} $TMPDIR/src
            chmod -R u+w $TMPDIR/src
            cd $TMPDIR/src
          '';
        in
        {
          packages.default = femtoboard;
          packages.femtoboard = femtoboard;

          devShells.default = pkgs.callPackage ./nix/devshell.nix { inherit pkgs python3; };

          checks = {
            formatting =
              pkgs.runCommand "femtoboard-ruff-format"
                {
                  nativeBuildInputs = [ pkgs.ruff ];
                }
                ''
                  ${stageSrc}
                  ruff format --check .
                  touch $out
                '';

            lint =
              pkgs.runCommand "femtoboard-ruff-lint"
                {
                  nativeBuildInputs = [ pkgs.ruff ];
                }
                ''
                  ${stageSrc}
                  ruff check .
                  touch $out
                '';

            typing =
              pkgs.runCommand "femtoboard-mypy"
                {
                  nativeBuildInputs = [ checkPython ];
                  DJANGO_SETTINGS_MODULE = "femtoboard.settings.test";
                }
                ''
                  ${stageSrc}
                  mypy .
                  touch $out
                '';

            djangoChecks =
              pkgs.runCommand "femtoboard-django-checks"
                {
                  nativeBuildInputs = [ checkPython ];
                  DJANGO_SETTINGS_MODULE = "femtoboard.settings.test";
                }
                ''
                  ${stageSrc}
                  python manage.py check
                  touch $out
                '';

            tests =
              pkgs.runCommand "femtoboard-pytest"
                {
                  nativeBuildInputs = [ checkPython ];
                  DJANGO_SETTINGS_MODULE = "femtoboard.settings.test";
                }
                ''
                  ${stageSrc}
                  pytest -q
                  touch $out
                '';
          };
        }
      );
    in
    systemOutputs
    // {
      overlays.default = final: prev: {
        femtoboard = final.callPackage ./nix/package.nix { python3 = final.python3; };
      };

      # services.femtoboard.package defaults to pkgs.femtoboard, so a
      # consuming NixOS configuration should apply overlays.default (or
      # set services.femtoboard.package explicitly to
      # femtoboard.packages.<system>.default).
      nixosModules.femtoboard = import ./nix/module.nix;
      nixosModules.default = self.nixosModules.femtoboard;
    };
}
