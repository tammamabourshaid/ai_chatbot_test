"""
evaluate.py

Human-readable runner for the chatbot test suite.
Delegates all test logic to tests/test_chatbot.py -- no duplicate cases here.

Run with:  python evaluate.py
"""

import datetime
import pytest


class _ResultCollector:
    def __init__(self):
        self.results = []

    def pytest_runtest_logreport(self, report):
        label = report.nodeid.split("::")[-1]
        if report.when == "setup" and report.skipped:
            self.results.append(("skip", label, "server unreachable"))
        elif report.when == "call":
            if report.passed:
                self.results.append(("pass", label, ""))
            elif report.failed:
                msg = str(report.longrepr).splitlines()[-1] if report.longrepr else ""
                self.results.append(("fail", label, msg))

    def pytest_runtest_logstart(self, nodeid, location):
        pass


def run():
    collector = _ResultCollector()

    pytest.main(
        ["tests/", "-v", "--tb=short", "--no-header", "-q"],
        plugins=[collector],
    )

    lines = []
    lines.append("\n" + "=" * 60)
    lines.append(f"  Banking Chatbot Evaluation -- {datetime.datetime.now():%Y-%m-%d %H:%M}")
    lines.append("=" * 60)

    passed = 0
    failed = 0
    skipped = 0
    for status, label, note in collector.results:
        if status == "pass":
            icon = "[PASS]"
            passed += 1
        elif status == "fail":
            icon = "[FAIL]"
            failed += 1
        else:
            icon = "[SKIP]"
            skipped += 1
        note_str = f" | {note}" if note else ""
        lines.append(f"  {icon}  {label}{note_str}")

    total = passed + failed + skipped
    lines.append("\n" + "=" * 60)
    lines.append(f"  RESULTS: {passed}/{total} passed  ({skipped} skipped)")
    lines.append("=" * 60 + "\n")

    output = "\n".join(lines)
    print(output)
    with open("results.log", "a") as f:
        f.write(output + "\n")


if __name__ == "__main__":
    run()
