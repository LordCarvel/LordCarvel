"""Calendar periods shared by the README and the interactive dashboard."""

import datetime as dt

LABELS = {"mes": "Mês atual", "bimestre": "Bimestre atual", "semestre": "Semestre atual", "ano": "Ano atual"}


def bounds(now):
    months = {"mes": now.month, "bimestre": ((now.month-1)//2)*2+1,
              "semestre": 1 if now.month <= 6 else 7, "ano": 1}
    return {key: (now.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0), now)
            for key, month in months.items()}


def summarize(collection, start, end, label):
    calendar = collection["contributionCalendar"]
    by_date = {day["date"]: day["contributionCount"]
               for week in calendar["weeks"] for day in week["contributionDays"]}
    days, current = [], start.date()
    while current <= end.date():
        days.append({"date": current.isoformat(), "count": by_date.get(current.isoformat(), 0)})
        current += dt.timedelta(days=1)
    repos = []
    for item in collection.get("commitContributionsByRepository", []):
        repository = item["repository"]
        if not repository["isPrivate"]:
            repos.append({"name": repository["name"], "url": repository["url"],
                          "commits": item["contributions"]["totalCount"]})
    return {"label": label, "start": start.date().isoformat(), "end": end.date().isoformat(),
            "contributions": sum(day["count"] for day in days),
            "commits": collection["totalCommitContributions"],
            "active_days": sum(day["count"] > 0 for day in days),
            "days": days, "repositories": sorted(repos, key=lambda item: (-item["commits"],item["name"])),
            "wakatime": {"available": False,
                         "reason": "O WakaTime disponibiliza o histórico completo, sem recorte público para este período.",
                         "source_url": "https://wakatime.com/@639f7836-87c5-41ed-8dd2-0f0090178640"}}
