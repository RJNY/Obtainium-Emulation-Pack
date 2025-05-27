## FAQ

### Why do some applications say TRACK ONLY?

As the name implies, these application versions are only tracked, not pulled.
This was done because we _can't_ pull these resources, but you may still care to know when these
resources have updates so you can pull them manually. For example: NetherSX2 can't provide an APK
for legal reasons, but you'll get update notifications so you don't have to manually check or be
stuck with outdated resources.

### How do I use TRACK ONLY resources?

When you get notified of an update to your track only resource:

- visit the link to your resource
- download it manually
- in obtainium > click resource > click "Mark Updated"

### How do I updated Obtainium Emulation Pack?

Same as install method. It'll update existing resources.
It will not remove any other resources you've added.

### A new switch emulator has released! Can you add it?

No.

### A note about stable, beta, nightly and canary versions of the same app

You cannot install more than one version of the same app. For example: You must choose between RetroArch (stable) or RetroArch (nightly). You cannot have both.

### How does this work?

Obtainium allows you to filter for links on a page using regular expression (regex)
It also allows you to follow multiple links using regex.
see <https://regexr.com/7rmf7> for a basic example of how this works.

### Can this break?

Yes. Absolutely it can.
Any of the scrapers that use regex can break if the maintainer changes their page.
The applications pulling from GitHub are more stable and less likely to break.
