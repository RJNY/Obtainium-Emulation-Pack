# Development & Contribution

## Contributing

You are welcome to make a PR with a contribution.

### 1. Making changes to the pack

You'll want to directly edit only things in either `./pages/` or `./src/`. Everything else should be designed to update
through scripts. Including the README!

...why template out the README? Because that table is very cumbersome to update on every change.

### 2. Pre-Commit

Before you commit, make sure to run `make release`.
This will:

- template the README
- update the minified json release file

## Development Tips

### Meta field options

My scripts will do specific actions if a `meta` field is present

| key              | type | default | description                                    |
| ---------------- | ---- | ------- | ---------------------------------------------- |
| exludeFromExport | bool | false   | Excludes the app from the release export json. |
| exludeFromTable  | bool | false   | Excludes the app from the README table.        |
