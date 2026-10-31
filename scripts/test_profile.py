import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import render_profile as profile


class ProfileTests(unittest.TestCase):
    def test_distribution_excludes_forks_and_preserves_total(self):
        def repo(name, size, fork=False):
            return {"isFork": fork, "languages": {"edges": [{"size": size, "node": {"name": name}}]}}
        result = profile.distribution([repo("Java", 30), repo("JS", 70), repo("Python", 900, True)])
        self.assertEqual(dict(result), {"JS": 70.0, "Java": 30.0})
        self.assertEqual(profile.distribution([]), [])

    def test_monthly_data_handles_year_boundary_and_limits_window(self):
        weeks = [{"contributionDays": [
            {"date": "2025-12-31", "contributionCount": 3},
            {"date": "2026-01-01", "contributionCount": 5},
            {"date": "2026-01-02", "contributionCount": 2},
        ]}]
        self.assertEqual(profile.monthly_counts(weeks), [("2025-12", 3), ("2026-01", 7)])
        longer = [{"contributionDays": [{"date": f"2025-{month:02d}-01", "contributionCount": 1} for month in range(1, 13)] + [{"date": "2026-01-01", "contributionCount": 2}]}]
        limited = profile.monthly_counts(longer)
        self.assertEqual(len(limited), 12)
        self.assertEqual(limited[0][0], "2025-02")
        self.assertEqual(limited[-1], ("2026-01", 2))

    def test_render_handles_empty_repos_and_escapes_external_text(self):
        user = {"repositories": {"totalCount": 0}, "contributionsCollection": {
            "totalCommitContributions": 0,
            "contributionCalendar": {"totalContributions": 0, "weeks": []},
        }}
        waka = {"range": "all_time", "total_seconds": 3600,
                "languages": [{"name": "A&B <code>", "percent": 100, "total_seconds": 3600}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(profile, "ROOT", Path(directory)):
            (Path(directory)/"assets").mkdir()
            profile.render(user, [], waka, dt.datetime(2026, 10, 31, 12))
            for artifact in (Path(directory)/"assets").glob("*.svg"):
                document = ET.parse(artifact)
                self.assertEqual(document.getroot().tag, "{http://www.w3.org/2000/svg}svg")
            svg = (Path(directory)/"assets/wakatime.svg").read_text(encoding="utf-8")
            self.assertIn("A&amp;B &lt;code&gt;", svg)
            self.assertIn("1h 00min", svg)


if __name__ == "__main__":
    unittest.main()
