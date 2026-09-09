"""Create the Administrator and Janitor groups with their permission
sets (design doc sections 8, 9). This is the authoritative, repeatable
definition of staff role permissions -- not something configured by
hand after deployment."""

from __future__ import annotations

from django.apps import apps as global_apps
from django.db import migrations

_ADMIN_ONLY_BOARD = ["add_board", "change_board", "delete_board", "view_board"]
_ADMIN_ONLY_SITECONFIG = ["add_siteconfiguration", "change_siteconfiguration", "view_siteconfiguration"]
_ADMIN_ONLY_USER = ["add_user", "change_user", "delete_user", "view_user"]
_ADMIN_ONLY_GROUP = ["add_group", "change_group", "delete_group", "view_group"]
_ADMIN_ONLY_BAN = ["change_ban", "delete_ban", "issue_permanent_ban", "search_ip"]

_SHARED_BAN = ["add_ban", "view_ban"]
_SHARED_REPORT = ["view_report", "change_report", "resolve_report"]
_SHARED_MODERATION_ACTION = ["view_moderationaction", "view_ip_history"]
_SHARED_POST = ["view_post", "view_thread", "delete_post", "delete_thread", "lock_thread", "sticky_thread"]


def _perms(Permission, ContentType, app_label: str, model: str, codenames: list[str]) -> list[object]:
    ct = ContentType.objects.get(app_label=app_label, model=model)
    return list(Permission.objects.filter(content_type=ct, codename__in=codenames))


def create_groups(apps, schema_editor):  # noqa: ANN001, ANN201
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Permission/ContentType rows are normally created by a post_migrate
    # signal that only fires once, after every app's migrations have run.
    # This data migration needs the boards/posts/moderation permissions
    # to already exist, so create them explicitly (the documented Django
    # workaround for referencing permissions from a data migration).
    from django.contrib.auth.management import create_permissions

    for app_config in global_apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    admins, _ = Group.objects.get_or_create(name="Administrators")
    janitors, _ = Group.objects.get_or_create(name="Janitors")

    admin_perms: list[object] = []
    admin_perms += _perms(Permission, ContentType, "boards", "board", _ADMIN_ONLY_BOARD)
    admin_perms += _perms(Permission, ContentType, "boards", "siteconfiguration", _ADMIN_ONLY_SITECONFIG)
    admin_perms += _perms(Permission, ContentType, "auth", "user", _ADMIN_ONLY_USER)
    admin_perms += _perms(Permission, ContentType, "auth", "group", _ADMIN_ONLY_GROUP)
    admin_perms += _perms(Permission, ContentType, "moderation", "ban", _ADMIN_ONLY_BAN + _SHARED_BAN)
    admin_perms += _perms(Permission, ContentType, "moderation", "report", _SHARED_REPORT)
    admin_perms += _perms(
        Permission, ContentType, "moderation", "moderationaction", _SHARED_MODERATION_ACTION
    )
    admin_perms += _perms(Permission, ContentType, "posts", "post", _SHARED_POST)

    janitor_perms: list[object] = []
    janitor_perms += _perms(Permission, ContentType, "moderation", "ban", _SHARED_BAN)
    janitor_perms += _perms(Permission, ContentType, "moderation", "report", _SHARED_REPORT)
    janitor_perms += _perms(
        Permission, ContentType, "moderation", "moderationaction", _SHARED_MODERATION_ACTION
    )
    janitor_perms += _perms(Permission, ContentType, "posts", "post", _SHARED_POST)

    admins.permissions.set(admin_perms)
    janitors.permissions.set(janitor_perms)


def remove_groups(apps, schema_editor):  # noqa: ANN001, ANN201
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Administrators", "Janitors"]).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("boards", "0001_initial"),
        ("posts", "0001_initial"),
        ("moderation", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
