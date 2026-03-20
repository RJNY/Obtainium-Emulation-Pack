## FAQ

<details>
<summary><strong>Can I install both stable and nightly versions of the same app?</strong></summary>
<br>
No. Android only allows one app per package ID. You must choose between stable and nightly for apps like RetroArch, MelonDS, Eden, etc. The pack includes stable versions by default - use the individual "Add to Obtainium!" links above to switch to a nightly if you prefer.
</details>

<details>
<summary><strong>How do I update the pack?</strong></summary>
<br>
Same as the initial install. Re-import the latest JSON and it will update existing configs without removing any apps you've added separately.
</details>

<details>
<summary><strong>What are the two JSON variants?</strong></summary>
<br>
Some emulators have dual-screen forks (Cemu, MelonDS) that share the same Android package ID as the standard version. Since Obtainium can't have two apps with the same ID, the pack ships two variants:
<br><br>

- **Standard** - for AYN Odin, Retroid Pocket, and most Android devices
- **Dual-Screen** - for AYN Thor, Anbernic RG DS, and other dual-screen devices, with dual-screen forks swapped in plus dual-screen utilities

</details>

<details>
<summary><strong>Why do some applications say TRACK ONLY?</strong></summary>
<br>
As the name implies, these application versions are only tracked, not pulled.
This was done because we <em>can't</em> pull these resources, but you may still care to know when these
resources have updates so you can pull them manually. For example: GPU driver repos don't publish
APKs, but you'll get update notifications so you don't have to manually check for new releases.
</details>

<details>
<summary><strong>How do I use TRACK ONLY resources?</strong></summary>
<br>
When you get notified of an update to your track only resource:
<br><br>

- visit the link to your resource
- download it manually
- in obtainium > click resource > click "Mark Updated"

</details>

<details>
<summary><strong>Can configs break?</strong></summary>
<br>
Yes. Apps sourced from websites (HTML scraping) can break if the site changes its layout. GitHub-sourced apps are more stable. The pack is <a href="https://github.com/RJNY/Obtainium-Emulation-Pack/actions">tested daily</a> and broken configs are flagged automatically.
</details>