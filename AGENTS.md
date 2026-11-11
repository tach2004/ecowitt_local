# Anweisungen für diesen Fork

Vor Änderungen **CLAUDE.md und AGENT_SYSTEM_PROMPT.md vollständig lesen und als
zusätzliche Anweisungen beachten**. Sie beschreiben die bestehende Architektur,
Entwicklungsabläufe, Prüfungen und das Changelog-Format. Bestehende Lösungen
weiterverwenden; keine parallelen Verfahren oder abgeschwächten Prüfungen aufbauen.
Ausdrückliche neuere Nutzeranweisungen haben Vorrang, insbesondere diese
vereinbarten Ausnahmen für den Fork:

- Arbeitsrepository und einziges PR-Ziel sind `tach2004/ecowitt_local`, Basis `main`.
  `origin` vor Schreibzugriffen prüfen. Neue Änderungen beginnen auf einem eigenen
  Branch vom frisch abgerufenen `origin/main`; laufende Änderungen auf ihrem
  vorhandenen Branch abschließen. Lokale Änderungen erhalten. Cloud-Tasks sind
  isoliert; zusätzliche Git-Worktrees nur auf ausdrücklichen Wunsch erstellen.
- Niemals PRs, Pushes, Issues, Kommentare, Reviews oder Releases im Originalrepo
  von Alex erstellen oder an Alex senden, sofern der Nutzer keine ausdrückliche
  Ausnahme erteilt. Den Branch mit dem unveränderten Originalcode nicht anfassen;
  Upstream-Änderungen nur auf Auftrag übernehmen.
- Bei GitHub-Befehlen das Fork-Ziel ausdrücklich angeben: `--repo
  tach2004/ecowitt_local`, wenn unterstützt, sonst vollständige API-Pfade unter
  `repos/tach2004/ecowitt_local`. Keine automatischen Reviewer an Alex anfordern.
- Für diesen Auftrag bleibt der Branch `feat/1.12.0-fast-polling-uv-icon` und die
  Version `1.12.0`. Die Versionsnummerierung wird fortgesetzt. PRs offen zur
  Prüfung lassen; nicht eigenständig mergen, taggen oder veröffentlichen. Damit
  gelten die abweichenden Bot-Vorgaben zu `claude/release-*`, automatischem Merge
  und sofortiger Veröffentlichung hier nicht.
- **Alle Änderungen in der vorhandenen CHANGELOG.md dokumentieren und denselben
  Changelog zusätzlich in den PR aufnehmen.** Keine zweite Changelog-Struktur.
- Die vorhandenen GitHub Actions weiterverwenden. Die vorgeschriebenen Prüfungen
  aus den beiden Anweisungsdateien ausführen, einschließlich **100 % Coverage**;
  lokale Python-Befehle aus `.venv` ausführen. Unter Linux an der bestehenden
  CI-Konfiguration mit Python 3.13 orientieren, nicht an macOS-Pfaden.
- Nur tatsächlich verifizierte Ergebnisse berichten; fehlgeschlagene,
  übersprungene und noch laufende Prüfungen klar unterscheiden. Nichts erfinden;
  bei entscheidenden fehlenden Informationen nachfragen.

Diese Datei bewahrt die Vereinbarungen im Repository; sie ist kein globaler
Erinnerungsspeicher. Bei künftigen Repositories ebenfalls das vom Nutzer gewählte
Fork-Ziel prüfen und Änderungen im bestehenden Changelog sowie PR dokumentieren.
