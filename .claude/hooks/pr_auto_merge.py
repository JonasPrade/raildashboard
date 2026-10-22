#!/usr/bin/env python3
"""PostToolUse-Hook: nach dem Anlegen eines PRs den Auto-Merge-Auftrag einspeisen.

Dass dieses Skript in `.claude/settings.json` eines Repos eingetragen ist, ist die
Freischaltung: Nur Repos, in denen allein Jonas entwickelt, tragen es. Der Hook
handelt nicht selbst, er gibt Claude den Auftrag — CI abwarten, Fehler beheben,
mergen — als Kontext mit, sobald der PR existiert.
"""

import json
import re
import sys

AUFTRAG = """\
Auto-Merge ist in diesem Repository eingeschaltet (`.claude/settings.json`), \
PR {pr} ist gerade entstanden. Das ist Jonas' dauerhafter Auftrag, ohne Rückfrage:

1. `subscribe_pr_activity` für {owner}/{repo}#{nummer} aufrufen und auf die \
CI-Ereignisse warten — nicht mit `sleep` pollen.
2. Wird die CI rot: Ursache finden, lokal mit `make test` nachstellen, beheben, \
pushen. So lange \
wiederholen, bis die CI auf dem aktuellen Head grün ist. Nie einen Test \
überspringen oder abschalten.
3. Ist die CI grün, gibt es keinen Merge-Konflikt und keinen offenen \
Review-Thread: den PR mit `merge_pull_request` als Merge-Commit \
(`merge_method: merge`) zusammenführen, danach `unsubscribe_pr_activity`.

Nicht mergen, sondern grün melden und anhalten, wenn das Issue eine manuelle \
Verifikation braucht (Workflow-Status „Needs User Test").
"""


def main() -> None:
    ereignis = json.load(sys.stdin)
    eingabe = json.dumps(ereignis.get("tool_input", {}))
    if ereignis.get("tool_name") == "Bash" and "gh pr create" not in eingabe:
        return
    if re.search(r'"draft": true|--draft', eingabe):
        return
    treffer = re.search(
        r"github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)",
        json.dumps(ereignis.get("tool_response", "")),
    )
    if not treffer:
        return
    owner, repo, nummer = treffer.groups()
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": AUFTRAG.format(
                pr=f"https://github.com/{owner}/{repo}/pull/{nummer}",
                owner=owner, repo=repo, nummer=nummer,
            ),
        }
    }))


if __name__ == "__main__":
    main()
