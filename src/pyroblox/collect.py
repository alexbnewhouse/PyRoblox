"""High-level collectors: everything about one user, group, or game in one call.

Each collector returns a :class:`~pyroblox.export.Snapshot` whose tables can
be saved as CSV files with ``snapshot.save("some_folder")``. Collection is
best-effort: the primary lookup (the user, group, or game itself) must succeed,
but every secondary table that Roblox refuses (private, cookie-only, deleted)
is recorded under ``snapshot.meta["omitted"]`` and collection carries on. Rate
limit and Roblox server errors are not swallowed; they propagate so that you
never end up with a silently half-empty dataset.

The network collectors build edge lists for social network analysis:

* :func:`friend_network` walks friend lists out to ``depth`` hops.
* :func:`group_network` maps a group's allies and enemies (one step out) plus,
  optionally, the membership of every group in that neighbourhood.

The three functions at the bottom (:func:`build_dataframes`,
:func:`group_edgelist`, :func:`friend_edgelist`) keep the v1 names and output
files so existing scripts keep working, with the v1 bugs fixed.
"""

from __future__ import annotations

import logging
from typing import (Any, Callable, Dict, Iterable, List, Optional, Sequence, Set,
                    Tuple, Union)

from .client import PagedList, RobloxClient
from .errors import (
    AuthRequiredError,
    BadRequestError,
    EntityUnavailable,
    NotFoundError,
    PrivateError,
    RateLimitedError,
    RobloxError,
    ServerError,
)
from .export import Snapshot
from .models.base import to_record, to_records

log = logging.getLogger("pyroblox.collect")

ProgressFn = Callable[[str], None]

USER_TABLES: Tuple[str, ...] = (
    "profile", "counts", "friends", "followers", "followings", "groups", "games",
    "favorite_games", "badges", "username_history", "avatar", "collectibles",
    "roblox_badges", "promotion_channels", "presence",
)
GROUP_TABLES: Tuple[str, ...] = (
    "profile", "roles", "members", "allies", "enemies", "games", "name_history",
    "social_links",
)
GAME_TABLES: Tuple[str, ...] = (
    "profile", "votes", "places", "servers", "badges", "media", "game_passes",
)

#: Tables that only work with a .ROBLOSECURITY cookie (as of 2026-09).
COOKIE_ONLY_TABLES = frozenset({"followers", "followings", "badges", "social_links"})

_OMITTED = object()


# -- helpers --------------------------------------------------------------------

def _plain(value: Any) -> Any:
    """Turn API results (models, lists of models, PagedList of models) into plain
    dicts so the collectors can work with Roblox's own key names. A PagedList
    keeps its ``truncated`` flag."""
    if isinstance(value, PagedList):
        return PagedList(to_records(value), value.truncated)
    return to_record(value)


def _say(progress: Optional[ProgressFn], message: str) -> None:
    if progress:
        progress(message)
    else:
        log.info(message)


def _select(all_tables: Sequence[str], include: Optional[Iterable[str]],
            exclude: Iterable[str]) -> List[str]:
    wanted = list(all_tables) if include is None else list(include)
    unknown = [t for t in list(wanted) + list(exclude) if t not in all_tables]
    if unknown:
        raise ValueError(f"unknown table(s) {unknown}; valid names: {list(all_tables)}")
    excluded = set(exclude)
    return [t for t in all_tables if t in wanted and t not in excluded]


def _primary(entity: str, fn: Callable[..., Any], *args: Any) -> Any:
    """Run the primary lookup; translate failures into :class:`EntityUnavailable`."""
    try:
        return _plain(fn(*args))
    except NotFoundError as e:
        raise EntityUnavailable("not-found", f"{entity} does not exist or was deleted") from e
    except PrivateError as e:
        raise EntityUnavailable("private", f"{entity} is private or hidden") from e
    except BadRequestError as e:
        raise EntityUnavailable("invalid", f"{entity} rejected by Roblox: "
                                f"{e.roblox_message or e}") from e


def _attempt(snapshot: Snapshot, name: str, fn: Callable[..., Any], *args: Any,
             **kwargs: Any) -> Any:
    """Run a secondary lookup. 4xx outcomes are recorded as omissions and return
    the ``_OMITTED`` sentinel; rate-limit and server errors propagate."""
    try:
        return _plain(fn(*args, **kwargs))
    except (RateLimitedError, ServerError):
        raise
    except AuthRequiredError:
        snapshot.omit(name, "cookie-required")
    except PrivateError:
        snapshot.omit(name, "private")
    except NotFoundError:
        snapshot.omit(name, "not-found")
    except BadRequestError as e:
        snapshot.omit(name, "invalid")
        snapshot.record_error(name, e)
    except RobloxError as e:
        snapshot.omit(name, "error")
        snapshot.record_error(name, e)
    return _OMITTED


def _add(snapshot: Snapshot, name: str, result: Any) -> bool:
    """Add ``result`` unless it was omitted. Marks truncation for PagedList."""
    if result is _OMITTED:
        return False
    snapshot.add(name, result)
    if isinstance(result, PagedList) and result.truncated:
        snapshot.mark_truncated(name)
    return True


def _hydrate_names(client: RobloxClient, records: List[dict],
                   id_key: str = "id") -> List[dict]:
    """Fill in blank ``name`` / ``displayName`` fields via the batch users endpoint."""
    missing = [r[id_key] for r in records
               if isinstance(r, dict) and r.get(id_key) is not None and not r.get("name")]
    if not missing:
        return records
    lookup = {u["id"]: u for u in to_records(client.users.get_batch(missing))}
    out = []
    for r in records:
        info = lookup.get(r.get(id_key)) if isinstance(r, dict) else None
        if info:
            r = dict(r)
            r.setdefault("name", None)
            r["name"] = info.get("name") or r.get("name")
            r["displayName"] = info.get("displayName") or r.get("displayName")
            if "hasVerifiedBadge" in info:
                r["hasVerifiedBadge"] = info["hasVerifiedBadge"]
        out.append(r)
    return out


# -- single-entity snapshots -----------------------------------------------------

def user_snapshot(client: RobloxClient, user_id: int, *,
                  include: Optional[Iterable[str]] = None,
                  exclude: Iterable[str] = (),
                  max_items: Optional[int] = None,
                  hydrate_names: bool = True,
                  progress: Optional[ProgressFn] = None) -> Snapshot:
    """Collect everything public about one user.

    Tables (see :data:`USER_TABLES`): ``profile``, ``counts``, ``friends``,
    ``followers`` (cookie), ``followings`` (cookie), ``groups``, ``games``,
    ``favorite_games``, ``badges`` (cookie), ``username_history``, ``avatar`` (also
    writes ``avatar_assets``), ``collectibles``, ``roblox_badges``,
    ``promotion_channels`` (values null without a cookie), ``presence``.

    Raises :class:`EntityUnavailable` if the user itself cannot be fetched.
    """
    tables = _select(USER_TABLES, include, exclude)
    snap = Snapshot("user", user_id)
    _say(progress, f"user {user_id}: profile")
    profile = _primary(f"user {user_id}", client.users.get_info, user_id)
    snap.add("profile", profile)

    if "counts" in tables:
        _say(progress, f"user {user_id}: friend/follower counts")
        _add(snap, "counts", _attempt(snap, "counts", client.friends.get_counts, user_id))
    if "friends" in tables:
        _say(progress, f"user {user_id}: friends")
        friends = _attempt(snap, "friends", client.friends.get_friends, user_id)
        if friends is not _OMITTED and hydrate_names:
            friends = _attempt(snap, "friends", _hydrate_names, client, friends)
        _add(snap, "friends", friends)
    if "followers" in tables:
        _say(progress, f"user {user_id}: followers")
        _add(snap, "followers", _attempt(snap, "followers", client.friends.get_followers,
                                         user_id, max_items=max_items))
    if "followings" in tables:
        _say(progress, f"user {user_id}: followings")
        _add(snap, "followings", _attempt(snap, "followings", client.friends.get_followings,
                                          user_id, max_items=max_items))
    if "groups" in tables:
        _say(progress, f"user {user_id}: groups")
        _add(snap, "groups", _attempt(snap, "groups", client.groups.get_user_groups, user_id))
    if "games" in tables:
        _say(progress, f"user {user_id}: created games")
        _add(snap, "games", _attempt(snap, "games", client.games.get_user_games,
                                     user_id, max_items=max_items))
    if "favorite_games" in tables:
        _say(progress, f"user {user_id}: favorite games")
        _add(snap, "favorite_games", _attempt(snap, "favorite_games",
                                              client.games.get_user_favorites,
                                              user_id, max_items=max_items))
    if "badges" in tables:
        _say(progress, f"user {user_id}: badges")
        _add(snap, "badges", _attempt(snap, "badges", client.badges.get_user_badges,
                                      user_id, max_items=max_items))
    if "username_history" in tables:
        _say(progress, f"user {user_id}: username history")
        _add(snap, "username_history", _attempt(snap, "username_history",
                                                client.users.get_username_history,
                                                user_id, max_items=max_items))
    if "avatar" in tables:
        _say(progress, f"user {user_id}: avatar")
        avatar = _attempt(snap, "avatar", client.avatar.get_avatar, user_id)
        if avatar is not _OMITTED:
            assets = avatar.get("assets") or []
            snap.add("avatar", {k: v for k, v in avatar.items() if k != "assets"})
            snap.add("avatar_assets", assets)
    if "collectibles" in tables:
        _say(progress, f"user {user_id}: collectibles")
        _add(snap, "collectibles", _attempt(snap, "collectibles",
                                            client.inventory.get_collectibles,
                                            user_id, max_items=max_items))
    if "roblox_badges" in tables:
        _say(progress, f"user {user_id}: Roblox badges")
        _add(snap, "roblox_badges", _attempt(snap, "roblox_badges",
                                             client.account.get_roblox_badges, user_id))
    if "promotion_channels" in tables:
        _say(progress, f"user {user_id}: promotion channels")
        channels = _attempt(snap, "promotion_channels",
                            client.account.get_promotion_channels, user_id)
        if channels is not _OMITTED:
            if not client.has_cookie and not any(channels.values()):
                snap.omit("promotion_channels", "cookie-required")
            snap.add("promotion_channels", channels)
    if "presence" in tables:
        _say(progress, f"user {user_id}: presence")
        _add(snap, "presence", _attempt(snap, "presence", client.presence.get_presence, [user_id]))
    return snap


def group_snapshot(client: RobloxClient, group_id: int, *,
                   include: Optional[Iterable[str]] = None,
                   exclude: Iterable[str] = (),
                   max_items: Optional[int] = None,
                   progress: Optional[ProgressFn] = None) -> Snapshot:
    """Collect everything public about one group.

    Tables (see :data:`GROUP_TABLES`): ``profile``, ``roles``, ``members``,
    ``allies``, ``enemies``, ``games``, ``name_history``, ``social_links`` (cookie).
    ``max_items`` caps the paginated tables (members in particular).
    """
    tables = _select(GROUP_TABLES, include, exclude)
    snap = Snapshot("group", group_id)
    _say(progress, f"group {group_id}: profile")
    profile = _primary(f"group {group_id}", client.groups.get_info, group_id)
    snap.add("profile", profile)

    if "roles" in tables:
        _say(progress, f"group {group_id}: roles")
        _add(snap, "roles", _attempt(snap, "roles", client.groups.get_roles, group_id))
    if "members" in tables:
        _say(progress, f"group {group_id}: members ({profile.get('memberCount', '?')} total)")
        _add(snap, "members", _attempt(snap, "members", client.groups.get_members,
                                       group_id, max_items=max_items))
    if "allies" in tables:
        _say(progress, f"group {group_id}: allies")
        _add(snap, "allies", _attempt(snap, "allies", client.groups.get_allies,
                                      group_id, max_items=max_items))
    if "enemies" in tables:
        _say(progress, f"group {group_id}: enemies")
        _add(snap, "enemies", _attempt(snap, "enemies", client.groups.get_enemies,
                                       group_id, max_items=max_items))
    if "games" in tables:
        _say(progress, f"group {group_id}: games")
        _add(snap, "games", _attempt(snap, "games", client.games.get_group_games,
                                     group_id, max_items=max_items))
    if "name_history" in tables:
        _say(progress, f"group {group_id}: name history")
        _add(snap, "name_history", _attempt(snap, "name_history",
                                            client.groups.get_name_history,
                                            group_id, max_items=max_items))
    if "social_links" in tables:
        _say(progress, f"group {group_id}: social links")
        _add(snap, "social_links", _attempt(snap, "social_links",
                                            client.groups.get_social_links, group_id))
    return snap


def game_snapshot(client: RobloxClient, game_id: int, *, by_place: bool = False,
                  include: Optional[Iterable[str]] = None,
                  exclude: Iterable[str] = (),
                  max_servers: Optional[int] = 100,
                  max_items: Optional[int] = None,
                  progress: Optional[ProgressFn] = None) -> Snapshot:
    """Collect everything public about one experience (game).

    ``game_id`` is a universe id unless ``by_place=True``, in which case it is the
    place id from a ``roblox.com/games/<id>`` link and is resolved first.
    Tables (see :data:`GAME_TABLES`): ``profile``, ``votes``, ``places``,
    ``servers`` (capped by ``max_servers``; Roblox allows ~3 calls/min here),
    ``badges``, ``media``, ``game_passes``.
    """
    tables = _select(GAME_TABLES, include, exclude)
    if by_place:
        _say(progress, f"place {game_id}: resolving universe")
        universe_id = _primary(f"place {game_id}", client.games.get_universe_id, game_id)
    else:
        universe_id = game_id
    snap = Snapshot("game", universe_id)
    _say(progress, f"game {universe_id}: profile")
    profile = _primary(f"game {universe_id}", client.games.get_info, universe_id)
    snap.add("profile", profile)
    root_place = profile.get("rootPlaceId")
    snap.meta["root_place_id"] = root_place
    if by_place:
        snap.meta["place_id"] = game_id

    if "votes" in tables:
        _say(progress, f"game {universe_id}: votes")
        votes = _attempt(snap, "votes", client.games.get_votes, universe_id)
        if votes is not _OMITTED:
            votes = dict(votes)
            fav = _attempt(snap, "votes", client.games.get_favorites_count, universe_id)
            if fav is not _OMITTED:
                votes["favoritesCount"] = fav
            snap.add("votes", votes)
    if "places" in tables:
        _say(progress, f"game {universe_id}: places")
        _add(snap, "places", _attempt(snap, "places", client.games.get_places,
                                      universe_id, max_items=max_items))
    if "servers" in tables:
        if root_place is None:
            snap.omit("servers", "no-root-place")
        else:
            _say(progress, f"game {universe_id}: public servers")
            _add(snap, "servers", _attempt(snap, "servers", client.games.get_servers,
                                           root_place, max_items=max_servers))
    if "badges" in tables:
        _say(progress, f"game {universe_id}: badges")
        _add(snap, "badges", _attempt(snap, "badges", client.badges.get_universe_badges,
                                      universe_id, max_items=max_items))
    if "media" in tables:
        _say(progress, f"game {universe_id}: media")
        _add(snap, "media", _attempt(snap, "media", client.games.get_media, universe_id))
    if "game_passes" in tables:
        _say(progress, f"game {universe_id}: game passes")
        _add(snap, "game_passes", _attempt(snap, "game_passes",
                                           client.games.get_game_passes, universe_id))
    return snap


# -- networks -------------------------------------------------------------------

def friend_network(client: RobloxClient, user_id: int, *, depth: int = 1,
                   max_users: Optional[int] = None, hydrate_names: bool = True,
                   progress: Optional[ProgressFn] = None) -> Snapshot:
    """Walk friend lists outward from ``user_id``.

    ``depth`` is how many hops of friend lists are fetched: 1 fetches the seed
    user's friends; 2 also fetches each friend's friends; and so on. Roblox
    allows about 20 friend-list calls per minute unauthenticated, so depth 2 on a
    user with 200 friends takes roughly ten minutes. ``max_users`` caps how many
    friend lists are fetched in total.

    Returns a snapshot with tables ``edges`` (``source``, ``target``, undirected,
    deduplicated), ``nodes`` (``id``, ``name``, ``displayName``,
    ``hasVerifiedBadge``, ``depth``, ``expanded``), and ``meta["failed"]`` listing
    users whose friend lists could not be fetched. Roblox reports deleted or hidden
    friends with id ``-1``; those are counted in ``meta["hidden_friends_skipped"]``
    rather than added to the graph.
    """
    if depth < 1:
        raise ValueError("depth must be at least 1")
    snap = Snapshot("friend_network", user_id)
    snap.meta.update({"depth": depth, "failed": {}, "hidden_friends_skipped": 0})
    node_depth: Dict[int, int] = {user_id: 0}
    expanded: Set[int] = set()
    edges: Set[Tuple[int, int]] = set()
    frontier: List[int] = [user_id]
    fetched = 0
    for hop in range(depth):
        next_frontier: List[int] = []
        for uid in frontier:
            if max_users is not None and fetched >= max_users:
                snap.mark_truncated("edges")
                break
            _say(progress, f"friend network: hop {hop + 1}, user {uid} "
                           f"({fetched + 1} lists fetched)")
            try:
                friends = to_records(client.friends.get_friends(uid))
            except (RateLimitedError, ServerError):
                raise
            except RobloxError as e:
                snap.meta["failed"][uid] = f"{type(e).__name__}: {e.roblox_message or e}"
                fetched += 1
                continue
            fetched += 1
            expanded.add(uid)
            for f in friends:
                fid = f.get("id")
                if not isinstance(fid, int) or fid <= 0:
                    # Roblox lists deleted/hidden friends as id -1; not a real node.
                    snap.meta["hidden_friends_skipped"] += 1
                    continue
                edges.add((min(uid, fid), max(uid, fid)))
                if fid not in node_depth:
                    node_depth[fid] = hop + 1
                    next_frontier.append(fid)
        else:
            frontier = next_frontier
            continue
        break
    snap.add("edges", [{"source": a, "target": b} for a, b in sorted(edges)])
    nodes = [{"id": nid, "name": None, "displayName": None, "depth": d,
              "expanded": nid in expanded} for nid, d in node_depth.items()]
    if hydrate_names and nodes:
        _say(progress, f"friend network: looking up {len(nodes)} usernames")
        nodes = _attempt(snap, "nodes", _hydrate_names, client, nodes)
        if nodes is _OMITTED:
            nodes = [{"id": nid, "depth": d, "expanded": nid in expanded}
                     for nid, d in node_depth.items()]
    snap.add("nodes", nodes)
    return snap


def group_network(client: RobloxClient, group_id: int, *,
                  include_members: bool = True,
                  include_member_profiles: bool = False,
                  include_favorites: bool = False,
                  max_groups: Optional[int] = None,
                  max_members: Optional[int] = None,
                  progress: Optional[ProgressFn] = None) -> Snapshot:
    """Map a group's ally/enemy neighbourhood and, optionally, who is in it.

    Steps:

    1. Fetch the seed group's allies and enemies.
    2. For each of those groups (up to ``max_groups``), fetch *their* allies and
       enemies, producing a one-step-out edge list.
    3. With ``include_members`` (default), fetch the member list of the seed group
       and every group found in step 1 (each capped at ``max_members``).
    4. With ``include_member_profiles``, fetch the full profile of every unique
       member (about 30 calls/min, so slow for big groups).
    5. With ``include_favorites``, fetch every unique member's favourite games
       (one call per member).

    Tables: ``groups`` (profile of every group seen), ``allies`` and ``enemies``
    (``source``, ``target`` edges), ``membership`` (``groupId`` + user + role),
    ``members`` (unique users), ``member_profiles``, ``favorite_games``
    (``userId``, ``universeId`` edges), and ``games`` (profiles of favourited games).
    """
    snap = Snapshot("group_network", group_id)
    snap.meta["failed"] = {}
    _say(progress, f"group network: seed group {group_id}")
    seed = _primary(f"group {group_id}", client.groups.get_info, group_id)
    groups: Dict[int, dict] = {group_id: seed}
    ally_edges: Set[Tuple[int, int]] = set()
    enemy_edges: Set[Tuple[int, int]] = set()

    def relationships(gid: int) -> Tuple[List[dict], List[dict]]:
        allies = _attempt(snap, "allies", client.groups.get_allies, gid)
        enemies = _attempt(snap, "enemies", client.groups.get_enemies, gid)
        if allies is _OMITTED or enemies is _OMITTED:
            snap.meta["failed"][gid] = "relationships unavailable (locked or deleted group)"
            snap.meta["omitted"].pop("allies", None)
            snap.meta["omitted"].pop("enemies", None)
        return ([] if allies is _OMITTED else list(allies),
                [] if enemies is _OMITTED else list(enemies))

    seed_allies, seed_enemies = relationships(group_id)
    for g in seed_allies:
        groups.setdefault(g["id"], g)
        ally_edges.add((group_id, g["id"]))
    for g in seed_enemies:
        groups.setdefault(g["id"], g)
        enemy_edges.add((group_id, g["id"]))

    neighbours = [gid for gid in groups if gid != group_id]
    if max_groups is not None and len(neighbours) > max_groups:
        neighbours = neighbours[:max_groups]
        snap.mark_truncated("groups")
    for i, gid in enumerate(neighbours, 1):
        _say(progress, f"group network: relationships of group {gid} ({i}/{len(neighbours)})")
        allies, enemies = relationships(gid)
        for g in allies:
            groups.setdefault(g["id"], g)
            ally_edges.add((gid, g["id"]))
        for g in enemies:
            groups.setdefault(g["id"], g)
            enemy_edges.add((gid, g["id"]))

    snap.add("groups", list(groups.values()))
    snap.add("allies", [{"source": a, "target": b} for a, b in sorted(ally_edges)])
    snap.add("enemies", [{"source": a, "target": b} for a, b in sorted(enemy_edges)])

    if not include_members:
        return snap

    membership: List[dict] = []
    users: Dict[int, dict] = {}
    member_groups = [group_id] + neighbours
    for i, gid in enumerate(member_groups, 1):
        _say(progress, f"group network: members of group {gid} ({i}/{len(member_groups)})")
        rows = _attempt(snap, "membership", client.groups.get_members, gid, max_items=max_members)
        if rows is _OMITTED:
            snap.meta["failed"][gid] = "members unavailable"
            snap.meta["omitted"].pop("membership", None)
            continue
        if rows.truncated:
            snap.mark_truncated("membership")
        for row in rows:
            record = {"groupId": gid}
            record.update(row)
            membership.append(record)
            user = row.get("user") or {}
            uid = user.get("userId")
            if uid is not None:
                users.setdefault(uid, {"id": uid, "name": user.get("username"),
                                       "displayName": user.get("displayName"),
                                       "hasVerifiedBadge": user.get("hasVerifiedBadge")})
    snap.add("membership", membership)
    snap.add("members", list(users.values()))

    if include_member_profiles:
        profiles: List[dict] = []
        for i, uid in enumerate(users, 1):
            if i == 1 or i % 25 == 0:
                _say(progress, f"group network: member profiles ({i}/{len(users)})")
            prof = _attempt(snap, "member_profiles", client.users.get_info, uid)
            if prof is not _OMITTED:
                profiles.append(prof)
            else:
                snap.meta["omitted"].pop("member_profiles", None)
                snap.meta["failed"][uid] = "profile unavailable"
        snap.add("member_profiles", profiles)

    if include_favorites:
        fav_edges: List[dict] = []
        games: Dict[int, dict] = {}
        for i, uid in enumerate(users, 1):
            if i == 1 or i % 25 == 0:
                _say(progress, f"group network: favourite games ({i}/{len(users)})")
            favs = _attempt(snap, "favorite_games", client.games.get_user_favorites, uid)
            if favs is _OMITTED:
                snap.meta["omitted"].pop("favorite_games", None)
                snap.meta["failed"][uid] = "favorites unavailable"
                continue
            for g in favs:
                fav_edges.append({"userId": uid, "universeId": g["id"]})
                games.setdefault(g["id"], g)
        snap.add("favorite_games", fav_edges)
        snap.add("games", list(games.values()))
    return snap


# -- v1 compatibility -------------------------------------------------------------

def _client_from(client: Optional[RobloxClient], cookie: Union[str, dict, None]) -> RobloxClient:
    if client is not None:
        return client
    if isinstance(cookie, dict):
        cookie = cookie.get(".ROBLOSECURITY")
    from .config import load_config
    return load_config(cookie=cookie).make_client()


def group_edgelist(group_id: int, client: Optional[RobloxClient] = None) -> Dict[str, List[List[int]]]:
    """v1-compatible: ``{"allies": [[from, to], ...], "enemies": [[from, to], ...]}``
    for the seed group and each of its allies/enemies (one step out)."""
    snap = group_network(_client_from(client, None), group_id, include_members=False)
    return {
        "allies": [[e["source"], e["target"]] for e in snap["allies"]],
        "enemies": [[e["source"], e["target"]] for e in snap["enemies"]],
    }


def friend_edgelist(user_id: int, client: Optional[RobloxClient] = None) -> List[List[int]]:
    """v1-compatible: ``[[from, to], ...]`` for the user's friends and their friends."""
    snap = friend_network(_client_from(client, None), user_id, depth=2, hydrate_names=False)
    return [[e["source"], e["target"]] for e in snap["edges"]]


def build_dataframes(group_id: int, cookie: Union[str, dict, None] = None,
                     output_dir: str = ".", client: Optional[RobloxClient] = None,
                     include_favorites: bool = True,
                     progress: Optional[ProgressFn] = None) -> Dict[str, Any]:
    """v1-compatible "master function": write the seven v1 CSVs for a group.

    Files written to ``output_dir`` (same names as v1):
    ``allies_<id>_edgelist.csv``, ``enemies_<id>_edgelist.csv``, ``group_info_<id>.csv``,
    ``membership_<id>_edgelist.csv``, ``user_info_membership_<id>.csv``,
    ``asset_el<id>.csv``, ``asset_info_<id>.csv``.

    Differences from v1: every group's own members are collected (v1 wrote the
    seed group's members for every group), the favourite-game edge list is
    complete (v1 wrote the wrong variable and stopped after two pages), a cookie
    is optional, and the function returns the DataFrames instead of ``None``.
    """
    from pathlib import Path

    import pandas as pd

    from .export import to_dataframe

    rc = _client_from(client, cookie)
    snap = group_network(rc, group_id, include_members=True,
                         include_member_profiles=True,
                         include_favorites=include_favorites, progress=progress)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    allies = pd.DataFrame([[e["source"], e["target"]] for e in snap["allies"]],
                          columns=["From", "To"])
    enemies = pd.DataFrame([[e["source"], e["target"]] for e in snap["enemies"]],
                           columns=["From", "To"])
    group_info = to_dataframe(snap["groups"])
    membership = pd.DataFrame([[m["groupId"], (m.get("user") or {}).get("userId")]
                               for m in snap["membership"]], columns=["Group", "User"])
    user_info = to_dataframe(snap.get("member_profiles") or snap["members"])
    favorites = pd.DataFrame([[e["userId"], e["universeId"]] for e in snap.get("favorite_games", [])],
                             columns=["User", "FavoritedGame"])
    games = to_dataframe(snap.get("games", []))

    frames = {
        "allies": allies, "enemies": enemies, "group_info": group_info,
        "membership": membership, "user_info": user_info,
        "asset_el": favorites, "asset_info": games,
    }
    allies.to_csv(out / f"allies_{group_id}_edgelist.csv", index=False)
    enemies.to_csv(out / f"enemies_{group_id}_edgelist.csv", index=False)
    group_info.to_csv(out / f"group_info_{group_id}.csv", index=False)
    membership.to_csv(out / f"membership_{group_id}_edgelist.csv", index=False)
    user_info.to_csv(out / f"user_info_membership_{group_id}.csv", index=False)
    favorites.to_csv(out / f"asset_el{group_id}.csv", index=False)
    games.to_csv(out / f"asset_info_{group_id}.csv", index=False)
    frames["snapshot"] = snap
    return frames
