"""Shared constants for Obtainium Emulation Pack scripts."""

SRC_FILE = "src/applications.json"
PAGES_DIR = "pages"
TABLE_FILE = "pages/table.md"

REDIRECT_URL = "http://apps.obtainium.imranr.dev/redirect.html"
OBTAINIUM_SCHEME = "obtainium://app/"

VARIANTS = ("standard", "dual-screen")

GITHUB_NOREPLY_SUFFIX = "@users.noreply.github.com"

# ---------------------------------------------------------------------------
# Obtainium source types and settings schema
# Derived from Obtainium source code: lib/app_sources/*.dart
# Reference: ~/code/Obtainium
# ---------------------------------------------------------------------------

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

# Common additionalSettings keys valid for all source types
COMMON_SETTINGS_KEYS = {
    "trackOnly",
    "versionExtractionRegEx",
    "matchGroupToUse",
    "versionDetection",
    "useVersionCodeAsOSVersion",
    "apkFilterRegEx",
    "invertAPKFilter",
    "autoApkFilterByArch",
    "appName",
    "appAuthor",
    "shizukuPretendToBeGooglePlay",
    "allowInsecure",
    "exemptFromBackgroundUpdates",
    "skipUpdateNotifications",
    "about",
    "refreshBeforeDownload",
    "releaseDateAsVersion",
    "includeZips",
    "zippedApkFilterRegEx",
}

# Source-specific additionalSettings keys
SOURCE_SPECIFIC_KEYS: dict[str, set[str]] = {
    "GitHub": {
        "includePrereleases",
        "fallbackToOlderReleases",
        "filterReleaseTitlesByRegEx",
        "filterReleaseNotesByRegEx",
        "verifyLatestTag",
        "sortMethodChoice",
        "useLatestAssetDateAsReleaseDate",
        "releaseTitleAsVersion",
        "github-creds",
        "GHReqPrefix",
    },
    "GitLab": {
        "fallbackToOlderReleases",
        "gitlab-creds",
    },
    "Codeberg": {
        # Inherits GitHub's settings
        "includePrereleases",
        "fallbackToOlderReleases",
        "filterReleaseTitlesByRegEx",
        "filterReleaseNotesByRegEx",
        "verifyLatestTag",
        "sortMethodChoice",
        "useLatestAssetDateAsReleaseDate",
        "releaseTitleAsVersion",
    },
    "FDroid": {
        "filterVersionsByRegEx",
        "trySelectingSuggestedVersionCode",
        "autoSelectHighestVersionCode",
    },
    "IzzyOnDroid": {
        # Inherits FDroid's settings
        "filterVersionsByRegEx",
        "trySelectingSuggestedVersionCode",
        "autoSelectHighestVersionCode",
    },
    "FDroidRepo": {
        "appIdOrName",
        "pickHighestVersionCode",
        "trySelectingSuggestedVersionCode",
    },
    "SourceHut": {
        "fallbackToOlderReleases",
    },
    "APKPure": {
        "fallbackToOlderReleases",
        "stayOneVersionBehind",
        "useFirstApkOfVersion",
    },
    "APKMirror": {
        "fallbackToOlderReleases",
        "filterReleaseTitlesByRegEx",
    },
    "Farsroid": {
        "useFirstApkOfVersion",
    },
    "HTML": {
        "intermediateLink",
        "customLinkFilterRegex",
        "filterByLinkText",
        "matchLinksOutsideATags",
        "skipSort",
        "reverseSort",
        "sortByLastLinkSegment",
        "versionExtractWholePage",
        "requestHeader",
        "defaultPseudoVersioningMethod",
    },
    "DirectAPKLink": {
        "requestHeader",
        "defaultPseudoVersioningMethod",
    },
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

# Settings keys that contain regex patterns (should be validated)
REGEX_SETTINGS_KEYS = {
    "apkFilterRegEx",
    "versionExtractionRegEx",
    "filterReleaseTitlesByRegEx",
    "filterReleaseNotesByRegEx",
    "customLinkFilterRegex",
    "filterVersionsByRegEx",
    "zippedApkFilterRegEx",
}
