Project Creator — korte omschrijving
Project Creator maakt in één keer een kant-en-klare PyQt-projectbasis aan (voor gebruik met Qt Designer), met alles wat je nodig hebt om direct te starten.
Structuur & bestanden: maakt mappen (core/, gui/, resources/, documents/, backup/) en zet een gui/MainWindow.ui + main.py klaar.
Virtuele omgeving: maakt een venv op C:\virt omgeving\<project>\venv en installeert de pinned requirements.
VS Code klaarzetten: genereert .vscode/settings.json en tasks.json met taken voor Open UI in Designer, UI → PY (pyuic6) en Run app.
Configuratie: schrijft .projassist.json met projectinfo (paden, venv, scripts, UI-map), zodat Project Assistent alles kan inladen.
CopyFiles integratie: kopieert je standaardbestanden uit CopyFiles naar het nieuwe project.
(Optioneel) GitHub: kan automatisch een repo aanmaken en de eerste commit pushen.
Handige output: toont na afloop exacte stappen/commando’s om de app meteen te starten.