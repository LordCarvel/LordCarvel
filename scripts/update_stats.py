"""Fetch public statistics and regenerate the Neovim profile."""

import datetime as dt
import json
import os
import urllib.error
import urllib.request

from render_profile import render
from periods import bounds, summarize, LABELS

USER = "LordCarvel"
WAKA = "639f7836-87c5-41ed-8dd2-0f0090178640"
ZONE = dt.timezone(dt.timedelta(hours=-3))


def request(url, payload=None, token=None):
    headers = {"User-Agent": "LordCarvel-profile", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if payload is None else json.dumps(payload).encode()
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def github(now):
    query = '''query($login:String!,$cursor:String,$from:DateTime!,$to:DateTime!) { user(login:$login) {
      contributionsCollection(from:$from,to:$to) { startedAt endedAt totalCommitContributions
        contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } }
      repositories(first:100,after:$cursor,ownerAffiliations:OWNER,privacy:PUBLIC) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes { name description pushedAt stargazerCount isFork isArchived
          primaryLanguage { name }
          defaultBranchRef { name target { ... on Commit { history { totalCount } } } }
          languages(first:100) { edges { size node { name } } } }
      }
    } }'''
    nodes, cursor = [], None
    while True:
        variables = {"login": USER, "cursor": cursor, "from": (now-dt.timedelta(days=365)).isoformat(), "to": now.isoformat()}
        result = request("https://api.github.com/graphql", {"query": query, "variables": variables}, os.environ["GH_TOKEN"])
        if result.get("errors"):
            raise RuntimeError("GitHub GraphQL query failed")
        user = result["data"]["user"]
        repo = user["repositories"]
        nodes.extend(repo["nodes"])
        if not repo["pageInfo"]["hasNextPage"]:
            return user, nodes
        cursor = repo["pageInfo"]["endCursor"]


def wakatime():
    try:
        data = request(f"https://wakatime.com/api/v1/users/{WAKA}/stats")["data"]
    except urllib.error.HTTPError as error:
        if error.code not in (401, 403, 404):
            raise
        print("WakaTime: public stats unavailable; keeping the last published panel.")
        return None
    if not data.get("is_coding_activity_visible") or "total_seconds" not in data:
        print("WakaTime: activity is private; keeping the last published panel.")
        return None
    # Only pass the fields used by the profile, excluding unrelated account data.
    return {key: data.get(key) for key in ("total_seconds", "range", "languages")}


def period_stats(now):
    windows = bounds(now)
    fields = []
    for key, (start, end) in windows.items():
        fields.append(f'''{key}: contributionsCollection(from:"{start.isoformat()}",to:"{end.isoformat()}") {{
          totalCommitContributions
          contributionCalendar {{ weeks {{ contributionDays {{ date contributionCount }} }} }}
          commitContributionsByRepository(maxRepositories:100) {{
            repository {{ name url isPrivate }} contributions {{ totalCount }}
          }}
        }}''')
    query = 'query { user(login:"'+USER+'") { '+" ".join(fields)+' } }'
    result = request("https://api.github.com/graphql", {"query": query}, os.environ["GH_TOKEN"])
    if result.get("errors"):
        raise RuntimeError("GitHub period query failed")
    data = result["data"]["user"]
    return {key: summarize(data[key], start, end, LABELS[key]) for key, (start,end) in windows.items()}


if __name__ == "__main__":
    now = dt.datetime.now(ZONE)
    user, nodes = github(now)
    render(user, nodes, wakatime(), now, period_stats(now))
    print("Profile regenerated from current public data.")
