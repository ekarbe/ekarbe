# Activity cards

A nightly GitHub Action pulls new Garmin activities, makes one backdated commit
per activity, and redraws the three cards on the profile README.

## How a sync works

[`sync.yml`](../.github/workflows/sync.yml) runs [`sync.py`](sync.py) every night
at about 04:20 Berlin time, and on demand from the Actions tab.

1. **Fetch.** [`fetch_garmin.py`](fetch_garmin.py) logs in to Garmin Connect and
   fetches everything from two weeks before the newest stored activity, so
   late watch syncs are caught too. Already-stored IDs are skipped. If Garmin
   fails and the Strava secrets are set, [`fetch_strava.py`](fetch_strava.py)
   takes over and the run gets a warning annotation.
2. **Commit.** [`commit_activities.py`](commit_activities.py) adds each new
   activity to [`data/activities.json`](../data/activities.json) in its own
   commit, oldest first. The commit is authored with your noreply email and
   dated 12:00 Berlin time on the activity's day, e.g. `Run · 8.2 km`.
3. **Render.** [`render_cards.py`](render_cards.py) redraws `cards/*.svg` in a light
   and a dark variant. The commit is authored by `github-actions[bot]`, so it
   doesn't count on your contribution graph.
4. **Push** to `main`.

When `data/activities.json` is empty, the first run imports your whole Garmin
history.

Login tokens are cached between runs (encrypted, in the Actions cache), so
the sync doesn't do a full Garmin login every night.

## Setup

### 1. Garmin and the token cache

Add these under **Settings → Secrets and variables → Actions → New repository
secret**:

| Secret | Value |
| --- | --- |
| `GARMIN_EMAIL` | Your Garmin Connect email |
| `GARMIN_PASSWORD` | Your Garmin Connect password |
| `TOKEN_CACHE_KEY` | Any long random string, e.g. from `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |

In a public repo, pull request workflows can read the Actions cache, so the
cached tokens are encrypted with `TOKEN_CACHE_KEY`. Without the key nothing is
cached and every run logs in from scratch.

### 2. Strava fallback

1. Create an API application at <https://www.strava.com/settings/api>. Any
   name and website will do. Set **Authorization Callback Domain** to
   `localhost`.
2. On your own machine, run:

   ```sh
   pip install requests
   STRAVA_CLIENT_ID=... STRAVA_CLIENT_SECRET=... python scripts/strava_auth.py
   ```

   Follow the prompts. It prints a refresh token with `activity:read_all`
   access, so activities set to "Only me" count too.
3. Add the three Strava secrets:

| Secret | Value |
| --- | --- |
| `STRAVA_CLIENT_ID` | Client ID of the Strava app |
| `STRAVA_CLIENT_SECRET` | Client secret of the Strava app |
| `STRAVA_REFRESH_TOKEN` | The token `strava_auth.py` printed |

Activities that Garmin uploaded to Strava keep their Garmin ID, so switching
between sources never creates duplicates.

### 3. First run

Open **Actions → Sync activities → Run workflow**. With the data file empty,
this run imports your full history and pushes one commit per activity. The
contribution graph can take a while to catch up after a big push.

To preview locally without committing anything:

```sh
pip install -r requirements.txt
GARMIN_EMAIL=... GARMIN_PASSWORD=... python scripts/sync.py --dry-run
```

## Data and privacy

The repo is public, history included. Only these fields are stored:
activity type, day (no time), duration, distance in km, and the Garmin
activity ID for de-duplication. Names, start times, GPS tracks, locations,
heart rate and device names are never written anywhere.

The workflow logs are public too. They list the same date, type and distance
that the commits already show.

## When things break

- **Garmin login breaks.** The nightly run falls back to Strava and shows a
  warning. Once the [garminconnect](https://pypi.org/project/garminconnect/)
  library ships a fix, bump its version in [`requirements.txt`](../requirements.txt).
  To force a source, choose it under **Run workflow**.
- **Strava token stops working.** Run `strava_auth.py` again and replace
  `STRAVA_REFRESH_TOKEN`.
- **Scheduled runs stop.** GitHub disables scheduled workflows after 60 days
  without repo activity. The nightly card commit normally prevents that. If it
  happens, re-enable the workflow in the Actions tab.
- **An activity is wrong.** Edit `data/activities.json` by hand. Its commit
  stays in history and on the graph.

## Tests

```sh
pip install -r requirements-dev.txt
python -m pytest
```
