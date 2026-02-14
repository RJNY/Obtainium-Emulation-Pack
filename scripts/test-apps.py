#!/usr/bin/env python3
"""Live validation that app configs can resolve to downloadable APKs.

Usage:
    python scripts/test-apps.py src/applications.json
    python scripts/test-apps.py src/applications.json Dolphin
    python scripts/test-apps.py src/applications.json --id org.dolphinemu.dolphinemu

Set GITHUB_TOKEN in .env or environment to avoid API rate limits.
"""

import json
import os
import re
import ssl
import sys
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from utils import load_dotenv

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; K) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Mobile Safari/537.36"
)
REQUEST_TIMEOUT = 30
MAX_RELEASES_TO_CHECK = 25
APK_EXTENSIONS = (".apk", ".xapk")
MAX_STORED_APK_URLS = 5
MAX_DISPLAYED_APK_URLS = 3


def _make_request(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = REQUEST_TIMEOUT,
) -> tuple[str, dict[str, str], str]:
    """Returns (body, response_headers, final_url). Allows self-signed certs."""
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)

    req = Request(url, headers=hdrs)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    resp = urlopen(req, timeout=timeout, context=ctx)
    body = resp.read().decode("utf-8", errors="replace")
    resp_headers = {k.lower(): v for k, v in resp.headers.items()}
    return body, resp_headers, resp.url


def _fetch_json(
    url: str,
    headers: dict[str, str] | None = None,
) -> tuple[Any, dict[str, str]]:
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    body, resp_headers, _ = _make_request(url, headers=hdrs)
    return json.loads(body), resp_headers


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(urljoin(self.base_url, value))


def _extract_links(html_body: str, base_url: str) -> list[str]:
    parser = LinkExtractor(base_url)
    parser.feed(html_body)
    return parser.links


def _filter_links_by_regex(links: list[str], regex: str) -> list[str]:
    pattern = re.compile(regex)
    return [link for link in links if pattern.search(link)]


def _filter_links_by_extension(links: list[str]) -> list[str]:
    return [link for link in links if any(link.lower().endswith(ext) for ext in APK_EXTENSIONS)]


def _sort_links(
    links: list[str],
    skip_sort: bool = False,
    reverse_sort: bool = False,
    sort_by_last_segment: bool = False,
) -> list[str]:
    if skip_sort:
        return links
    key = (lambda u: u.rsplit("/", 1)[-1]) if sort_by_last_segment else None
    result = sorted(links, key=key)
    if reverse_sort:
        result.reverse()
    return result


def _format_filter_context(**filters: str) -> str:
    """Build a diagnostic string of active filters, e.g. ', apkFilter=foo, titleFilter=bar'."""
    parts = [f", {name}={value}" for name, value in filters.items() if value]
    return "".join(parts)


def _apply_apk_filter(urls: list[str], settings: dict[str, Any]) -> list[str]:
    apk_filter = settings.get("apkFilterRegEx", "")
    if not apk_filter or not urls:
        return urls
    pattern = re.compile(apk_filter)
    if settings.get("invertAPKFilter", False):
        return [u for u in urls if not pattern.search(u)]
    return [u for u in urls if pattern.search(u)]


def _extract_version(raw_version: str, settings: dict[str, Any]) -> tuple[str, str | None]:
    """Apply versionExtractionRegEx. Returns (version, warning_or_none)."""
    regex_str = settings.get("versionExtractionRegEx", "")
    if not regex_str or not raw_version:
        return raw_version, None
    try:
        match = re.search(regex_str, raw_version)
        if match:
            group_to_use = settings.get("matchGroupToUse", "")
            if group_to_use:
                return match.expand(group_to_use), None
            elif match.groups():
                return match.group(1), None
            return match.group(0), None
    except re.error as e:
        return raw_version, f"versionExtractionRegEx error: {e}"
    return raw_version, None


def _check_apk_index(app: dict[str, Any], apk_count: int) -> str | None:
    """Returns a warning string if preferredApkIndex is out of bounds."""
    index = app.get("preferredApkIndex", 0)
    if apk_count > 0 and index >= apk_count:
        return f"preferredApkIndex={index} but only {apk_count} APKs found"
    return None


class TestResult:
    def __init__(self, app_name: str, app_id: str, source: str, url: str):
        self.app_name = app_name
        self.app_id = app_id
        self.source = source
        self.url = url
        self.passed = False
        self.version: str | None = None
        self.apk_count = 0
        self.apk_urls: list[str] = []
        self.error: str | None = None
        self.warnings: list[str] = []
        self.duration_ms = 0

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"{status}: {self.app_name} ({self.source})"


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _parse_owner_repo(url: str) -> tuple[str, str, str]:
    """Returns (owner, repo, host)."""
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from: {url}")
    return parts[0], parts[1], parsed.netloc


def _collect_apks_from_assets(assets: list[dict], settings: dict[str, Any]) -> list[str]:
    """Extract APK download URLs from a GitHub/Codeberg release's asset list."""
    urls = []
    for asset in assets:
        name = asset.get("name", "").lower()
        dl_url = asset.get("browser_download_url", "")
        if any(name.endswith(ext) for ext in APK_EXTENSIONS):
            urls.append(dl_url)
        elif name.endswith(".zip") and settings.get("includeZips", False):
            urls.append(dl_url)
    return urls


def _find_release_with_apks(
    releases: list[dict],
    settings: dict[str, Any],
    title_filter: re.Pattern | None = None,
    notes_filter: re.Pattern | None = None,
) -> tuple[dict | None, list[str]]:
    """Walk releases and return the first one with matching APK assets.

    Returns (target_release, filtered_apk_urls). For track-only apps,
    falls back to any release with a tag_name even if no APKs found.
    """
    include_prereleases = settings.get("includePrereleases", False)
    track_only = settings.get("trackOnly", False)
    fallback = settings.get("fallbackToOlderReleases", True)

    for release in releases:
        if release.get("draft", False):
            continue
        if release.get("prerelease", False) and not include_prereleases:
            continue

        if title_filter:
            name = release.get("name", "") or ""
            if not title_filter.search(name):
                continue
        if notes_filter:
            body = release.get("body", "") or ""
            if not notes_filter.search(body):
                continue

        apk_urls = _collect_apks_from_assets(release.get("assets", []), settings)
        apk_urls = _apply_apk_filter(apk_urls, settings)

        if not apk_urls and not track_only:
            if fallback:
                continue
            break

        return release, apk_urls

    # Track-only fallback: any release with a version tag
    if track_only:
        for release in releases:
            if release.get("tag_name"):
                return release, []

    return None, []


def test_github(app: dict[str, Any], settings: dict[str, Any]) -> TestResult:
    result = TestResult(app["name"], app["id"], "GitHub", app["url"])

    try:
        owner, repo, _ = _parse_owner_repo(app["url"])
    except ValueError as e:
        result.error = str(e)
        return result

    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page={MAX_RELEASES_TO_CHECK}"

    try:
        releases, resp_headers = _fetch_json(api_url, headers=_github_headers())
    except Exception as e:
        result.error = f"GitHub API error: {e}"
        if "403" in str(e) or "rate" in str(e).lower():
            result.error += " (rate limited - set GITHUB_TOKEN env var)"
        return result

    remaining = resp_headers.get("x-ratelimit-remaining", "")
    if remaining and int(remaining) < 10:
        result.warnings.append(f"GitHub API rate limit low: {remaining} remaining")

    if not releases:
        result.error = "No releases found"
        return result

    title_str = settings.get("filterReleaseTitlesByRegEx", "")
    notes_str = settings.get("filterReleaseNotesByRegEx", "")
    title_regex = re.compile(title_str) if title_str else None
    notes_regex = re.compile(notes_str) if notes_str else None

    target, apk_urls = _find_release_with_apks(
        releases, settings, title_filter=title_regex, notes_filter=notes_regex
    )

    if not target:
        prerelease_state = "on" if settings.get("includePrereleases", False) else "off"
        context = _format_filter_context(
            titleFilter=title_str,
            apkFilter=settings.get("apkFilterRegEx", ""),
        )
        result.error = (
            f"No releases with matching APK assets found "
            f"(checked {len(releases)} releases, prereleases={prerelease_state}{context})"
        )
        return result

    version = target.get("tag_name", "") or target.get("name", "")
    version, warning = _extract_version(version, settings)
    if warning:
        result.warnings.append(warning)

    index_warning = _check_apk_index(app, len(apk_urls))
    if index_warning:
        result.warnings.append(index_warning)

    result.passed = True
    result.version = version
    result.apk_count = len(apk_urls)
    result.apk_urls = apk_urls
    return result


def test_codeberg(app: dict[str, Any], settings: dict[str, Any]) -> TestResult:
    result = TestResult(app["name"], app["id"], "Codeberg", app["url"])

    try:
        owner, repo, host = _parse_owner_repo(app["url"])
    except ValueError as e:
        result.error = str(e)
        return result

    api_url = f"https://{host}/api/v1/repos/{owner}/{repo}/releases?limit={MAX_RELEASES_TO_CHECK}"

    try:
        releases, _ = _fetch_json(api_url)
    except Exception as e:
        result.error = f"Codeberg API error: {e}"
        return result

    if not releases:
        result.error = "No releases found"
        return result

    target, apk_urls = _find_release_with_apks(releases, settings)

    if not target:
        result.error = "No releases with matching APK assets"
        return result

    version = target.get("tag_name", "") or target.get("name", "")
    version, warning = _extract_version(version, settings)
    if warning:
        result.warnings.append(warning)

    index_warning = _check_apk_index(app, len(apk_urls))
    if index_warning:
        result.warnings.append(index_warning)

    result.passed = True
    result.version = version
    result.apk_count = len(apk_urls)
    result.apk_urls = apk_urls
    return result


def _parse_request_headers(settings: dict[str, Any]) -> dict[str, str]:
    headers = {}
    for header_obj in settings.get("requestHeader", []):
        if isinstance(header_obj, dict):
            header_str = header_obj.get("requestHeader", "")
            if ": " in header_str:
                key, val = header_str.split(": ", 1)
                headers[key] = val
    return headers


def _follow_intermediate_links(
    start_url: str,
    steps: list[dict],
    headers: dict[str, str],
) -> tuple[str, str | None]:
    """Walk intermediateLink chain. Returns (final_url, error_or_none)."""
    current_url = start_url
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        try:
            body, _, final_url = _make_request(current_url, headers=headers)
        except Exception as e:
            return current_url, f"Failed to fetch intermediate URL ({current_url}): {e}"

        links = _extract_links(body, final_url)
        step_regex = step.get("customLinkFilterRegex", "")
        if step_regex:
            links = _filter_links_by_regex(links, step_regex)

        links = _sort_links(
            links,
            skip_sort=step.get("skipSort", False),
            reverse_sort=step.get("reverseSort", False),
            sort_by_last_segment=step.get("sortByLastLinkSegment", False),
        )

        if not links:
            return current_url, (
                f"Intermediate link step {i} found no matching links "
                f"(url={current_url}, regex={step_regex!r})"
            )

        current_url = links[-1]  # Obtainium takes the last link after sorting

    return current_url, None


def test_html(app: dict[str, Any], settings: dict[str, Any]) -> TestResult:
    result = TestResult(app["name"], app["id"], "HTML", app["url"])

    req_headers = _parse_request_headers(settings)
    intermediate_links = settings.get("intermediateLink", [])

    current_url, error = _follow_intermediate_links(app["url"], intermediate_links, req_headers)
    if error:
        result.error = error
        return result

    try:
        body, _, final_url = _make_request(current_url, headers=req_headers)
    except Exception as e:
        result.error = f"Failed to fetch final URL ({current_url}): {e}"
        return result

    links = _extract_links(body, final_url)
    custom_regex = settings.get("customLinkFilterRegex", "")
    apk_links = _filter_links_by_regex(links, custom_regex) if custom_regex else _filter_links_by_extension(links)
    apk_links = _apply_apk_filter(apk_links, settings)

    track_only = settings.get("trackOnly", False)
    if not apk_links and not track_only:
        context = _format_filter_context(
            customLinkFilterRegex=custom_regex,
            apkFilterRegEx=settings.get("apkFilterRegEx", ""),
        )
        result.error = (
            f"No APK links found on page ({current_url}{context}, "
            f"{len(links)} total links on page)"
        )
        return result

    version = None
    version_regex_str = settings.get("versionExtractionRegEx", "")
    if version_regex_str:
        extract_whole_page = settings.get("versionExtractWholePage", False)
        if extract_whole_page:
            search_text = body
        elif apk_links:
            search_text = apk_links[-1]  # Obtainium uses last link
        else:
            search_text = ""

        version, warning = _extract_version(search_text, settings)
        if warning:
            result.warnings.append(warning)

    if not version:
        pseudo_method = settings.get("defaultPseudoVersioningMethod", "")
        if pseudo_method:
            version = f"<pseudo:{pseudo_method}>"
        else:
            result.warnings.append("No version extracted (no regex match, no pseudo-method)")

    index_warning = _check_apk_index(app, len(apk_links))
    if index_warning:
        result.warnings.append(index_warning)

    result.passed = True
    result.version = version
    result.apk_count = len(apk_links)
    result.apk_urls = apk_links[:MAX_STORED_APK_URLS]
    return result


def _effective_source(app: dict[str, Any]) -> str:
    override = app.get("overrideSource")
    if override:
        return override

    host = urlparse(app.get("url", "")).netloc.lower().lstrip("www.")
    if "github.com" in host:
        return "GitHub"
    if "gitlab.com" in host:
        return "GitLab"
    if "codeberg.org" in host:
        return "Codeberg"
    if "f-droid.org" in host:
        return "FDroid"
    return "HTML"


def test_app(app: dict[str, Any]) -> TestResult:
    source = _effective_source(app)

    settings_str = app.get("additionalSettings", "{}")
    try:
        settings = json.loads(settings_str) if isinstance(settings_str, str) else {}
    except json.JSONDecodeError:
        result = TestResult(app.get("name", "?"), app.get("id", "?"), source, app.get("url", "?"))
        result.error = "Cannot parse additionalSettings JSON"
        return result

    start = time.monotonic()

    if source == "GitHub":
        result = test_github(app, settings)
    elif source == "Codeberg":
        result = test_codeberg(app, settings)
    elif source in ("HTML", "DirectAPKLink"):
        result = test_html(app, settings)
    else:
        result = TestResult(app.get("name", "?"), app.get("id", "?"), source, app.get("url", "?"))
        result.passed = True
        result.warnings.append(f"Skipped: source type '{source}' not yet supported")

    result.duration_ms = int((time.monotonic() - start) * 1000)
    return result


def print_result(result: TestResult, verbose: bool = False) -> None:
    status = "\033[32mPASS\033[0m" if result.passed else "\033[31mFAIL\033[0m"
    version_str = f" v{result.version}" if result.version else ""
    apk_str = f" ({result.apk_count} APKs)" if result.apk_count else ""

    print(f"  {status}  {result.app_name}{version_str}{apk_str} [{result.duration_ms}ms]")

    if result.error:
        print(f"         Error: {result.error}")
    for warning in result.warnings:
        print(f"         \033[33mWarn\033[0m: {warning}")
    if verbose and result.apk_urls:
        for url in result.apk_urls[:MAX_DISPLAYED_APK_URLS]:
            print(f"         APK: {url}")


def main() -> int:
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python test-apps.py <json_file> [name_filter] [--id <app_id>] [--verbose]")
        print()
        print("Examples:")
        print("  python test-apps.py src/applications.json              # test all apps")
        print("  python test-apps.py src/applications.json Dolphin      # filter by name")
        print("  python test-apps.py src/applications.json --id org.dolphinemu.dolphinemu")
        print("  python test-apps.py src/applications.json --verbose    # show APK URLs")
        return 1

    json_file = sys.argv[1]
    args = sys.argv[2:]

    verbose = "--verbose" in args
    if verbose:
        args.remove("--verbose")

    id_filter = None
    if "--id" in args:
        idx = args.index("--id")
        if idx + 1 < len(args):
            id_filter = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            print("Error: --id requires an argument")
            return 1

    name_filter = " ".join(args).lower() if args else None

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading {json_file}: {e}")
        return 1

    apps = data.get("apps", [])
    if id_filter:
        apps = [a for a in apps if a.get("id") == id_filter]
    elif name_filter:
        apps = [a for a in apps if name_filter in a.get("name", "").lower()]

    if not apps:
        print("No apps matched the filter.")
        return 1

    has_token = bool(os.environ.get("GITHUB_TOKEN"))
    github_count = sum(1 for a in apps if _effective_source(a) == "GitHub")
    if github_count > 0 and not has_token:
        print(
            f"\033[33mNote\033[0m: {github_count} GitHub apps to test, "
            "but GITHUB_TOKEN is not set. You may hit rate limits.\n"
            "  Set it with: export GITHUB_TOKEN=<your_token>\n"
        )

    print(f"Testing {len(apps)} app(s)...\n")

    results = []
    for app in apps:
        result = test_app(app)
        results.append(result)
        print_result(result, verbose=verbose)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    warned = sum(1 for r in results if r.warnings)
    total_time = sum(r.duration_ms for r in results)

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {warned} with warnings")
    print(f"Time: {total_time / 1000:.1f}s total")

    if failed > 0:
        print(f"\nFailed apps:")
        for r in results:
            if not r.passed:
                print(f"  - {r.app_name}: {r.error}")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
