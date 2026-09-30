"""The ``roblox`` command line tool.

Every command fetches something from Roblox, prints a short summary, and writes
the result to a file in the output folder (``./roblox_data`` by default). Add
``--stdout`` to print JSON to the terminal instead of writing a file.

Identifiers can be a numeric id, a roblox.com link, or (for users) a username.
Run ``roblox --help`` or ``roblox user --help`` for the command list.
"""

from __future__ import annotations

import functools
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Sequence

import click

from . import __version__
from .client import RobloxClient
from .collect import (
    GAME_TABLES, GROUP_TABLES, USER_TABLES, _hydrate_names, friend_network,
    game_snapshot, group_network, group_snapshot, user_snapshot,
)
from .config import RobloxConfig, load_config
from .errors import (
    AuthRequiredError, BadRequestError, EntityUnavailable, NotFoundError,
    PrivateError, RateLimitedError, RobloxError, ServerError,
)
from .export import Snapshot, edgelist_to_graphml, to_dataframe, write_json, write_records
from .urls import looks_like_id, parse_roblox_url

log = logging.getLogger("robloxwrapper.cli")


# -- runtime ------------------------------------------------------------------

@dataclass
class Runtime:
    config: RobloxConfig
    client: RobloxClient
    fmt: str = "csv"
    quiet: bool = False
    debug: bool = False
    stdout: bool = False

    @property
    def output_dir(self) -> Path:
        return Path(self.config.output_dir)

    def say(self, message: str) -> None:
        if not self.quiet:
            click.echo(message, err=True)

    def progress(self, message: str) -> None:
        if not self.quiet:
            click.echo(f"  ... {message}", err=True)

    def emit(self, name: str, records: Any, summary: Optional[str] = None) -> Optional[Path]:
        """Print JSON (``--stdout``) or write ``<name>.<fmt>`` and report the path."""
        if self.stdout:
            click.echo(json.dumps(records, indent=2, ensure_ascii=False, default=str))
            return None
        if isinstance(records, dict):
            records = [records]
        path = self.output_dir / f"{name}.{self.fmt}"
        write_records(records, path, fmt=self.fmt)
        if summary:
            click.echo(summary)
        click.echo(f"Wrote {len(records)} row(s) to {path}")
        return path

    def emit_snapshot(self, snap: Snapshot) -> List[Path]:
        if self.stdout:
            click.echo(json.dumps({"meta": snap.meta, "tables": snap.tables},
                                  indent=2, ensure_ascii=False, default=str))
            return []
        paths = snap.save(self.output_dir, fmt=self.fmt)
        click.echo(f"Saved {len(paths) - 1} table(s) for {snap.entity} {snap.entity_id} "
                   f"to {self.output_dir}/")
        for name, count in snap.counts().items():
            click.echo(f"  {name:<20} {count:>7} row(s)")
        for name, reason in snap.meta.get("omitted", {}).items():
            click.echo(f"  {name:<20} skipped: {_explain_omission(reason)}")
        for name in snap.meta.get("truncated", {}):
            click.echo(f"  {name:<20} truncated by a --max limit; more data exists")
        failed = snap.meta.get("failed") or {}
        if failed:
            click.echo(f"  {len(failed)} item(s) could not be fetched; see the manifest")
        click.echo(f"Manifest: {paths[-1]}")
        return paths


def _explain_omission(reason: str) -> str:
    return {
        "cookie-required": "Roblox only shows this to logged-in accounts (add --cookie)",
        "private": "this account keeps it private",
        "not-found": "Roblox returned not found",
        "invalid": "Roblox rejected the request (banned, locked, or deleted?)",
        "no-root-place": "the game has no root place",
        "error": "an unexpected Roblox error (see the manifest)",
    }.get(reason, reason)


def _friendly(error: Exception) -> str:
    if isinstance(error, EntityUnavailable):
        return str(error).split(" [")[0]
    if isinstance(error, NotFoundError):
        return "Not found. Check the id; the account, group, or game may be deleted."
    if isinstance(error, AuthRequiredError):
        return ("Roblox only shows this to logged-in accounts. Add --cookie or set "
                "ROBLOX_COOKIE (see docs/getting-started.md).")
    if isinstance(error, PrivateError):
        return "Roblox says this is private or hidden from you."
    if isinstance(error, BadRequestError):
        return f"Roblox rejected the request: {error.roblox_message or 'bad request'}."
    if isinstance(error, RateLimitedError):
        return "Roblox is rate limiting this computer. Wait a minute and try again."
    if isinstance(error, ServerError):
        return "Roblox's servers returned an error. Try again in a few minutes."
    if isinstance(error, RobloxError):
        return f"Roblox error: {error}"
    return str(error)


def handle_errors(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = click.get_current_context()
        rt: Runtime = ctx.obj
        try:
            return fn(*args, **kwargs)
        except click.ClickException:
            raise
        except (RobloxError, FileNotFoundError, ValueError) as e:
            if rt.debug:
                raise
            raise click.ClickException(_friendly(e))
        except KeyboardInterrupt:
            raise click.ClickException("Stopped by user (Ctrl-C). Files written so far are kept.")
    return wrapper


# -- identifier resolution ----------------------------------------------------

def resolve_user(rt: Runtime, value: str) -> int:
    """Numeric id, roblox.com/users/<id> link, or username."""
    value = value.strip()
    if looks_like_id(value):
        return int(value)
    try:
        kind, ident = parse_roblox_url(value)
    except ValueError:
        kind, ident = None, None
    if kind == "user":
        return ident
    if kind is not None:
        raise click.ClickException(f"That is a {kind} link, not a user.")
    match = rt.client.users.resolve(value)
    rt.say(f"Resolved username {value!r} to user id {match['id']}")
    return int(match["id"])


def resolve_group(rt: Runtime, value: str) -> int:
    value = value.strip()
    if looks_like_id(value):
        return int(value)
    try:
        kind, ident = parse_roblox_url(value)
    except ValueError:
        raise click.ClickException(
            "Give a numeric group id or a roblox.com/groups/<id> link. "
            "To find a group by name, run: roblox search groups \"<name>\"")
    if kind != "group":
        raise click.ClickException(f"That is a {kind} link, not a group.")
    return ident


def resolve_universe(rt: Runtime, value: str, place: bool) -> int:
    """Universe id, or a place id (``--place``) / roblox.com/games/<placeId> link."""
    value = value.strip()
    if looks_like_id(value):
        ident = int(value)
        if place:
            universe = rt.client.games.place_to_universe(ident)
            rt.say(f"Resolved place {ident} to universe {universe}")
            return universe
        return ident
    try:
        kind, ident = parse_roblox_url(value)
    except ValueError:
        raise click.ClickException("Give a universe id, a place id with --place, or a "
                                   "roblox.com/games/<id> link.")
    if kind != "game":
        raise click.ClickException(f"That is a {kind} link, not a game.")
    universe = rt.client.games.place_to_universe(ident)
    rt.say(f"Resolved place {ident} to universe {universe}")
    return universe


def _split_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _read_ids(path: str) -> List[int]:
    ids: List[int] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip().split(",")[0].strip()
        if not line or line.startswith("#"):
            continue
        if looks_like_id(line):
            ids.append(int(line))
        else:
            try:
                ids.append(parse_roblox_url(line)[1])
            except ValueError:
                raise click.ClickException(f"Cannot read an id from line: {line!r}")
    if not ids:
        raise click.ClickException(f"No ids found in {path}")
    return ids


# -- root ---------------------------------------------------------------------

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--cookie", "-c", envvar="ROBLOX_COOKIE", help="Your .ROBLOSECURITY cookie (unlocks a few extra endpoints).")
@click.option("--cookie-file", type=click.Path(dir_okay=False), envvar="ROBLOX_COOKIE_FILE", help="File containing the cookie.")
@click.option("--output-dir", "-o", type=click.Path(file_okay=False), envvar="ROBLOX_OUTPUT_DIR", help="Folder for output files (default: roblox_data).")
@click.option("--format", "-f", "fmt", type=click.Choice(["csv", "json"]), default="csv", show_default=True, help="Output file format.")
@click.option("--rate", type=float, envvar="ROBLOX_RATE", help="Requests per second per Roblox host (default 1).")
@click.option("--config", type=click.Path(exists=True, dir_okay=False), help="YAML or JSON settings file.")
@click.option("--stdout", is_flag=True, help="Print JSON to the terminal instead of writing files.")
@click.option("--quiet", "-q", is_flag=True, help="Only print results and errors.")
@click.option("--debug", is_flag=True, help="Show full Python tracebacks and debug logging.")
@click.version_option(__version__, prog_name="roblox")
@click.pass_context
def cli(ctx: click.Context, cookie: Optional[str], cookie_file: Optional[str],
        output_dir: Optional[str], fmt: str, rate: Optional[float], config: Optional[str],
        stdout: bool, quiet: bool, debug: bool) -> None:
    """Pull public Roblox data (users, groups, games) into CSV or JSON files.

    Examples:

    \b
      roblox user info Shedletsky
      roblox user snapshot 261
      roblox group network 7 --output-dir my_study
      roblox game info https://www.roblox.com/games/1818/Classic-Crossroads
    """
    cfg = load_config(config, cookie=cookie, cookie_file=cookie_file,
                      output_dir=output_dir, rate=rate)
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    preset = ctx.obj if isinstance(ctx.obj, dict) else {}
    client = preset.get("client") or cfg.make_client()
    ctx.obj = Runtime(config=cfg, client=client, fmt=fmt, quiet=quiet, debug=debug,
                      stdout=stdout)


# -- check / resolve ----------------------------------------------------------

@cli.command()
@click.pass_obj
@handle_errors
def check(rt: Runtime) -> None:
    """Test the connection to Roblox and whether your cookie works."""
    click.echo(f"PyRoblox {__version__}")
    click.echo(f"Output folder: {rt.output_dir.resolve()}")
    user = rt.client.users.get(1)
    click.echo(f"Roblox reachable: yes (user 1 is {user.get('name')!r})")
    if rt.client.has_cookie:
        try:
            me = rt.client.users.authenticated()
            click.echo(f"Cookie: valid, logged in as {me.get('name')!r} (id {me.get('id')})")
        except AuthRequiredError:
            click.echo("Cookie: REJECTED by Roblox. Copy a fresh .ROBLOSECURITY value.")
    elif rt.client.cookie_rejected:
        click.echo("Cookie: REJECTED by Roblox. Copy a fresh .ROBLOSECURITY value.")
    else:
        click.echo("Cookie: none (public data only; followers, badges, and group social "
                   "links need one)")
    click.echo("Everything looks good.")


@cli.command()
@click.argument("value")
@click.pass_obj
@handle_errors
def resolve(rt: Runtime, value: str) -> None:
    """Turn a link, username, or type:id into an entity type and numeric id."""
    value = value.strip()
    try:
        kind, ident = parse_roblox_url(value)
    except ValueError:
        if looks_like_id(value):
            raise click.ClickException("A bare number could be a user, group, or game id; "
                                       "give a link or a username.")
        match = rt.client.users.resolve(value)
        kind, ident = "user", int(match["id"])
        click.echo(f"user {ident} ({match.get('name')}, display name {match.get('displayName')!r})")
        return
    if kind == "game":
        universe = rt.client.games.place_to_universe(ident)
        click.echo(f"game: place {ident} belongs to universe {universe}")
        return
    click.echo(f"{kind} {ident}")


# -- user -----------------------------------------------------------------------

@cli.group()
def user() -> None:
    """Commands about one user (by id, username, or profile link)."""


def _user_cmd(name: str, help_text: str, paged: bool = True):
    """Register a ``roblox user <name>`` command. ``paged`` adds ``--max``."""
    def deco(fn: Callable[[Runtime, int, Optional[int]], Any]):
        @user.command(name=name, help=help_text)
        @click.argument("who")
        @click.pass_obj
        @handle_errors
        def command(rt: Runtime, who: str, max_items: Optional[int] = None) -> None:
            uid = resolve_user(rt, who)
            fn(rt, uid, max_items)
        if paged:
            command = click.option("--max", "max_items", type=int,
                                   help="Stop after this many rows.")(command)
        command.__name__ = f"user_{name}"
        return command
    return deco


@_user_cmd("info", "Profile: name, display name, created date, banned flag, description.", paged=False)
def user_info(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    info = rt.client.users.get(uid)
    summary = (f"{info.get('name')} (display name {info.get('displayName')!r}, id {uid})\n"
               f"  created: {info.get('created')}  banned: {info.get('isBanned')}  "
               f"verified: {info.get('hasVerifiedBadge')}")
    rt.emit(f"user_{uid}_profile", info, summary)


@_user_cmd("friends", "Friend list (ids plus usernames looked up in bulk).")
def user_friends(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    friends = rt.client.friends.friends(uid)
    if max_items:
        friends = friends[:max_items]
    friends = _hydrate_names(rt.client, friends)
    rt.emit(f"user_{uid}_friends", friends, f"{len(friends)} friend(s)")


@_user_cmd("followers", "Followers (needs a cookie).")
def user_followers(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    rows = rt.client.friends.followers(uid, max_items=max_items)
    rt.emit(f"user_{uid}_followers", rows, f"{len(rows)} follower(s)")


@_user_cmd("following", "Accounts this user follows (needs a cookie).")
def user_following(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    rows = rt.client.friends.followings(uid, max_items=max_items)
    rt.emit(f"user_{uid}_followings", rows, f"{len(rows)} followed account(s)")


@_user_cmd("counts", "Friend, follower, and following counts.", paged=False)
def user_counts(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    counts = rt.client.friends.counts(uid)
    rt.emit(f"user_{uid}_counts", counts,
            f"friends {counts['friends']}, followers {counts['followers']}, "
            f"following {counts['followings']}")


@_user_cmd("groups", "Groups the user belongs to, with their role in each.")
def user_groups(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    rows = rt.client.groups.user_groups(uid)
    if max_items:
        rows = rows[:max_items]
    rt.emit(f"user_{uid}_groups", rows, f"{len(rows)} group(s)")


@_user_cmd("games", "Experiences (games) the user has published.")
def user_games(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    rows = rt.client.games.user_games(uid, max_items=max_items)
    rt.emit(f"user_{uid}_games", rows, f"{len(rows)} game(s)")


@_user_cmd("favorites", "Experiences the user has favourited.")
def user_favorites(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    rows = rt.client.games.user_favorites(uid, max_items=max_items)
    rt.emit(f"user_{uid}_favorite_games", rows, f"{len(rows)} favourite game(s)")


@_user_cmd("badges", "Badges earned in games (needs a cookie).")
def user_badges(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    rows = rt.client.badges.user_badges(uid, max_items=max_items)
    rt.emit(f"user_{uid}_badges", rows, f"{len(rows)} badge(s)")


@_user_cmd("history", "Previous usernames.")
def user_history(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    rows = rt.client.users.username_history(uid, max_items=max_items)
    rt.emit(f"user_{uid}_username_history", rows, f"{len(rows)} previous name(s)")


@_user_cmd("avatar", "Currently worn avatar items and body settings.", paged=False)
def user_avatar(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    avatar = rt.client.avatar.get(uid)
    assets = avatar.get("assets") or []
    rt.emit(f"user_{uid}_avatar_assets", assets, f"{len(assets)} worn item(s); "
            f"avatar type {avatar.get('playerAvatarType')}")


@_user_cmd("social", "Linked social accounts (values are hidden unless you use a cookie).", paged=False)
def user_social(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    channels = rt.client.account.promotion_channels(uid)
    shown = {k: v for k, v in channels.items() if v}
    note = ", ".join(f"{k}: {v}" for k, v in shown.items()) if shown else \
        "none visible" + ("" if rt.client.has_cookie else " (add --cookie to see them)")
    rt.emit(f"user_{uid}_promotion_channels", channels, note)


@_user_cmd("presence", "Online status and last known location.", paged=False)
def user_presence(rt: Runtime, uid: int, max_items: Optional[int]) -> None:
    rows = rt.client.presence.get([uid])
    kinds = {0: "offline", 1: "online", 2: "in game", 3: "in Studio"}
    state = kinds.get((rows or [{}])[0].get("userPresenceType"), "unknown")
    rt.emit(f"user_{uid}_presence", rows, f"status: {state}")


@user.command("snapshot")
@click.argument("who")
@click.option("--only", help="Comma-separated tables to collect (default: all).")
@click.option("--skip", help="Comma-separated tables to skip.")
@click.option("--max", "max_items", type=int, help="Cap rows per paginated table.")
@click.pass_obj
@handle_errors
def user_snapshot_cmd(rt: Runtime, who: str, only: Optional[str], skip: Optional[str],
                      max_items: Optional[int]) -> None:
    """Everything public about a user, one file per table.

    Tables: profile, counts, friends, followers*, followings*, groups, games,
    favorite_games, badges*, username_history, avatar, collectibles,
    roblox_badges, promotion_channels*, presence.  (* needs a cookie)
    """
    uid = resolve_user(rt, who)
    snap = user_snapshot(rt.client, uid, include=_split_list(only) or None,
                         exclude=_split_list(skip), max_items=max_items,
                         progress=rt.progress)
    rt.emit_snapshot(snap)


@user.command("network")
@click.argument("who")
@click.option("--depth", type=int, default=1, show_default=True,
              help="1 = the user's friends; 2 = also each friend's friends.")
@click.option("--max-users", type=int, help="Stop after fetching this many friend lists.")
@click.option("--graphml", is_flag=True, help="Also write a .graphml file for Gephi.")
@click.pass_obj
@handle_errors
def user_network_cmd(rt: Runtime, who: str, depth: int, max_users: Optional[int],
                     graphml: bool) -> None:
    """Friend network edge list (source,target) plus a nodes table."""
    uid = resolve_user(rt, who)
    if depth >= 2:
        rt.say("Depth 2+ fetches one friend list per friend at ~20 per minute; "
               "large networks take a while. Use --max-users to cap it.")
    snap = friend_network(rt.client, uid, depth=depth, max_users=max_users,
                          progress=rt.progress)
    paths = rt.emit_snapshot(snap)
    if graphml and not rt.stdout:
        nodes = {n["id"]: {k: v for k, v in n.items() if k != "id"} for n in snap["nodes"]}
        path = edgelist_to_graphml(snap["edges"], rt.output_dir / f"{snap.prefix}.graphml",
                                   nodes=nodes)
        click.echo(f"GraphML: {path}")


# -- group ----------------------------------------------------------------------

@cli.group()
def group() -> None:
    """Commands about one group (by id or group link)."""


def _group_cmd(name: str, help_text: str, paged: bool = True):
    """Register a ``roblox group <name>`` command. ``paged`` adds ``--max``."""
    def deco(fn: Callable[[Runtime, int, Optional[int]], Any]):
        @group.command(name=name, help=help_text)
        @click.argument("which")
        @click.pass_obj
        @handle_errors
        def command(rt: Runtime, which: str, max_items: Optional[int] = None) -> None:
            gid = resolve_group(rt, which)
            fn(rt, gid, max_items)
        if paged:
            command = click.option("--max", "max_items", type=int,
                                   help="Stop after this many rows.")(command)
        command.__name__ = f"group_{name}"
        return command
    return deco


@_group_cmd("info", "Group profile: name, owner, member count, description.", paged=False)
def group_info(rt: Runtime, gid: int, max_items: Optional[int]) -> None:
    info = rt.client.groups.get(gid)
    owner = info.get("owner") or {}
    summary = (f"{info.get('name')} (id {gid})\n  owner: {owner.get('username')} "
               f"(id {owner.get('userId')})  members: {info.get('memberCount')}  "
               f"locked: {bool(info.get('isLocked'))}")
    rt.emit(f"group_{gid}_profile", info, summary)


@_group_cmd("members", "All members with their role. Roblox allows ~100 per second here.")
def group_members(rt: Runtime, gid: int, max_items: Optional[int]) -> None:
    rows = rt.client.groups.members(gid, max_items=max_items)
    rt.emit(f"group_{gid}_members", rows, f"{len(rows)} member(s)"
            + (" (truncated by --max)" if rows.truncated else ""))


@_group_cmd("roles", "Roles (ranks) in the group and how many members hold each.", paged=False)
def group_roles(rt: Runtime, gid: int, max_items: Optional[int]) -> None:
    rows = rt.client.groups.roles(gid)
    rt.emit(f"group_{gid}_roles", rows, f"{len(rows)} role(s)")


@_group_cmd("allies", "Allied groups.")
def group_allies(rt: Runtime, gid: int, max_items: Optional[int]) -> None:
    rows = rt.client.groups.allies(gid, max_items=max_items)
    rt.emit(f"group_{gid}_allies", rows, f"{len(rows)} ally group(s)")


@_group_cmd("enemies", "Enemy groups.")
def group_enemies(rt: Runtime, gid: int, max_items: Optional[int]) -> None:
    rows = rt.client.groups.enemies(gid, max_items=max_items)
    rt.emit(f"group_{gid}_enemies", rows, f"{len(rows)} enemy group(s)")


@_group_cmd("games", "Experiences published by the group.")
def group_games(rt: Runtime, gid: int, max_items: Optional[int]) -> None:
    rows = rt.client.games.group_games(gid, max_items=max_items)
    rt.emit(f"group_{gid}_games", rows, f"{len(rows)} game(s)")


@_group_cmd("history", "Previous group names.")
def group_history(rt: Runtime, gid: int, max_items: Optional[int]) -> None:
    rows = rt.client.groups.name_history(gid, max_items=max_items)
    rt.emit(f"group_{gid}_name_history", rows, f"{len(rows)} previous name(s)")


@_group_cmd("social", "Linked social accounts (Discord, X, YouTube...). Needs a cookie.", paged=False)
def group_social(rt: Runtime, gid: int, max_items: Optional[int]) -> None:
    rows = rt.client.groups.social_links(gid)
    rt.emit(f"group_{gid}_social_links", rows, f"{len(rows)} social link(s)")


@group.command("snapshot")
@click.argument("which")
@click.option("--only", help="Comma-separated tables to collect (default: all).")
@click.option("--skip", help="Comma-separated tables to skip.")
@click.option("--max", "max_items", type=int, help="Cap rows per paginated table (members!).")
@click.pass_obj
@handle_errors
def group_snapshot_cmd(rt: Runtime, which: str, only: Optional[str], skip: Optional[str],
                       max_items: Optional[int]) -> None:
    """Everything public about a group, one file per table.

    Tables: profile, roles, members, allies, enemies, games, name_history,
    social_links* (* needs a cookie).
    """
    gid = resolve_group(rt, which)
    snap = group_snapshot(rt.client, gid, include=_split_list(only) or None,
                          exclude=_split_list(skip), max_items=max_items,
                          progress=rt.progress)
    rt.emit_snapshot(snap)


@group.command("network")
@click.argument("which")
@click.option("--no-members", is_flag=True, help="Only map allies/enemies; skip member lists.")
@click.option("--profiles", is_flag=True, help="Also fetch every member's full profile (~30/min, slow).")
@click.option("--favorites", is_flag=True, help="Also fetch every member's favourite games (slow).")
@click.option("--max-groups", type=int, help="Expand at most this many related groups.")
@click.option("--max-members", type=int, help="Cap members fetched per group.")
@click.option("--graphml", is_flag=True, help="Also write ally/enemy .graphml files for Gephi.")
@click.pass_obj
@handle_errors
def group_network_cmd(rt: Runtime, which: str, no_members: bool, profiles: bool,
                      favorites: bool, max_groups: Optional[int],
                      max_members: Optional[int], graphml: bool) -> None:
    """Ally/enemy network one step out, plus membership of every group in it.

    This is the v1 "build_dataframes" collection with its bugs fixed. Tables:
    groups, allies, enemies, membership, members, and optionally
    member_profiles, favorite_games, games.
    """
    gid = resolve_group(rt, which)
    snap = group_network(rt.client, gid, include_members=not no_members,
                         include_member_profiles=profiles, include_favorites=favorites,
                         max_groups=max_groups, max_members=max_members,
                         progress=rt.progress)
    rt.emit_snapshot(snap)
    if graphml and not rt.stdout:
        nodes = {g["id"]: {"name": g.get("name"), "memberCount": g.get("memberCount")}
                 for g in snap["groups"]}
        for table in ("allies", "enemies"):
            path = edgelist_to_graphml(snap[table], rt.output_dir / f"{snap.prefix}_{table}.graphml",
                                       nodes=nodes, directed=True)
            click.echo(f"GraphML: {path}")


# -- game -----------------------------------------------------------------------

@cli.group()
def game() -> None:
    """Commands about one experience (universe id, or a games link / --place)."""


def _game_cmd(name: str, help_text: str, paged: bool = True):
    """Register a ``roblox game <name>`` command. ``paged`` adds ``--max``."""
    def deco(fn: Callable[[Runtime, int, Optional[int]], Any]):
        @game.command(name=name, help=help_text)
        @click.argument("which")
        @click.option("--place", is_flag=True, help="WHICH is a place id, not a universe id.")
        @click.pass_obj
        @handle_errors
        def command(rt: Runtime, which: str, place: bool, max_items: Optional[int] = None) -> None:
            universe = resolve_universe(rt, which, place)
            fn(rt, universe, max_items)
        if paged:
            command = click.option("--max", "max_items", type=int,
                                   help="Stop after this many rows.")(command)
        command.__name__ = f"game_{name}"
        return command
    return deco


@_game_cmd("info", "Experience profile: creator, visits, players online, created date.", paged=False)
def game_info(rt: Runtime, universe: int, max_items: Optional[int]) -> None:
    info = rt.client.games.get(universe)
    creator = info.get("creator") or {}
    summary = (f"{info.get('name')} (universe {universe}, root place {info.get('rootPlaceId')})\n"
               f"  creator: {creator.get('name')} ({creator.get('type')} {creator.get('id')})  "
               f"visits: {info.get('visits')}  playing now: {info.get('playing')}")
    rt.emit(f"game_{universe}_profile", info, summary)


@_game_cmd("votes", "Up/down votes and favourite count.", paged=False)
def game_votes(rt: Runtime, universe: int, max_items: Optional[int]) -> None:
    votes = dict(rt.client.games.votes(universe))
    votes["favoritesCount"] = rt.client.games.favorites_count(universe)
    rt.emit(f"game_{universe}_votes", votes,
            f"up {votes.get('upVotes')}  down {votes.get('downVotes')}  "
            f"favourites {votes['favoritesCount']}")


@_game_cmd("servers", "Public servers running right now (~3 calls/min allowed).")
def game_servers(rt: Runtime, universe: int, max_items: Optional[int]) -> None:
    info = rt.client.games.get(universe)
    rows = rt.client.games.servers(info["rootPlaceId"], max_items=max_items or 100)
    rt.emit(f"game_{universe}_servers", rows, f"{len(rows)} server(s)")


@_game_cmd("badges", "Badges the experience awards.")
def game_badges(rt: Runtime, universe: int, max_items: Optional[int]) -> None:
    rows = rt.client.badges.universe_badges(universe, max_items=max_items)
    rt.emit(f"game_{universe}_badges", rows, f"{len(rows)} badge(s)")


@_game_cmd("passes", "Game passes offered by the experience (for sale or not).", paged=False)
def game_passes(rt: Runtime, universe: int, max_items: Optional[int]) -> None:
    rows = rt.client.games.game_passes(universe)
    rt.emit(f"game_{universe}_game_passes", rows, f"{len(rows)} game pass(es)")


@_game_cmd("places", "All places inside the experience.")
def game_places(rt: Runtime, universe: int, max_items: Optional[int]) -> None:
    rows = rt.client.games.places(universe, max_items=max_items)
    rt.emit(f"game_{universe}_places", rows, f"{len(rows)} place(s)")


@game.command("snapshot")
@click.argument("which")
@click.option("--place", is_flag=True, help="WHICH is a place id, not a universe id.")
@click.option("--only", help="Comma-separated tables to collect (default: all).")
@click.option("--skip", help="Comma-separated tables to skip.")
@click.option("--max-servers", type=int, default=100, show_default=True,
              help="Cap the servers table (Roblox allows ~3 server calls per minute).")
@click.pass_obj
@handle_errors
def game_snapshot_cmd(rt: Runtime, which: str, place: bool, only: Optional[str],
                      skip: Optional[str], max_servers: int) -> None:
    """Everything public about an experience, one file per table.

    Tables: profile, votes, places, servers, badges, media, game_passes.
    """
    universe = resolve_universe(rt, which, place)
    snap = game_snapshot(rt.client, universe, include=_split_list(only) or None,
                         exclude=_split_list(skip), max_servers=max_servers,
                         progress=rt.progress)
    rt.emit_snapshot(snap)


# -- search / batch -------------------------------------------------------------

@cli.group()
def search() -> None:
    """Find users or groups by keyword."""


@search.command("users")
@click.argument("keyword")
@click.option("--max", "max_items", type=int, default=100, show_default=True)
@click.pass_obj
@handle_errors
def search_users(rt: Runtime, keyword: str, max_items: int) -> None:
    """Search usernames (Roblox allows about one search per minute)."""
    rows = rt.client.users.search(keyword, max_items=max_items)
    rt.emit(f"search_users_{_slug(keyword)}", rows, f"{len(rows)} result(s)")


@search.command("groups")
@click.argument("keyword")
@click.option("--max", "max_items", type=int, default=100, show_default=True)
@click.pass_obj
@handle_errors
def search_groups(rt: Runtime, keyword: str, max_items: int) -> None:
    """Search group names."""
    rows = rt.client.groups.search(keyword, max_items=max_items)
    rt.emit(f"search_groups_{_slug(keyword)}", rows, f"{len(rows)} result(s)")


@cli.group()
def batch() -> None:
    """Look up many ids at once from a text file (one id or link per line)."""


@batch.command("users")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--full", is_flag=True, help="Fetch full profiles one by one (~30/min) instead of the fast batch lookup.")
@click.pass_obj
@handle_errors
def batch_users(rt: Runtime, file: str, full: bool) -> None:
    """Usernames (and, with --full, profiles) for a list of user ids."""
    ids = _read_ids(file)
    if full:
        rows = []
        for i, uid in enumerate(ids, 1):
            rt.progress(f"profile {i}/{len(ids)}: user {uid}")
            try:
                rows.append(rt.client.users.get(uid))
            except (NotFoundError, BadRequestError) as e:
                rows.append({"id": uid, "error": e.roblox_message or type(e).__name__})
    else:
        rows = rt.client.users.batch_get(ids)
    rt.emit(f"batch_users_{Path(file).stem}", rows, f"{len(rows)} of {len(ids)} found")


@batch.command("groups")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.pass_obj
@handle_errors
def batch_groups(rt: Runtime, file: str) -> None:
    """Basic profiles for a list of group ids."""
    ids = _read_ids(file)
    rows = rt.client.groups.batch_get(ids)
    rt.emit(f"batch_groups_{Path(file).stem}", rows, f"{len(rows)} of {len(ids)} found")


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.strip())[:40] or "query"


def main() -> None:
    """Console-script entry point."""
    cli(obj={})


if __name__ == "__main__":  # pragma: no cover
    main()
