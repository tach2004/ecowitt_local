# Deutsche/englische Anzeige und Windrichtungspfeile

[Geprüftes Testpaket als ZIP herunterladen](https://github.com/tach2004/ecowitt_local/raw/refs/heads/feat/de-en-localization-wind-icons-20261110/downloads/ecowitt_local_de_en_windrichtung.zip)

Das Paket enthält die 17 vollständigen neuen/geänderten Quell- und Testdateien,
eine deutsche Einbauanleitung, den Prüfbericht, Prüfprotokolle und einen Patch
gegen den Fork-Stand `39909129e5acb58d04287b8aecd1fabe710112d3`.

Die Quelländerungen stehen separat im Commit
`8402f5b523b71593988fee6be3cab7b8278d5d41`. Das binäre Downloadpaket ist in einem
eigenen Commit abgelegt und muss für einen späteren Upstream-Beitrag nicht
übernommen werden.

## Einbau

Lies im ZIP zuerst `LIESMICH.md`. Alle Dateien unter
`repository/custom_components/ecowitt_local/` ergänzen bzw. überschreiben die
gleichnamigen Dateien der bestehenden Installation. Unveränderte Dateien bleiben
erforderlich. Die bestehende Integration bleibt eingerichtet; danach Home
Assistant neu starten. Sensor-/Gerätenamen folgen der HA-Systemsprache.

Technische Entitäts-IDs, Unique-IDs und selbst vergebene Namen werden erhalten.
Der Upgrade-Test und ein echter SQLite-Recorder-Test prüfen den Erhalt von
Zuordnungen, Verlauf und Langzeitstatistiken. Ein Test an deinem echten Gateway
steht noch aus.

## Prüfungen

- 634 Tests bestanden, 100 % Codeabdeckung mit HA 2026.2.3.
- Alle 116 neuen Tests bestehen zusätzlich mit HA 2026.10.4.
- Direkte Laufzeitprüfung der Namen, Werte, IDs und Richtungsklassen mit HA 2026.11.1.
- Offizielle Übersetzungs-, Manifest- und Serviceprüfungen mit HA 2026.1.0 und 2026.2.3.

Genaue Prüfumfänge und Einschränkungen stehen im beiliegenden `PRUEFBERICHT.md`.

SHA-256 des ZIP:

```text
cbda629b016a82c2f4ff86f65e579c5b16c5e409df68f192f64a4863be3e591c
```
