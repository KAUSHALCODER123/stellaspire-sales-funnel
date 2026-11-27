Bundled so the plugin runs without installing anything: holidays 0.105, python-dateutil 2.9.0.post0, six 1.17.0.
ss.py appends this folder to sys.path last, so an installed copy of any of them wins.
Licenses: see the LICENSE-*.txt files.
One change: holidays/version.py states the version directly instead of reading install metadata.
