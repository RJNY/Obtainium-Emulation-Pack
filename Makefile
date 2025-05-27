release: readme minify

links:
	python scripts/generate-obtainium-urls.py obtainium-emulation-pack.json > scripts/links.md

minify:
	python scripts/minify-json.py obtainium-emulation-pack.json obtainium-emulation-pack.min.json

table:
	python scripts/generate-table.py obtainium-emulation-pack.json ./readme/table.md

read-me: table
	python scripts/generate-readme.py ./readme/init.md ./readme/table.md ./readme/faq.md
