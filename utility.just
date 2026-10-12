DIM := "\u{1B}[2m"

[private]
_generate-help:
    @echo '{{YELLOW}}usage:{{NORMAL}} just generate [subcommand]'
    @echo ''
    @echo 'Generate release artifacts and documentation from applications.json.'
    @echo ''
    @echo '{{BOLD}}subcommands:{{NORMAL}}'
    @echo '  {{GREEN}}just generate{{NORMAL}}              {{DIM}}Generate all output files{{NORMAL}}'
    @echo '  {{GREEN}}just generate help{{NORMAL}}         {{DIM}}Show this help{{NORMAL}}'
    @echo '  {{GREEN}}just generate table{{NORMAL}}        {{DIM}}Generate markdown table{{NORMAL}}'
    @echo '  {{GREEN}}just generate readme{{NORMAL}}       {{DIM}}Generate README (includes table){{NORMAL}}'
    @echo '  {{GREEN}}just generate json{{NORMAL}}         {{DIM}}Generate the release JSON{{NORMAL}}'

[private]
_generate-all: _generate-readme _generate-json

[private]
_generate-table:
    @python scripts/generate-table.py src/applications.json ./pages/table.md

[private]
_generate-readme: _generate-table
    @python scripts/generate-readme.py \
        ./pages/header.md \
        ./pages/table.md \
        ./pages/faq.md \
        ./pages/footer.md

[private]
_generate-json:
    @python scripts/minify-json.py src/applications.json obtainium-emulation-pack-latest.json
