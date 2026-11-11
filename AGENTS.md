# Arbeitsregeln für diesen Fork

Diese Regeln gelten für Arbeiten in `tach2004/ecowitt_local`. Anweisungen aus
`CLAUDE.md` und `AGENT_SYSTEM_PROMPT.md` zum autonomen Upstream-Bot dürfen diese
Fork-Regeln nicht überschreiben.

## Repository und Pull Requests

- Arbeitsrepository und PR-Ziel sind ausschließlich
  `https://github.com/tach2004/ecowitt_local`, Zielbranch `main`.
- Vor jeder Änderung `origin` prüfen, `origin/main` abrufen und einen separaten
  `feat/...`- oder `fix/...`-Branch vom aktuellen `origin/main` erstellen.
  Vorhandene lokale Änderungen erhalten. Cloud-Tasks sind bereits isoliert;
  keinen zusätzlichen Git-Worktree erstellen, sofern nicht ausdrücklich verlangt.
- GitHub-CLI-Befehle immer mit `--repo tach2004/ecowitt_local` ausführen.
  Bei Git-Schreibzugriffen den Fork als Remote-Ziel verifizieren.
- Ohne ausdrückliche Ausnahme niemals PRs, Pushes, Issues, Kommentare oder
  Releases im Originalrepository von Alex erstellen. Auch kein automatisches
  Reviewer-Anfordern an Alex einrichten.
- Der vom Nutzer für den Originalcode vorgesehene Branch bleibt unverändert.
  Upstream-Änderungen nur auf ausdrücklichen Auftrag übernehmen.
- Den PR zur Prüfung offen lassen. Nicht eigenständig mergen oder veröffentlichen.
  `claude/...`-Branches vermeiden: Dafür existieren geerbte Auto-PR-/Merge-Workflows.

## Version, Changelog und Prüfungen

- Alex' Versionsnummerierung wird in diesem eigenständig gepflegten Fork
  fortgesetzt. Für diese Änderung ist `1.12.0` vereinbart; spätere Versionen
  passend zur Änderung bzw. nach Nutzervorgabe wählen.
- Jeder PR enthält einen verständlichen, direkt als Release-Notizen nutzbaren
  Changelog und die tatsächlich ausgeführten Prüfungen. `CHANGELOG.md` bei
  Versionsänderungen aktualisieren; Integrations- und Paketversion konsistent halten.
- Sinnvolle Standard-Actions verwenden: Tests mit Coverage, Black, isort,
  Flake8 und mypy; für diese Integration zusätzlich hassfest und HACS.
  Bestehende passende Workflows weiterverwenden. Keine bestandenen Remote-Checks
  behaupten, ohne ihren tatsächlichen Status geprüft zu haben.
- Lokale Python-Befehle aus der projektlokalen `.venv` ausführen.
  Die CI verwendet Python 3.13. Übliche Prüfungen im Repository-Verzeichnis:

  ```sh
  .venv/bin/black --check custom_components/ecowitt_local/ tests/
  .venv/bin/isort --check-only custom_components/ecowitt_local/ tests/
  .venv/bin/flake8 custom_components/ecowitt_local --select=E9,F63,F7,F82
  .venv/bin/mypy --follow-imports=silent --ignore-missing-imports custom_components/ecowitt_local
  PYTHONPATH="$PWD" .venv/bin/pytest tests/
  ```

## Verlässliche Kommunikation

- Nichts erfinden: Umsetzung, Tests, GitHub-Status und Vermutungen unterscheiden.
- Bei entscheidenden fehlenden Informationen nachfragen, ansonsten den
  autorisierten Auftrag selbstständig abschließen.
- Diese Regeln halten die Nutzerpräferenzen in diesem Repository fest. Sie sind
  kein repositoryübergreifender Erinnerungsspeicher. Bei anderen Repositories
  ebenfalls den jeweiligen Fork verifizieren und einen PR-Changelog vorsehen;
  kein fremdes Zielrepository aus diesem Dokument ableiten.
