generate-urls:
	python scripts/generate-obtainium-urls.py obtainium-emulation-pack.json >> scripts/links.md

minify:
	python scripts/minify-json.py obtainium-emulation-pack.json obtainium-emulation-pack.min.json
