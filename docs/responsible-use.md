# Responsible use

PyRoblox is a research tool. This page sets out what it does and does not do,
and what you owe the people whose data you collect.

## What the tool does

PyRoblox reads endpoints that Roblox exposes to the public web. Every value it
returns can be seen by anyone who opens the matching roblox.com page in a
browser without logging in, with the exceptions listed under "Cookie" below. It
never performs an action on Roblox: no friend requests, no messages, no joins, no
purchases, no reports. It sends a GET or a read-only POST and records the answer.

It identifies itself with a `PyRoblox/2.0` user agent that links to this
repository, so Roblox can see who is asking and can contact the maintainers.

## Rate limits

Roblox limits how often each endpoint may be called from one IP address. The
limits are listed in [roblox-endpoints.md](roblox-endpoints.md). PyRoblox reads
Roblox's rate-limit headers, pauses when a quota is used up, honours
`Retry-After`, and stops with a clear error if Roblox keeps refusing. Leave those
mechanisms alone. In particular:

- Do not run many copies of a collection in parallel, on several machines, or
  through rotating proxies to get more requests per minute. That is evasion of a
  limit Roblox has set deliberately, and it is the behaviour that gets research
  IP ranges blocked for everyone.
- Do not lower the wait times in the client. The defaults are conservative on
  purpose.
- Prefer the batch endpoints (`batch_get`, `batch users`) over per-id lookups.
  They are hundreds of times cheaper for Roblox and for you.

## Terms of use

Roblox's Terms of Use govern your access to the platform, including access
through its web APIs. Read them before you start a study, and read them again
when they change. In outline they prohibit interfering with the service,
circumventing access controls, and harvesting data for uses Roblox has not
sanctioned. Public safety research that reads public pages at a polite rate
sits comfortably within what many platforms tolerate, but PyRoblox's authors
cannot give you legal advice, and the responsibility for complying is yours.

- Roblox Terms of Use: https://en.help.roblox.com/hc/en-us/articles/115004647846
- Roblox developer documentation, including the legacy web APIs this tool uses:
  https://create.roblox.com/docs/cloud

## People, not rows

Most Roblox users are under 18, and a large share are under 13. A user snapshot
is personal data about a child even when every field is public. Treat it that
way.

- **Collect the minimum.** Use `--only` to name the tables your research
  question needs, or `--skip` to drop the ones it does not. A study of group
  structure does not need anyone's avatar or favourite games.
- **Store it securely.** Keep collected data on an encrypted, access-controlled
  drive, not in a shared folder or a public repository. Delete it when the
  project ends or your data-management plan says so.
- **Pseudonymise before publishing.** Replace user ids and usernames with study
  codes in anything that leaves the research team. Do not publish network
  graphs with real usernames as node labels.
- **Follow your institution's process.** Most universities require ethics or
  Institutional Review Board (IRB) review for research involving minors, even
  when the data is public. Ask before collecting, not after.
- **Know the legal frame.** In the European Union and the United Kingdom, the
  General Data Protection Regulation treats online identifiers as personal data
  and requires a lawful basis, a purpose limitation, and data minimisation; the
  research exemptions help but do not remove those duties. In the United States,
  the Children's Online Privacy Protection Act (COPPA) binds operators of
  services aimed at children rather than researchers, but institutional and state
  rules on minors' data still apply to you.

## Cookie handling

A `.ROBLOSECURITY` cookie is a logged-in session. Whoever holds it is you, as
far as Roblox can tell.

- Use a dedicated research account with nothing of value on it, never a
  personal account.
- Store the cookie in a file that only your user can read (`chmod 600` on
  macOS and Linux) and point PyRoblox at it with `--cookie-file` or
  `ROBLOX_COOKIE_FILE`. Do not put it in a script, a config file that is
  committed, a notebook, or a chat message.
- PyRoblox sends the cookie only to `roblox.com` and `*.roblox.com` hosts. Image
  downloads from the `rbxcdn.com` CDN never carry it. If Roblox rejects the
  cookie, PyRoblox drops it for the rest of the run and warns you once.
- Log out of the research account, which invalidates the cookie, when the
  collection is finished.

## If you find abuse

Research on Roblox safety will surface harmful content. Have a plan before you
start.

- **Report to Roblox.** Every user, group, game, and asset page has a Report
  Abuse link. Roblox's guide: https://en.help.roblox.com/hc/en-us/articles/203312410
- **Child sexual abuse material.** Do not download, copy, or keep it, even as
  evidence. In the United States report to the National Center for Missing and
  Exploited Children (NCMEC) CyberTipline at https://report.cybertip.org. In the
  United Kingdom report to the Internet Watch Foundation at https://report.iwf.org.uk.
  Elsewhere use your national hotline (the INHOPE network lists them at
  https://www.inhope.org). Then report the account to Roblox.
- **Imminent threats to life** go to local law enforcement first.
- PyRoblox's thumbnail downloader (`client.thumbnails.save`) writes images to
  disk. Think about whether your study needs images at all before you enable it.

## Citing PyRoblox

If PyRoblox contributed to a publication, please cite it:

> Center on Terrorism, Extremism, and Counterterrorism (CTEC), Middlebury
> Institute of International Studies. *PyRoblox: a Python wrapper for Roblox's
> public web APIs* (version 2.0.0). 2026. https://github.com/CTEC-MIIS/PyRoblox

Bug reports and contributions are welcome at the same address.
