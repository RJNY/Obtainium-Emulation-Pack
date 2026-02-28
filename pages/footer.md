## Contributing

Want to add an app or fix a config? See the [Contributing Guide](CONTRIBUTING.md) for setup instructions, how to add apps, and the pre-commit checklist.

Quick version:

```bash
git clone https://github.com/RJNY/Obtainium-Emulation-Pack.git
cd Obtainium-Emulation-Pack

# Add or edit apps in src/applications.json (or use just add-app)
just test      # verify configs resolve to real APKs
just build     # test, validate, normalize, and generate all output files
```
