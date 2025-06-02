## Development & Contribution

### Contributing

You are welcome to make a PR with a contribution.

#### 1. Making changes to the pack

##### Adding / Removing Applications

To add, update or remove an application, you need to:

1. make edits to `src/applications.json`.
1. run `make release` in the root directory

#### 2. Pre-Commit

Before you commit, make sure to run `make release`.
This will:

- template the README and update the table
- update the minified json release file

After running `make release`, please check for the following:

- `obtainium-emulation-pack-latest.json` has been updated
- `README.md` has been updated.
- Does the README table generate a friendly application name? If not, see documentation for `nameOverride`
- Does the README table generate a friendly applicaation URL? If not, see documentation for `urlOverride`
- Is the application in beta? If so, please exclude it from the JSON using `meta.excludeFromExport`

### Developer Documentation

#### Meta field options

My scripts will do specific actions if specific application keys are present in the
`application.json`

| key                   | type   | default | description                                                                                                               |
| --------------------- | ------ | ------- | ------------------------------------------------------------------------------------------------------------------------- |
| meta.exludeFromExport | bool   | false   | Excludes the app from the release export json.                                                                            |
| meta.exludeFromTable  | bool   | false   | Excludes the app from the README table.                                                                                   |
| meta.nameOverride     | string | null    | Overwrite emulator name, useful if the default name is not human friendly                                                 |
| meta.urlOverride      | string | null    | Overwrite the application preview link. If empty, the readme table will use the application scraper link as the homepage. |
