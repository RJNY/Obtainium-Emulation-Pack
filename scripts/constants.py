"""Shared constants for Obtainium Emulation Pack scripts."""

from typing import Any, NamedTuple

SRC_FILE = "src/applications.json"
PAGES_DIR = "pages"
TABLE_FILE = "pages/table.md"

REDIRECT_URL = "http://apps.obtainium.imranr.dev/redirect.html"
OBTAINIUM_SCHEME = "obtainium://app/"

VARIANTS = ("standard", "dual-screen")

GITHUB_NOREPLY_SUFFIX = "@users.noreply.github.com"

# Valid overrideSource values (runtime type names from Obtainium)
VALID_SOURCES = {
    "GitHub",
    "GitLab",
    "Codeberg",
    "FDroid",
    "FDroidRepo",
    "IzzyOnDroid",
    "SourceHut",
    "APKPure",
    "Aptoide",
    "Uptodown",
    "HuaweiAppGallery",
    "Tencent",
    "VivoAppStore",
    "RuStore",
    "Farsroid",
    "CoolApk",
    "RockMods",
    "LiteAPKs",
    "Jenkins",
    "APKMirror",
    "TelegramApp",
    "NeutronCode",
    "SourceForge",
    "DirectAPKLink",
    "HTML",
}

# URL host-to-source mapping for auto-detection
SOURCE_HOST_MAP = {
    "github.com": "GitHub",
    "gitlab.com": "GitLab",
    "codeberg.org": "Codeberg",
    "f-droid.org": "FDroid",
    "android.izzysoft.de": "IzzyOnDroid",
    "git.sr.ht": "SourceHut",
    "apkpure.net": "APKPure",
    "aptoide.com": "Aptoide",
    "uptodown.com": "Uptodown",
    "appgallery.huawei.com": "HuaweiAppGallery",
    "sj.qq.com": "Tencent",
    "h5.appstore.vivo.com.cn": "VivoAppStore",
    "rustore.ru": "RuStore",
    "farsroid.com": "Farsroid",
    "coolapk.com": "CoolApk",
    "rockmods.net": "RockMods",
    "liteapks.com": "LiteAPKs",
    "apkmirror.com": "APKMirror",
    "telegram.org": "TelegramApp",
    "neutroncode.com": "NeutronCode",
    "sourceforge.net": "SourceForge",
}

# Deprecated keys still accepted for backward compatibility.
# Obtainium auto-migrates these on load (see appJSONCompatibilityModifiers
# in lib/providers/source_provider.dart). New configs should use the
# replacement key instead.
DEPRECATED_SETTINGS_KEYS: dict[str, str] = {
    "dontSortReleasesList": "sortMethodChoice",
    "supportFixedAPKURL": "defaultPseudoVersioningMethod",
    "sortByFileNamesNotLinks": "sortByLastLinkSegment",
}


# ---------------------------------------------------------------------------
# Obtainium additionalSettings schema
# Single source of truth for key metadata: default value, applicable sources,
# whether the value is a regex pattern. Derived from Obtainium source code:
# lib/app_sources/*.dart. Reference: ~/code/Obtainium
#
# Dict insertion order defines the canonical key ordering used by
# normalize-json.py and export hydration.
# ---------------------------------------------------------------------------

ALL_SOURCES = frozenset(VALID_SOURCES)

_GITHUB_LIKE = frozenset({"GitHub", "Codeberg"})

_DEFAULT_USER_AGENT_HEADER = [
    {"requestHeader": "User-Agent: Mozilla/5.0 (Linux; Android 10; K) "
     "AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/114.0.0.0 Mobile Safari/537.36"}
]


class SettingDef(NamedTuple):
    default: Any
    sources: frozenset[str]
    is_regex: bool = False


SETTINGS_SCHEMA: dict[str, SettingDef] = {
    # --- GitHub / Codeberg source-specific ---
    "includePrereleases":           SettingDef(False,  _GITHUB_LIKE),
    "fallbackToOlderReleases":      SettingDef(True,   frozenset({"GitHub", "Codeberg", "GitLab", "SourceHut", "APKPure", "APKMirror"})),
    "filterReleaseTitlesByRegEx":   SettingDef("",     frozenset({"GitHub", "Codeberg", "APKMirror"}), is_regex=True),
    "filterReleaseNotesByRegEx":    SettingDef("",     _GITHUB_LIKE, is_regex=True),
    "verifyLatestTag":              SettingDef(False,  _GITHUB_LIKE),
    "sortMethodChoice":             SettingDef("date", _GITHUB_LIKE),
    "useLatestAssetDateAsReleaseDate": SettingDef(False, _GITHUB_LIKE),
    "releaseTitleAsVersion":        SettingDef(False,  _GITHUB_LIKE),
    "github-creds":                 SettingDef("",     frozenset({"GitHub"})),
    "GHReqPrefix":                  SettingDef("",     frozenset({"GitHub"})),

    # --- GitLab source-specific ---
    "gitlab-creds":                 SettingDef("",     frozenset({"GitLab"})),

    # --- FDroid / IzzyOnDroid source-specific ---
    "filterVersionsByRegEx":        SettingDef("",     frozenset({"FDroid", "IzzyOnDroid"}), is_regex=True),
    "trySelectingSuggestedVersionCode": SettingDef(True, frozenset({"FDroid", "IzzyOnDroid", "FDroidRepo"})),
    "autoSelectHighestVersionCode": SettingDef(False,  frozenset({"FDroid", "IzzyOnDroid"})),

    # --- FDroidRepo source-specific ---
    "appIdOrName":                  SettingDef("",     frozenset({"FDroidRepo"})),
    "pickHighestVersionCode":       SettingDef(False,  frozenset({"FDroidRepo"})),

    # --- APKPure source-specific ---
    "stayOneVersionBehind":         SettingDef(False,  frozenset({"APKPure"})),
    "useFirstApkOfVersion":         SettingDef(True,   frozenset({"APKPure", "Farsroid"})),

    # --- HTML source-specific ---
    "intermediateLink":             SettingDef([],     frozenset({"HTML"})),
    "customLinkFilterRegex":        SettingDef("",     frozenset({"HTML"}), is_regex=True),
    "filterByLinkText":             SettingDef(False,  frozenset({"HTML"})),
    "matchLinksOutsideATags":       SettingDef(False,  frozenset({"HTML"})),
    "skipSort":                     SettingDef(False,  frozenset({"HTML"})),
    "reverseSort":                  SettingDef(False,  frozenset({"HTML"})),
    "sortByLastLinkSegment":        SettingDef(False,  frozenset({"HTML"})),
    "versionExtractWholePage":      SettingDef(False,  frozenset({"HTML"})),
    "requestHeader":                SettingDef(_DEFAULT_USER_AGENT_HEADER, frozenset({"HTML", "DirectAPKLink"})),
    "defaultPseudoVersioningMethod": SettingDef("partialAPKHash", frozenset({"HTML", "DirectAPKLink"})),

    # --- Common keys (all sources) ---
    "trackOnly":                    SettingDef(False,  ALL_SOURCES),
    "versionExtractionRegEx":       SettingDef("",     ALL_SOURCES, is_regex=True),
    "matchGroupToUse":              SettingDef("",     ALL_SOURCES),
    "versionDetection":             SettingDef(True,   ALL_SOURCES),
    "releaseDateAsVersion":         SettingDef(False,  ALL_SOURCES),
    "useVersionCodeAsOSVersion":    SettingDef(False,  ALL_SOURCES),
    "apkFilterRegEx":               SettingDef("",     ALL_SOURCES, is_regex=True),
    "invertAPKFilter":              SettingDef(False,  ALL_SOURCES),
    "autoApkFilterByArch":          SettingDef(True,   ALL_SOURCES),
    "appName":                      SettingDef("",     ALL_SOURCES),
    "appAuthor":                    SettingDef("",     ALL_SOURCES),
    "shizukuPretendToBeGooglePlay": SettingDef(False,  ALL_SOURCES),
    "allowInsecure":                SettingDef(False,  ALL_SOURCES),
    "exemptFromBackgroundUpdates":  SettingDef(False,  ALL_SOURCES),
    "skipUpdateNotifications":      SettingDef(False,  ALL_SOURCES),
    "about":                        SettingDef("",     ALL_SOURCES),
    "refreshBeforeDownload":        SettingDef(False,  ALL_SOURCES),
    "includeZips":                  SettingDef(False,  ALL_SOURCES),
    "zippedApkFilterRegEx":         SettingDef("",     ALL_SOURCES, is_regex=True),
}

# ---------------------------------------------------------------------------
# Derived views - computed from SETTINGS_SCHEMA so there's one place to update
# ---------------------------------------------------------------------------

COMMON_SETTINGS_KEYS: set[str] = {
    key for key, s in SETTINGS_SCHEMA.items() if s.sources == ALL_SOURCES
}

SOURCE_SPECIFIC_KEYS: dict[str, set[str]] = {}
for _source in VALID_SOURCES:
    _keys = {key for key, s in SETTINGS_SCHEMA.items() if _source in s.sources and s.sources != ALL_SOURCES}
    if _keys:
        SOURCE_SPECIFIC_KEYS[_source] = _keys

REGEX_SETTINGS_KEYS: set[str] = {
    key for key, s in SETTINGS_SCHEMA.items() if s.is_regex
}
