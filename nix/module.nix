{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.femtoboard;
  socketPath = "${cfg.dataDir}/runtime/femtoboard.sock";

  maintenanceCommands = {
    femtoboard-cleanup-ips = "cleanup_expired_ips";
    femtoboard-cleanup-pow = "cleanup_pow_challenges";
    femtoboard-cleanup-rate-limits = "cleanup_rate_limits";
    femtoboard-cleanup-media = "cleanup_orphaned_media";
    femtoboard-prune-threads = "prune_threads";
  };

  commonServiceHardening = {
    NoNewPrivileges = true;
    PrivateTmp = true;
    PrivateDevices = true;
    ProtectSystem = "strict";
    ProtectHome = true;
    ProtectKernelTunables = true;
    ProtectKernelModules = true;
    ProtectKernelLogs = true;
    ProtectControlGroups = true;
    ProtectClock = true;
    ProtectHostname = true;
    ProtectProc = "invisible";
    RestrictNamespaces = true;
    RestrictRealtime = true;
    RestrictSUIDSGID = true;
    LockPersonality = true;
    MemoryDenyWriteExecute = true;
    RemoveIPC = true;
    UMask = "0027";
    CapabilityBoundingSet = "";
    AmbientCapabilities = "";
    SystemCallFilter = [ "@system-service" ];
    SystemCallErrorNumber = "EPERM";
    ReadWritePaths = [ cfg.dataDir ];
  };

  commonEnvironment = {
    DJANGO_SETTINGS_MODULE = "femtoboard.settings.prod";
    FEMTOBOARD_DATA_DIR = cfg.dataDir;
    FEMTOBOARD_ALLOWED_HOSTS = lib.concatStringsSep "," cfg.allowedHosts;
    FEMTOBOARD_CSRF_TRUSTED_ORIGINS = lib.concatStringsSep "," (
      map (h: "https://${h}") cfg.allowedHosts
    );
    FEMTOBOARD_TRUSTED_PROXY_COUNT = "1";
    DJANGO_SECRET_KEY_FILE = "${cfg.secretsDir}/django-secret-key";
    FEMTOBOARD_TRIPCODE_KEY_FILE = "${cfg.secretsDir}/tripcode-key";
  };
in
{
  options.services.femtoboard = {
    enable = lib.mkEnableOption "the Femtoboard imageboard";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.femtoboard;
      description = "The femtoboard package to run.";
    };

    domain = lib.mkOption {
      type = lib.types.str;
      description = "Public domain name Femtoboard is served on.";
      example = "board.example.org";
    };

    allowedHosts = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ cfg.domain ];
      description = "Django ALLOWED_HOSTS / CSRF trusted origins (host part).";
    };

    dataDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/femtoboard";
      description = "Mutable data directory: SQLite database, media, runtime files.";
    };

    secretsDir = lib.mkOption {
      type = lib.types.path;
      description = ''
        Directory containing runtime secret files, outside the Nix store:
        `django-secret-key` and `tripcode-key`. Must be readable only by
        the femtoboard service user (mode 0400/0700), e.g. provisioned by
        agenix/sops-nix.
      '';
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = "femtoboard";
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = "femtoboard";
    };

    workers = lib.mkOption {
      type = lib.types.int;
      default = 3;
      description = "Number of gunicorn worker processes.";
    };

    nginx = {
      enable = lib.mkEnableOption "an automatically configured nginx virtual host";
    };
  };

  config = lib.mkIf cfg.enable {
    users.users.${cfg.user} = {
      isSystemUser = true;
      group = cfg.group;
      home = cfg.dataDir;
    };
    users.groups.${cfg.group} = { };

    systemd.tmpfiles.rules = [
      "d ${cfg.dataDir} 0750 ${cfg.user} ${cfg.group} -"
      "d ${cfg.dataDir}/db 0750 ${cfg.user} ${cfg.group} -"
      "d ${cfg.dataDir}/media 0750 ${cfg.user} ${cfg.group} -"
      "d ${cfg.dataDir}/media/images 0750 ${cfg.user} ${cfg.group} -"
      "d ${cfg.dataDir}/media/videos 0750 ${cfg.user} ${cfg.group} -"
      "d ${cfg.dataDir}/media/thumbs 0750 ${cfg.user} ${cfg.group} -"
      "d ${cfg.dataDir}/runtime 0750 ${cfg.user} ${cfg.group} -"
      "d ${cfg.dataDir}/runtime/staticfiles 0750 ${cfg.user} ${cfg.group} -"
    ];

    systemd.services.femtoboard-migrate = {
      description = "Femtoboard database migrations";
      after = [ "network.target" ];
      environment = commonEnvironment;
      serviceConfig = commonServiceHardening // {
        Type = "oneshot";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.dataDir;
        ExecStart = "${cfg.package}/bin/femtoboard-manage migrate --noinput";
      };
    };

    systemd.services.femtoboard-collectstatic = {
      description = "Femtoboard static file collection";
      after = [ "femtoboard-migrate.service" ];
      requires = [ "femtoboard-migrate.service" ];
      environment = commonEnvironment;
      serviceConfig = commonServiceHardening // {
        Type = "oneshot";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.dataDir;
        ExecStart = "${cfg.package}/bin/femtoboard-manage collectstatic --noinput";
      };
    };

    systemd.services.femtoboard = {
      description = "Femtoboard application server";
      after = [
        "network.target"
        "femtoboard-migrate.service"
        "femtoboard-collectstatic.service"
      ];
      requires = [
        "femtoboard-migrate.service"
        "femtoboard-collectstatic.service"
      ];
      wantedBy = [ "multi-user.target" ];
      path = [ pkgs.ffmpeg-headless ];
      environment = commonEnvironment // {
        FEMTOBOARD_BIND = "unix:${socketPath}";
        FEMTOBOARD_WORKERS = toString cfg.workers;
      };
      serviceConfig = commonServiceHardening // {
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.dataDir;
        RuntimeDirectory = "femtoboard";
        ExecStart = "${cfg.package}/bin/femtoboard-serve";
        Restart = "on-failure";
        RestartSec = "5s";
      };
    };

    systemd.services = lib.mapAttrs' (
      serviceName: subcommand:
      lib.nameValuePair serviceName {
        description = "Femtoboard maintenance: ${subcommand}";
        environment = commonEnvironment;
        serviceConfig = commonServiceHardening // {
          Type = "oneshot";
          User = cfg.user;
          Group = cfg.group;
          WorkingDirectory = cfg.dataDir;
          ExecStart = "${cfg.package}/bin/femtoboard-manage ${subcommand}";
        };
      }
    ) maintenanceCommands;

    systemd.timers = lib.mapAttrs' (
      serviceName: _: lib.nameValuePair serviceName {
        description = "Timer for ${serviceName}";
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnCalendar = "hourly";
          Persistent = true;
          RandomizedDelaySec = "10m";
        };
      }
    ) maintenanceCommands;

    services.nginx = lib.mkIf cfg.nginx.enable {
      enable = true;
      virtualHosts.${cfg.domain} = {
        forceSSL = lib.mkDefault true;
        enableACME = lib.mkDefault true;
        locations."/static/".alias = "${cfg.dataDir}/runtime/staticfiles/";
        locations."/media/".alias = "${cfg.dataDir}/media/";
        locations."/" = {
          proxyPass = "http://unix:${socketPath}:";
          proxyWebsockets = false;
          extraConfig = ''
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_set_header X-Forwarded-Proto $scheme;
            client_max_body_size 64m;
          '';
        };
      };
    };
  };
}
