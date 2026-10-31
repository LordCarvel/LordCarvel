import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from periods import bounds, summarize
import profile_views
import render_profile


ZONE = dt.timezone(dt.timedelta(hours=-3))


def collection(days, repositories=(), commits=0):
    return {
        "contributionCalendar": {"weeks": [{"contributionDays": [
            {"date": date, "contributionCount": count} for date, count in days
        ]}]},
        "totalCommitContributions": commits,
        "commitContributionsByRepository": list(repositories),
    }


def repository(name, commits, private=False):
    return {"repository": {"name": name, "url": f"https://github.com/example/{name}", "isPrivate": private},
            "contributions": {"totalCount": commits}}


class CalendarPeriodTests(unittest.TestCase):
    def test_calendar_boundaries_keep_timezone_and_current_instant(self):
        cases = [
            ((2026, 1, 1), {"mes": 1, "bimestre": 1, "semestre": 1, "ano": 1}),
            ((2026, 6, 30), {"mes": 6, "bimestre": 5, "semestre": 1, "ano": 1}),
            ((2026, 7, 1), {"mes": 7, "bimestre": 7, "semestre": 7, "ano": 1}),
            ((2026, 11, 30), {"mes": 11, "bimestre": 11, "semestre": 7, "ano": 1}),
            ((2026, 12, 31), {"mes": 12, "bimestre": 11, "semestre": 7, "ano": 1}),
            ((2024, 2, 29), {"mes": 2, "bimestre": 1, "semestre": 1, "ano": 1}),
        ]
        for date, expected_months in cases:
            now = dt.datetime(*date, 23, 15, 9, 123, tzinfo=ZONE)
            for key, (start, end) in bounds(now).items():
                with self.subTest(date=date, period=key):
                    self.assertEqual(start, dt.datetime(date[0], expected_months[key], 1, tzinfo=ZONE))
                    self.assertIs(end, now)
                    self.assertIs(start.tzinfo, ZONE)

    def test_summary_excludes_calendar_padding_and_fills_gaps(self):
        start = dt.datetime(2024, 2, 28, tzinfo=ZONE)
        end = dt.datetime(2024, 3, 1, 12, tzinfo=ZONE)
        source = collection([
            ("2024-02-27", 100),
            ("2024-02-28", 2),
            ("2024-03-01", 3),
            ("2024-03-02", 200),
        ], commits=4)
        result = summarize(source, start, end, "Teste")
        self.assertEqual(result["days"], [
            {"date": "2024-02-28", "count": 2},
            {"date": "2024-02-29", "count": 0},
            {"date": "2024-03-01", "count": 3},
        ])
        self.assertEqual(result["contributions"], 5)
        self.assertEqual(result["active_days"], 2)
        self.assertEqual(result["commits"], 4)

    def test_summary_omits_private_repository_names_and_sorts_public_repos(self):
        now = dt.datetime(2026, 1, 1, tzinfo=ZONE)
        source = collection([], [
            repository("private-client-secret", 99, private=True),
            repository("Zeta", 4), repository("Beta", 4), repository("Main", 12),
        ])
        result = summarize(source, now, now, "Ano atual")
        self.assertEqual([repo["name"] for repo in result["repositories"]], ["Main", "Beta", "Zeta"])
        self.assertNotIn("private-client-secret", json.dumps(result))
        self.assertFalse(result["wakatime"]["available"])
        self.assertEqual(result["days"], [{"date": "2026-01-01", "count": 0}])

    def test_period_export_contains_only_public_repository_details(self):
        now = dt.datetime(2026, 1, 1, 12, tzinfo=ZONE)
        source = collection([("2026-01-01", 1)], [
            repository("private-client-secret", 19, private=True), repository("Cdatra", 1),
        ], commits=1)
        period = summarize(source, now.replace(hour=0), now, "Mês atual")
        node = {"name": "Cdatra", "isFork": False, "pushedAt": now.isoformat(),
                "languages": {"edges": [{"size": 100, "node": {"name": "Java"}}]},
                "defaultBranchRef": {"target": {"history": {"totalCount": 5}}},
                "unrelated_private_metadata": "do-not-export-this"}
        with tempfile.TemporaryDirectory() as directory, patch.object(render_profile, "ROOT", Path(directory)):
            (Path(directory)/"assets").mkdir()
            profile_views.publish_views({}, [node], None, now, {"mes": period})
            path = Path(directory)/"site/data.json"
            serialized = path.read_text(encoding="utf-8")
            data = json.loads(serialized)
            self.assertNotIn("private-client-secret", serialized)
            self.assertNotIn("do-not-export-this", serialized)
            self.assertEqual(data["periods"]["mes"]["repositories"][0]["name"], "Cdatra")
            self.assertEqual(data["profile"]["projects"][0]["commits"], 5)
            self.assertIsNone(data["wakatime"])
            for artifact in (Path(directory)/"assets").glob("*.svg"):
                ET.parse(artifact)


if __name__ == "__main__":
    unittest.main()
