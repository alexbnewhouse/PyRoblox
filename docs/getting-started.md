# Getting started with PyRoblox

This guide is for researchers who have never used a command line. It takes about
fifteen minutes. If you already know Python, skim this and then read
[python-api.md](python-api.md).

## What PyRoblox does

PyRoblox downloads public information from Roblox about users, groups
(communities), and games, and saves it as spreadsheet files (CSV). You type one
command, and a folder of CSV files appears. Everything it collects is visible to
anyone who visits roblox.com in a browser.

PyRoblox does not log in as anyone, does not send friend requests or messages,
does not join groups, and cannot see private data. A few kinds of data need a
logged-in account (see "Using a cookie" below); everything else works without one.

## Install

### 1. Install Python

PyRoblox needs Python 3.9 or newer.

- **macOS**: Python 3 is usually present. Open **Terminal** (press Cmd+Space,
  type `Terminal`, press Enter) and type `python3 --version`. If you see a
  version number 3.9 or higher, skip to step 2. Otherwise download the installer
  from https://www.python.org/downloads/ and run it.
- **Windows**: download the installer from https://www.python.org/downloads/.
  On the first screen of the installer, **tick "Add python.exe to PATH"**, then
  click Install Now. Afterwards open **PowerShell** (press the Windows key, type
  `PowerShell`, press Enter).

### 2. Install PyRoblox

Copy this line into the Terminal or PowerShell window and press Enter:

```
python3 -m pip install "git+https://github.com/CTEC-MIIS/PyRoblox"
```

On Windows, if `python3` is not recognised, use `py` instead:

```
py -m pip install "git+https://github.com/CTEC-MIIS/PyRoblox"
```

Text will scroll by for a minute. It is done when you get the prompt back.

### 3. Check it works

```
roblox --version
roblox check
```

The first prints `roblox, version 2.0.0`. The second contacts Roblox and should
end with `Everything looks good.`

If the computer says `roblox: command not found`, the install worked but the
shortcut is not on your path. Use this longer form instead, wherever this guide
says `roblox`:

```
python3 -m pyroblox.cli check
```

## Your first commands

Roblox identifies things by number. PyRoblox accepts the number, a username, or
a link copied from your browser, so you rarely need to look the number up.

```
roblox user info Shedletsky
```

prints a short summary and writes `roblox_data/user_261_profile.csv`.

```
roblox user snapshot Shedletsky
```

collects everything public about that user: profile, friends, groups, games,
favourites, avatar, and so on. It prints progress as it goes and ends with a list
of the files it wrote.

```
roblox group snapshot 7
roblox game info https://www.roblox.com/games/1818/Classic-Crossroads
```

The group command takes a group id or a `roblox.com/groups/...` or
`roblox.com/communities/...` link. The game command takes a universe id or a
`roblox.com/games/...` link (PyRoblox converts the place id in the link for you).

### Where the files go

Files are written to a folder called `roblox_data` inside whatever folder your
Terminal is currently in (usually your home folder). To choose a different
folder, add `-o` and a folder name to any command:

```
roblox user snapshot Shedletsky -o shedletsky_study
```

### Opening the CSV files

Double-click a CSV file to open it in Excel, or upload it to Google Sheets.

One warning: Roblox ids are very large numbers. Excel may show
`4.37199E+09` instead of `4371992339`, and may round the last digits if you
edit and save the file. To avoid that, in Excel use File > Import instead of
double-clicking, and set the id columns to **Text**. In Google Sheets, select the
id column and choose Format > Number > Plain text. Never save an edited CSV over
the original.

## Reading the output

Every snapshot writes one CSV per table plus a manifest:

```
roblox_data/
  user_261_profile.csv
  user_261_friends.csv
  user_261_groups.csv
  ...
  user_261_manifest.json
```

File names follow the pattern `<what>_<id>_<table>.csv`. The manifest is a small
text file that records when the data was collected, how many rows each table
has, which tables were skipped and why (for example "cookie-required" or
"private"), and which tables were cut short by a `--max` limit. Keep it with the
CSVs; it is your record of what the data does and does not contain.

Column meanings are in [data-dictionary.md](data-dictionary.md).

## Collecting a whole network

Two commands build network edge lists for tools such as Gephi or NodeXL.

```
roblox user network Shedletsky
```

fetches the user's friend list and writes `friend_network_261_edges.csv`
(columns `source`, `target`) and `friend_network_261_nodes.csv` (ids, names, and
how far each node is from the seed user). Add `--depth 2` to also fetch each
friend's friends. Add `--graphml` to write a `.graphml` file that Gephi opens
directly.

```
roblox group network 7
```

fetches the group's allies and enemies, then their allies and enemies, then the
member list of every group in that neighbourhood. It writes `groups`, `allies`,
`enemies`, `membership`, and `members` tables.

### How long will it take?

Roblox limits how fast anyone can ask for data. PyRoblox waits when it has to,
so a big collection is slow rather than broken. Rough guides:

| Data | Roblox allows | Example |
|---|---|---|
| friend lists | about 20 per minute | depth 2 for a user with 200 friends: about 10 minutes |
| group member lists | about 100 members per second | a 100,000-member group: about 20 minutes |
| full user profiles (`--profiles`) | about 30 per minute | 1,000 members: about 35 minutes |
| public servers of a game | about 3 calls per minute | keep `--max-servers` small |

Use the caps when you only need a sample: `--max` (rows per table), `--max-users`
(friend lists to fetch), `--max-groups` and `--max-members` (for group networks).
Anything that was cut short is marked "truncated" in the manifest.

You can stop a run at any time with Ctrl-C. Files already written are kept.

## Using a cookie (optional)

A few kinds of data are only shown to logged-in Roblox accounts:

- a user's **followers** and **following** lists (the counts are public)
- a user's **badges** earned in games
- a group's **social links** (Discord, X, YouTube)
- a user's **linked social accounts** (`roblox user social`)

To collect these, PyRoblox needs the `.ROBLOSECURITY` cookie from a logged-in
browser session.

**Warning.** This cookie is your login. Anyone who has it can use your account,
spend your Robux, and change your settings. Use a throwaway research account,
never a personal one. Never paste the cookie into a document, an email, or a
shared drive, and never commit it to a code repository. PyRoblox only ever sends
it to roblox.com addresses.

To find it in Chrome: log in to roblox.com, press F12 to open Developer Tools,
click the **Application** tab, expand **Cookies** in the left panel, click
`https://www.roblox.com`, and copy the **Value** of the row named
`.ROBLOSECURITY`. In Firefox the tab is called **Storage**.

Save it in a text file that only you can read, for example `roblox_cookie.txt`,
then either pass the file each time:

```
roblox --cookie-file roblox_cookie.txt user followers Shedletsky
```

or set it once for the whole Terminal session:

```
export ROBLOX_COOKIE_FILE=/full/path/to/roblox_cookie.txt      # macOS
$env:ROBLOX_COOKIE_FILE = "C:\full\path\to\roblox_cookie.txt"   # Windows PowerShell
```

`roblox check` tells you whether the cookie is accepted. Cookies expire when you
log out or change your password; copy a fresh one if `check` says it was rejected.

## When something goes wrong

PyRoblox tries to explain problems in plain language. The messages you are most
likely to see:

| Message | Meaning | What to do |
|---|---|---|
| `Not found. Check the id; the account, group, or game may be deleted.` | Roblox has nothing with that id. | Check the id or link. |
| `user 12345 rejected by Roblox: The user is invalid.` | Usually a banned account. | The profile itself may still work with `roblox user info`; other tables will not. |
| `Roblox only shows this to logged-in accounts. Add --cookie ...` | That data needs a cookie. | See "Using a cookie". |
| `Roblox says this is private or hidden from you.` | The user hides this (for example their inventory). | Nothing to do. |
| `Roblox is rate limiting this computer. Wait a minute and try again.` | Too many requests from your network. | Wait a minute. Do not run several commands at once. |
| `Roblox's servers returned an error. Try again in a few minutes.` | Roblox itself is having trouble. | Wait. |
| `Give a numeric group id or a roblox.com/groups/<id> link.` | Group names are not unique, so PyRoblox does not guess. | Run `roblox search groups "the name"` first. |

Inside a snapshot, a table that Roblox refuses does not stop the run. It is
listed as skipped in the summary and in the manifest, and the other tables are
still written.

If you need to report a bug, run the command again with `--debug` at the front
(`roblox --debug user info 261`) and include the full output.

## Being a good citizen

PyRoblox only reads public data, but "public" does not mean "free of
obligations". Many Roblox users are children. Collect only what your research
question needs (`--only` and `--skip` let you pick tables), store the files
securely, and follow your institution's ethics process. Do not try to get around
Roblox's rate limits by running many copies at once. Read
[responsible-use.md](responsible-use.md) before you start a study.
