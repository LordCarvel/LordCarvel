"""Build profile graphics from public GitHub and WakaTime statistics."""

import collections
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USER = "LordCarvel"
WAKA = "639f7836-87c5-41ed-8dd2-0f0090178640"
ZONE = dt.timezone(dt.timedelta(hours=-3))
NOW = dt.datetime.now(ZONE)
TODAY = NOW.date().isoformat()
COLORS = ["#a7e084", "#e6bd78", "#86cbd6", "#c3a1e8", "#e99d91", "#93a9d8"]


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


def text(x, y, value, size=20, color="#f1f1ed", extra=""):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" {extra}>{html.escape(str(value))}</text>'


def svg(name, height, title, content, description):
    document = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(description)}</desc>'
        f'<rect x="1" y="1" width="958" height="{height-2}" rx="12" fill="#0c0c0c" stroke="#353832"/>'
        '<g font-family="DejaVu Sans Mono,Consolas,monospace">'
        + text(32, 43, title, 23, "#a7e084")
        + content
        + text(32, height-22, f"Atualizado em {TODAY}", 14, "#a8aaa2")
        + '</g></svg>\n'
    )
    (ROOT / "assets" / name).write_text(document, encoding="utf-8")


def bars(rows, y=95, width=545):
    output = ""
    for i, (name, percent, label) in enumerate(rows):
        line = y + i * 43
        output += text(32, line, name, 18)
        output += f'<rect x="235" y="{line-16}" width="{width}" height="18" rx="3" fill="#23271f"/>'
        output += f'<rect x="235" y="{line-16}" width="{max(1, width*percent/100):.1f}" height="18" rx="3" fill="{COLORS[i % len(COLORS)]}"/>'
        output += text(920, line, label, 17, "#d7d9d1", 'text-anchor="end"')
    return output


def github():
    query = '''query($login:String!,$cursor:String,$from:DateTime!,$to:DateTime!) { user(login:$login) {
      contributionsCollection(from:$from,to:$to) { startedAt endedAt totalCommitContributions
        contributionCalendar { totalContributions weeks { contributionDays { date contributionCount color } } } }
      repositories(first:100,after:$cursor,ownerAffiliations:OWNER,privacy:PUBLIC) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes { isFork languages(first:100) { edges { size node { name } } } }
      }
    } }'''
    nodes, cursor, user = [], None, None
    while True:
        variables = {"login": USER, "cursor": cursor, "from": (NOW-dt.timedelta(days=365)).isoformat(), "to": NOW.isoformat()}
        response = request("https://api.github.com/graphql", {"query": query, "variables": variables}, os.environ["GH_TOKEN"])
        if response.get("errors"):
            raise RuntimeError("GitHub GraphQL query failed")
        user = response["data"]["user"]
        repo = user["repositories"]
        nodes.extend(repo["nodes"])
        if not repo["pageInfo"]["hasNextPage"]:
            break
        cursor = repo["pageInfo"]["endCursor"]
    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    active = sum(day["contributionCount"] > 0 for week in calendar["weeks"] for day in week["contributionDays"])
    metrics = [(repo["totalCount"], "repos públicos"), (calendar["totalContributions"], "contribuições"), (collection["totalCommitContributions"], "commits"), (active, "dias ativos")]
    output = ""
    for i, (value, label) in enumerate(metrics):
        x = 32 + i * 232
        output += text(x, 106, value, 43) + text(x, 135, label, 17, "#a8aaa2")
    start, end = [dt.datetime.fromisoformat(collection[key].replace("Z", "+00:00")).astimezone(ZONE).date().isoformat() for key in ("startedAt", "endedAt")]
    output += text(32, 181, f"Contribuições · {start} a {end}", 17, "#a8aaa2")
    palette = ["#23271f", "#345031", "#547b41", "#7dae60", "#a7e084"]
    for col, week in enumerate(calendar["weeks"]):
        for day in week["contributionDays"]:
            date = dt.date.fromisoformat(day["date"])
            row = (date.weekday() + 1) % 7
            count = day["contributionCount"]
            color = palette[0 if not count else min(4, 1 + (count-1)//3)]
            output += f'<rect x="{32+col*17}" y="{205+row*19}" width="13" height="15" rx="2" fill="{color}"><title>{day["date"]}: {count} contribuições</title></rect>'
    output += text(32, 366, "Atividade nos últimos 12 meses · GitHub", 15, "#a8aaa2")
    svg("github-stats.svg", 415, "~ $ git log --stat", output, "; ".join(f"{v} {label}" for v, label in metrics))
    languages = collections.Counter()
    for node in nodes:
        if not node["isFork"]:
            for edge in node["languages"]["edges"]:
                languages[edge["node"]["name"]] += edge["size"]
    total = sum(languages.values())
    ranked = languages.most_common(5)
    remainder = total - sum(size for _, size in ranked)
    if remainder:
        ranked.append(("Outras", remainder))
    rows = [(name, 100*size/total, f"{100*size/total:.1f}%") for name, size in ranked] if total else []
    output = bars(rows) + text(32, 367, "Código público por tamanho · forks excluídos", 15, "#a8aaa2")
    svg("languages.svg", 415, "~ $ linguagens --github", output, "; ".join(f"{name}: {label}" for name, _, label in rows))


def wakatime():
    url = f"https://wakatime.com/api/v1/users/{WAKA}"
    try:
        data = request(url + "/stats")["data"]
    except urllib.error.HTTPError as error:
        if error.code not in (401, 403, 404):
            raise
        print("WakaTime: public stats unavailable; preserving existing panel.")
        return
    if not data.get("is_coding_activity_visible") or not data.get("human_readable_total"):
        print("WakaTime: coding activity is not public; preserving existing panel.")
        return
    total = data["human_readable_total"]
    average = data.get("human_readable_daily_average", "—")
    public_range = data.get("range", "public")
    range_label = "histórico completo" if public_range == "all_time" else "período público selecionado"
    output = text(32, 98, total, 34) + text(32, 127, range_label, 17, "#a8aaa2")
    output += text(520, 98, average, 34) + text(520, 127, "média diária no período", 17, "#a8aaa2")
    languages = data.get("languages", [])[:5]
    rows = [(item["name"], item["percent"], f'{item["percent"]:.1f}%') for item in languages]
    output += bars(rows, y=187)
    footer = 187 + len(rows)*43
    description = f"Tempo no período público ({public_range}): {total}; média diária: {average}. "
    try:
        lifetime = request(url + "/all_time_since_today")["data"].get("text")
    except urllib.error.HTTPError as error:
        if error.code not in (401, 403, 404):
            raise
        lifetime = None
    if lifetime and public_range != "all_time":
        output += text(32, footer, f"Total registrado: {lifetime}", 18, "#e6bd78")
        description += f"Total registrado: {lifetime}. "
    start, end = data.get("start", "")[:10], data.get("end", "")[:10]
    output += text(32, footer+32, f"Período: {start} a {end} · WakaTime", 15, "#a8aaa2")
    svg("wakatime.svg", footer+86, "~ $ wakatime --" + public_range.replace("_", "-"), output, description + "; ".join(f"{n}: {p}" for n, _, p in rows))
    readme = ROOT / "README.md"
    content = readme.read_text(encoding="utf-8")
    section = '''<!-- WAKATIME:START -->

## Tempo de programação

<p align="center">
  <a href="https://wakatime.com/@639f7836-87c5-41ed-8dd2-0f0090178640">
    <img src="./assets/wakatime.svg" width="960" alt="WakaTime: tempo de programação, média diária e linguagens no período público selecionado." />
  </a>
</p>

<sub>Tempo registrado pelo WakaTime nos editores conectados. A distribuição de linguagens considera o período indicado no painel.</sub>

<!-- WAKATIME:END -->'''
    content, replacements = re.subn(r"<!-- WAKATIME:START -->.*?<!-- WAKATIME:END -->", lambda _: section, content, flags=re.S)
    if replacements != 1:
        raise RuntimeError("Expected exactly one WakaTime section")
    readme.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    github()
    wakatime()
    print("Profile statistics updated.")
