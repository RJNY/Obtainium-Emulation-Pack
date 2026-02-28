# Contributing

## Prerequisites

- Python 3.11+
- [just](https://github.com/casey/just) (task runner)
- Git

## Quick Start

```bash
# Clone the repository
git clone https://github.com/RJNY/Obtainium-Emulation-Pack.git
cd Obtainium-Emulation-Pack

# Make your changes to src/applications.json (or use just add-app)
just test              # verify configs resolve to real APKs
just build             # test, validate, normalize, and generate all output files
```

## Project Structure

```
justfile                         # Primary task runner (run `just` to see commands)
utility.just                     # Private helper recipes (imported by justfile)
src/
  applications.json              # Source of truth - all app definitions
scripts/
  constants.py                   # Shared constants and Obtainium source schema
  utils.py                       # Shared utility functions and .env loader
  help_formatter.py              # Styled argparse help formatter (ANSI colors)
  validate-json.py               # Validates applications.json
  test-apps.py                   # Live-tests configs resolve to downloadable APKs
  add-app.py                     # Interactive CLI to add a new app
  generate-table.py              # Generates the README table
  generate-readme.py             # Stitches markdown files into README
  minify-json.py                 # Creates release JSON files
  normalize-json.py              # Normalize key order and backfill defaults
  release.py                     # Automated release workflow (tag, push, gh release)
pages/
  header.md                      # README header/intro
  table.md                       # Generated - app tables (do not edit)
  faq.md                         # FAQ section
  footer.md                      # Short section linking here (stitched into README)
obtainium-emulation-pack-latest.json           # Standard release
obtainium-emulation-pack-dual-screen-latest.json # Dual-screen release
```

## Adding a New Application

### Option A: Quick Add (Recommended for GitHub apps)

Use the interactive CLI to quickly add a new app:

```bash
just add-app
```

This will:

- Prompt you for the GitHub URL
- Auto-detect the source, author, and app name
- Ask for the Android package ID and category
- Generate proper Obtainium settings
- Add the app to `applications.json`

> **Tip:** To find the package ID, open the app in Obtainium - the package ID is displayed directly below the source URL (e.g., `com.example.android`).

After running, execute `just build` to regenerate all files.

### Option B: Manual Add (For complex configs or non-GitHub sources)

#### Step 1: Export the app config from Obtainium

1. Open Obtainium on your device
2. Add the app you want to include (configure it how you want)
3. Long-press the app and select "Export"
4. Choose "Obtainium Export" format
5. Transfer the JSON to your computer

#### Step 2: Add the app to applications.json

Open `src/applications.json` and add your app to the `apps` array:

```json
{
  "id": "com.example.emulator",
  "url": "https://github.com/example/emulator",
  "author": "example",
  "name": "Example Emulator",
  "preferredApkIndex": 0,
  "additionalSettings": "{...}",
  "categories": ["Emulator"],
  "overrideSource": "GitHub"
}
```

#### Step 3: Add meta fields (optional)

Add a `meta` object to customize how the app appears:

```json
{
  "id": "com.example.emulator",
  "url": "https://github.com/example/emulator",
  "author": "example",
  "name": "Example Emulator",
  "preferredApkIndex": 0,
  "additionalSettings": "{...}",
  "categories": ["Emulator"],
  "overrideSource": "GitHub",
  "meta": {
    "nameOverride": "Example Emu",
    "urlOverride": "https://example-emu.org"
  }
}
```

#### Step 4: Validate, test, and regenerate

```bash
just validate          # check for structural errors
just test              # verify your app config resolves to a real APK
just build             # test, validate, normalize, and generate all output files
```

## CI

Pull requests and pushes to `main` are checked by GitHub Actions (single job):

1. **Validate** - structural checks, regex syntax, source types
2. **Test** - verifies all app configs resolve to real APKs
3. **Generate** - normalizes, generates README, builds release JSONs
4. **Diff check** - fails if generated files are out of date

All steps must pass before merging.

## Pre-Commit Checklist

Before committing, run `just build`, then verify:

- [ ] `just test` passes (all app configs resolve to downloadable APKs)
- [ ] `obtainium-emulation-pack-latest.json` has been updated
- [ ] `obtainium-emulation-pack-dual-screen-latest.json` has been updated
- [ ] `README.md` has been updated
- [ ] The README table shows a friendly application name (use `nameOverride` if not)
- [ ] The README table links to the correct homepage (use `urlOverride` if not)
- [ ] Beta apps are excluded with `meta.excludeFromExport: true`

## Available Commands

Run `just` to see all available commands. Recipes with `*args` accept `-h` for help.

| Command                 | Description                                                 |
| ----------------------- | ----------------------------------------------------------- |
| `just add-app`          | Interactive CLI to add a new app                            |
| `just validate`         | Validate applications.json (structure, regex, source types) |
| `just normalize`        | Normalize key order and backfill defaults                   |
| `just test`             | Live-test all app configs resolve to downloadable APKs      |
| `just test AppName`     | Live-test a single app by name (partial match)              |
| `just test --verbose`   | Live-test all apps with APK URL details                     |
| `just generate`         | Generate all output files (README, release JSONs)           |
| `just generate table`   | Generate the README table only                              |
| `just build`            | Test, validate, normalize, and generate all output files    |
| `just release`          | Tag, push, and create a GitHub release                      |

## Meta Field Reference

These fields in the `meta` object control how apps are processed:

| Field                 | Type   | Default | Description                                                         |
| --------------------- | ------ | ------- | ------------------------------------------------------------------- |
| `excludeFromExport`   | bool   | `false` | Exclude from both release JSON files. Use for beta/unstable apps.   |
| `excludeFromTable`    | bool   | `false` | Exclude from the README table.                                      |
| `includeInStandard`   | bool   | `true`  | Include in standard release. Set `false` for dual-screen-only apps. |
| `includeInDualScreen` | bool   | `true`  | Include in dual-screen release. Set `false` for standard-only apps. |
| `nameOverride`        | string | `null`  | Override the display name in the README table.                      |
| `urlOverride`         | string | `null`  | Override the homepage link in the README table.                     |

## Categories

Apps are organized into categories that appear as sections in the README table:

| Category       | Description                                                      |
| -------------- | ---------------------------------------------------------------- |
| `Emulator`     | Console/handheld emulators (Dolphin, RetroArch, PPSSPP, etc.)    |
| `Frontend`     | Emulator launchers and game library managers (Daijisho, Pegasus) |
| `Utilities`    | Helper apps (Syncthing, OdinTools, LED controllers, etc.)        |
| `PC Emulation` | Windows/PC game layers (Winlator, etc.)                          |
| `Streaming`    | Game streaming clients (Moonlight, etc.)                         |
| `Track Only`   | Version tracking without APK downloads (drivers, meta-packages)  |

An app can belong to multiple categories.

## Dual-Screen vs Standard

The pack supports two variants:

- **Standard** (`obtainium-emulation-pack-latest.json`): For regular Android devices
- **Dual-Screen** (`obtainium-emulation-pack-dual-screen-latest.json`): For dual-screen devices like LG V60/Velvet

Some apps have dual-screen-specific forks (e.g., Cemu, MelonDS). Use the `includeInStandard` and `includeInDualScreen` flags to control which variant(s) include each app.

**Why this matters:** Apps with the same Android package ID (`id` field) will conflict in Obtainium. If two apps share an ID (like standard Cemu and dual-screen Cemu), they **must not** both appear in the same JSON file.

Example: Standard Cemu excluded from dual-screen, dual-screen fork excluded from standard:

```json
// Standard Cemu - exclude from dual-screen JSON
{
  "id": "info.cemu.cemu",
  "name": "Cemu",
  "url": "https://github.com/SSimco/Cemu",
  "categories": ["Emulator"],
  "meta": { "includeInDualScreen": false }
}

// Dual-screen Cemu fork - exclude from standard JSON
{
  "id": "info.cemu.cemu",
  "name": "Cemu",
  "url": "https://github.com/SapphireRhodonite/Cemu",
  "categories": ["Dual Screen"],
  "meta": { "includeInStandard": false }
}
```

## Choosing the Right Category and Variant

Use this decision tree:

1. **Is this app device-specific?** (e.g., AYN Thor frontend)

   - Yes: Set `includeInStandard: false` and use appropriate category
   - No: Continue to step 2

2. **Does this app share an ID with another app in the pack?** (e.g., forks, beta builds, dual-screen variants)

   - Yes: Only one app per ID can be in each release JSON. Options:
     - Use `includeInStandard`/`includeInDualScreen` to split between variants
     - Use `excludeFromExport: true` on the less stable version (e.g., nightly builds)
   - No: App can be in both variants (default)

3. **Is this app stable and ready for users?**
   - Yes: Include normally
   - No: Set `excludeFromExport: true` (still visible in table but not in release JSONs)
