#!/usr/bin/env python3
"""Resolve Android package IDs from app source trees or release APKs."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import struct
import sys
import zlib
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from constants import USER_AGENT
from help_formatter import StyledHelpFormatter
from utils import load_dotenv

REQUEST_TIMEOUT = 30
TREE_FETCH_TIMEOUT = 60
MAX_SOURCE_FILES_TO_FETCH = 12
MAX_APK_FULL_DOWNLOAD = 40 * 1024 * 1024
ZIP_TAIL_SIZE = 128 * 1024
ZIP_EOCD_SIG = b"PK\x05\x06"
ZIP_CD_SIG = b"PK\x01\x02"
ZIP_LOCAL_SIG = b"PK\x03\x04"
AXML_RES_XML = 0x0003
AXML_STRING_POOL = 0x0001
AXML_START_ELEMENT = 0x0102
AXML_TYPE_STRING = 0x03
PACKAGE_NAME_RE = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$"
)

APPLICATION_ID_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "applicationId",
        re.compile(
            r"""applicationId\s*(?:=\s*["']([^"']+)["']|\s+["']([^"']+)["'])"""
        ),
    ),
    (
        "namespace",
        re.compile(r"""namespace\s*=\s*["']([^"']+)["']"""),
    ),
    (
        "manifest-package",
        re.compile(r"""package\s*=\s*["']([a-zA-Z][a-zA-Z0-9_.]+)["']"""),
    ),
]

@dataclass(frozen=True)
class PackageIdHit:
    package_id: str
    source: str
    detail: str


@dataclass(frozen=True)
class PackageIdResult:
    package_id: str | None
    hits: tuple[PackageIdHit, ...]
    errors: tuple[str, ...]

    @property
    def ambiguous(self) -> bool:
        ids = {hit.package_id for hit in self.hits}
        return self.package_id is None and len(ids) > 1


def _http_request(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = REQUEST_TIMEOUT,
    method: str | None = None,
) -> tuple[bytes, dict[str, str]]:
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs, method=method)
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=timeout, context=ctx) as resp:
        body = resp.read()
        resp_headers = {k.lower(): v for k, v in resp.headers.items()}
        return body, resp_headers


def _http_json(url: str, headers: dict[str, str] | None = None) -> Any:
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    body, _ = _http_request(url, headers=hdrs)
    return json.loads(body.decode("utf-8", errors="replace"))


def _http_text(url: str, headers: dict[str, str] | None = None) -> str:
    body, _ = _http_request(url, headers=headers)
    return body.decode("utf-8", errors="replace")


def _http_range(url: str, start: int, end: int) -> bytes:
    body, _ = _http_request(
        url,
        headers={"Range": f"bytes={start}-{end}"},
        timeout=TREE_FETCH_TIMEOUT,
    )
    return body


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _parse_owner_repo(url: str) -> tuple[str, str, str]:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from: {url}")
    return parts[0], parts[1], parsed.netloc.lower()


def _is_valid_package_id(value: str) -> bool:
    if not value or value.startswith("android."):
        return False
    if "${" in value or value.startswith("@"):
        return False
    return bool(PACKAGE_NAME_RE.fullmatch(value))


def extract_package_ids_from_text(text: str) -> list[tuple[str, str]]:
    """Return (kind, package_id) pairs found in Gradle/manifest text."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for kind, pattern in APPLICATION_ID_PATTERNS:
        for match in pattern.finditer(text):
            candidate = next((g for g in match.groups() if g), "")
            if not _is_valid_package_id(candidate):
                continue
            key = f"{kind}:{candidate}"
            if key in seen:
                continue
            seen.add(key)
            found.append((kind, candidate))
    return found


def _path_is_source_candidate(path: str) -> bool:
    lower = path.lower().replace("\\", "/")
    if not (
        lower.endswith("build.gradle")
        or lower.endswith("build.gradle.kts")
        or lower.endswith("androidmanifest.xml")
    ):
        return False
    parts = lower.split("/")
    parents = parts[:-1]
    if any(
        p in {"example", "examples", "sample", "samples", "test", "tests", "androidtest"}
        for p in parents
    ):
        return False
    if "/build/" in f"/{lower}/" or "/.gradle/" in f"/{lower}/":
        return False
    if "generated" in parents or "intermediates" in parents:
        return False
    return True


def _rank_source_path(path: str) -> tuple[int, int, str]:
    lower = path.lower().replace("\\", "/")
    score = 0
    if lower.endswith("build.gradle.kts") or lower.endswith("build.gradle"):
        score += 100
    if lower.endswith("androidmanifest.xml"):
        score += 40
    if "/app/" in f"/{lower}" or lower.startswith("app/"):
        score += 30
    if "benchmark" in lower or "baselineprofile" in lower:
        score -= 80
    if "android" in lower:
        score += 10
    depth = lower.count("/")
    return (-score, depth, lower)


def _select_package_from_kinds(hits: list[tuple[str, str, str]]) -> str | None:
    """hits are (package_id, kind, detail). Prefer applicationId over weaker kinds."""
    by_id: dict[str, list[tuple[str, str]]] = {}
    for package_id, kind, detail in hits:
        by_id.setdefault(package_id, []).append((kind, detail))

    if not by_id:
        return None
    if len(by_id) == 1:
        return next(iter(by_id))

    app_ids = {
        pid
        for pid, kinds in by_id.items()
        if any(k == "applicationId" for k, _ in kinds)
    }
    if len(app_ids) == 1:
        return next(iter(app_ids))
    return None


def try_from_source_tree(url: str, source: str | None) -> PackageIdResult:
    errors: list[str] = []
    try:
        owner, repo, host = _parse_owner_repo(url)
    except ValueError as exc:
        return PackageIdResult(None, (), (str(exc),))

    try:
        if host == "github.com" or source == "GitHub":
            paths, _branch, raw_base = _github_source_paths(owner, repo)
        else:
            paths, _branch, raw_base = _gitea_source_paths(host, owner, repo)
    except (HTTPError, URLError, ValueError, KeyError, TimeoutError, OSError) as exc:
        return PackageIdResult(None, (), (f"source tree lookup failed: {exc}",))

    candidates = sorted(
        (p for p in paths if _path_is_source_candidate(p)),
        key=_rank_source_path,
    )[:MAX_SOURCE_FILES_TO_FETCH]

    if not candidates:
        return PackageIdResult(None, (), ("no Gradle/manifest files found in repo tree",))

    typed_hits: list[tuple[str, str, str]] = []
    result_hits: list[PackageIdHit] = []

    for path in candidates:
        raw_url = f"{raw_base}/{path}"
        try:
            text = _http_text(raw_url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append(f"fetch {path}: {exc}")
            continue
        for kind, package_id in extract_package_ids_from_text(text):
            typed_hits.append((package_id, kind, path))
            result_hits.append(
                PackageIdHit(package_id, "source", f"{kind} in {path}")
            )

    chosen = _select_package_from_kinds(typed_hits)
    if chosen is None and result_hits:
        unique = {h.package_id for h in result_hits}
        if len(unique) > 1:
            errors.append(
                "ambiguous package IDs in source: " + ", ".join(sorted(unique))
            )
            return PackageIdResult(None, tuple(result_hits), tuple(errors))
    return PackageIdResult(chosen, tuple(result_hits), tuple(errors))


def _github_source_paths(owner: str, repo: str) -> tuple[list[str], str, str]:
    headers = _github_headers()
    meta = _http_json(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
    )
    branch = meta.get("default_branch") or "main"
    tree = _http_json(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
        headers=headers,
    )
    if tree.get("truncated"):
        raise ValueError("GitHub tree response truncated")
    paths = [
        item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"
    ]
    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    return paths, branch, raw_base


def _gitea_source_paths(host: str, owner: str, repo: str) -> tuple[list[str], str, str]:
    meta = _http_json(f"https://{host}/api/v1/repos/{owner}/{repo}")
    branch = meta.get("default_branch") or "main"
    branch_info = _http_json(
        f"https://{host}/api/v1/repos/{owner}/{repo}/branches/{branch}"
    )
    sha = branch_info.get("commit", {}).get("id")
    if not sha:
        raise ValueError(f"no commit sha for branch {branch}")
    tree = _http_json(
        f"https://{host}/api/v1/repos/{owner}/{repo}/git/trees/{sha}?recursive=true"
    )
    paths = [item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"]
    raw_base = f"https://{host}/{owner}/{repo}/raw/branch/{branch}"
    return paths, branch, raw_base


def parse_axml_package_id(data: bytes) -> str:
    if len(data) < 8:
        raise ValueError("AXML too short")
    chunk_type, header_size, file_size = struct.unpack_from("<HHI", data, 0)
    if chunk_type != AXML_RES_XML:
        raise ValueError(f"not an AXML document (type={chunk_type:#x})")
    if file_size > len(data):
        raise ValueError("AXML size exceeds buffer")

    pos = header_size
    strings: list[str] = []
    while pos + 8 <= len(data):
        ctype, chdr, csize = struct.unpack_from("<HHI", data, pos)
        if csize < 8 or pos + csize > len(data):
            raise ValueError("invalid AXML chunk")
        if ctype == AXML_STRING_POOL:
            strings = _parse_string_pool(data, pos, chdr, csize)
        elif ctype == AXML_START_ELEMENT:
            package_id = _package_from_start_element(data, pos, strings)
            if package_id:
                return package_id
        pos += csize
    raise ValueError("package attribute not found in AndroidManifest.xml")


def _parse_string_pool(data: bytes, pos: int, header_size: int, chunk_size: int) -> list[str]:
    if header_size < 28:
        raise ValueError("string pool header too small")
    string_count, _style_count, flags, strings_start, _styles_start = struct.unpack_from(
        "<IIIII", data, pos + 8
    )
    utf8 = bool(flags & (1 << 8))
    offsets_pos = pos + header_size
    if offsets_pos + string_count * 4 > pos + chunk_size:
        raise ValueError("string pool offsets overrun")
    offsets = [
        struct.unpack_from("<I", data, offsets_pos + i * 4)[0] for i in range(string_count)
    ]
    str_base = pos + strings_start
    strings: list[str] = []
    for offset in offsets:
        p = str_base + offset
        if p >= pos + chunk_size:
            strings.append("")
            continue
        if utf8:
            _char_len, p = _read_utf8_len(data, p)
            byte_len, p = _read_utf8_len(data, p)
            end = min(p + byte_len, pos + chunk_size)
            strings.append(data[p:end].decode("utf-8", errors="replace"))
        else:
            char_len, p = _read_utf16_len(data, p)
            end = min(p + char_len * 2, pos + chunk_size)
            strings.append(data[p:end].decode("utf-16-le", errors="replace"))
    return strings


def _read_utf8_len(data: bytes, pos: int) -> tuple[int, int]:
    b0 = data[pos]
    if b0 & 0x80:
        return ((b0 & 0x7F) << 8) | data[pos + 1], pos + 2
    return b0, pos + 1


def _read_utf16_len(data: bytes, pos: int) -> tuple[int, int]:
    c0 = struct.unpack_from("<H", data, pos)[0]
    if c0 & 0x8000:
        c1 = struct.unpack_from("<H", data, pos + 2)[0]
        return ((c0 & 0x7FFF) << 16) | c1, pos + 4
    return c0, pos + 2


def _package_from_start_element(data: bytes, pos: int, strings: list[str]) -> str | None:
    if pos + 36 > len(data):
        return None
    attr_start, attr_size, attr_count = struct.unpack_from("<HHH", data, pos + 24)
    if attr_size < 20:
        return None
    for i in range(attr_count):
        ap = pos + 16 + attr_start + i * attr_size
        if ap + 20 > len(data):
            break
        _ns, name_idx, _raw = struct.unpack_from("<III", data, ap)
        _size, _res0, dtype = struct.unpack_from("<HBB", data, ap + 12)
        value = struct.unpack_from("<I", data, ap + 16)[0]
        if name_idx >= len(strings) or strings[name_idx] != "package":
            continue
        if dtype != AXML_TYPE_STRING or value >= len(strings):
            continue
        candidate = strings[value]
        if _is_valid_package_id(candidate):
            return candidate
    return None


def extract_android_manifest_from_apk(apk_data: bytes) -> bytes:
    return _extract_zip_entry(apk_data, "AndroidManifest.xml")


def extract_android_manifest_from_apk_url(url: str) -> bytes:
    size = _apk_content_length(url)
    if size is None:
        body, _ = _http_request(url, timeout=TREE_FETCH_TIMEOUT)
        if len(body) > MAX_APK_FULL_DOWNLOAD:
            raise ValueError(
                f"APK too large for full download ({len(body)} bytes); need Range support"
            )
        return extract_android_manifest_from_apk(body)

    tail_start = max(0, size - ZIP_TAIL_SIZE)
    tail = _http_range(url, tail_start, size - 1)
    eocd = tail.rfind(ZIP_EOCD_SIG)
    if eocd < 0:
        raise ValueError("ZIP end-of-central-directory not found")
    cd_size, cd_offset = struct.unpack_from("<II", tail, eocd + 12)
    if cd_offset + cd_size > size:
        raise ValueError("invalid ZIP central directory bounds")
    cd = _http_range(url, cd_offset, cd_offset + cd_size - 1)
    local_off, comp_size, method = _find_zip_entry(cd, "AndroidManifest.xml")
    local = _http_range(url, local_off, local_off + 30 + 512 + comp_size - 1)
    return _inflate_local_entry(local, comp_size, method)


def _apk_content_length(url: str) -> int | None:
    try:
        _body, headers = _http_request(url, method="HEAD", timeout=REQUEST_TIMEOUT)
    except (HTTPError, URLError, TimeoutError, OSError):
        return None
    length = headers.get("content-length")
    accept = headers.get("accept-ranges", "")
    if not length:
        return None
    if accept.lower() != "bytes" and "bytes" not in accept.lower():
        return None
    return int(length)


def _find_zip_entry(cd: bytes, name: str) -> tuple[int, int, int]:
    pos = 0
    target = name.encode("utf-8")
    while pos + 46 <= len(cd):
        if cd[pos : pos + 4] != ZIP_CD_SIG:
            break
        method = struct.unpack_from("<H", cd, pos + 10)[0]
        comp_size = struct.unpack_from("<I", cd, pos + 20)[0]
        name_len, extra_len, comment_len = struct.unpack_from("<HHH", cd, pos + 28)
        local_off = struct.unpack_from("<I", cd, pos + 42)[0]
        entry_name = cd[pos + 46 : pos + 46 + name_len]
        if entry_name == target:
            return local_off, comp_size, method
        pos += 46 + name_len + extra_len + comment_len
    raise ValueError(f"{name} not found in APK")


def _extract_zip_entry(apk_data: bytes, name: str) -> bytes:
    eocd = apk_data.rfind(ZIP_EOCD_SIG)
    if eocd < 0:
        raise ValueError("ZIP end-of-central-directory not found")
    cd_size, cd_offset = struct.unpack_from("<II", apk_data, eocd + 12)
    cd = apk_data[cd_offset : cd_offset + cd_size]
    local_off, comp_size, method = _find_zip_entry(cd, name)
    return _inflate_local_entry(apk_data[local_off:], comp_size, method)


def _inflate_local_entry(local: bytes, comp_size: int, method: int) -> bytes:
    if local[:4] != ZIP_LOCAL_SIG:
        raise ValueError("invalid ZIP local header")
    name_len, extra_len = struct.unpack_from("<HH", local, 26)
    data_start = 30 + name_len + extra_len
    comp = local[data_start : data_start + comp_size]
    if len(comp) < comp_size:
        raise ValueError("truncated compressed entry data")
    if method == 0:
        return comp
    if method == 8:
        return zlib.decompress(comp, -15)
    raise ValueError(f"unsupported ZIP compression method {method}")


def _pick_apk_asset(assets: list[dict[str, Any]]) -> tuple[str, str] | None:
    apks: list[tuple[str, str]] = []
    for asset in assets:
        name = asset.get("name") or ""
        dl = asset.get("browser_download_url") or ""
        if not dl:
            continue
        lower = name.lower()
        if lower.endswith(".apk") and not lower.endswith(".xapk"):
            apks.append((name, dl))
    if not apks:
        return None
    if len(apks) == 1:
        return apks[0]

    def rank(item: tuple[str, str]) -> tuple[int, int, str]:
        name = item[0].lower()
        score = 0
        if "android" in name:
            score += 50
        if "arm64" in name or "aarch64" in name:
            score += 20
        if "universal" in name:
            score += 15
        if any(x in name for x in ("x86", "windows", "linux", "macos", "debug")):
            score -= 40
        return (-score, len(name), name)

    return sorted(apks, key=rank)[0]


def try_from_apk(url: str, source: str | None) -> PackageIdResult:
    errors: list[str] = []
    try:
        owner, repo, host = _parse_owner_repo(url)
    except ValueError as exc:
        return PackageIdResult(None, (), (str(exc),))

    try:
        if host == "github.com" or source == "GitHub":
            apk = _latest_github_apk(owner, repo)
        else:
            apk = _latest_gitea_apk(host, owner, repo)
    except (HTTPError, URLError, ValueError, KeyError, TimeoutError, OSError) as exc:
        return PackageIdResult(None, (), (f"APK resolve failed: {exc}",))

    if apk is None:
        return PackageIdResult(None, (), ("no APK asset on latest suitable release",))

    name, apk_url = apk
    try:
        manifest = extract_android_manifest_from_apk_url(apk_url)
        package_id = parse_axml_package_id(manifest)
    except (HTTPError, URLError, ValueError, TimeoutError, OSError) as exc:
        return PackageIdResult(None, (), (f"APK manifest parse failed ({name}): {exc}",))

    hit = PackageIdHit(package_id, "apk", name)
    return PackageIdResult(package_id, (hit,), tuple(errors))


def _latest_github_apk(owner: str, repo: str) -> tuple[str, str] | None:
    headers = _github_headers()
    releases = _http_json(
        f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=20",
        headers=headers,
    )
    if not isinstance(releases, list):
        raise ValueError("unexpected GitHub releases payload")
    for release in releases:
        if release.get("draft"):
            continue
        picked = _pick_apk_asset(release.get("assets") or [])
        if picked:
            return picked
    return None


def _latest_gitea_apk(host: str, owner: str, repo: str) -> tuple[str, str] | None:
    releases = _http_json(
        f"https://{host}/api/v1/repos/{owner}/{repo}/releases?limit=20"
    )
    if not isinstance(releases, list):
        raise ValueError("unexpected Gitea releases payload")
    for release in releases:
        if release.get("draft"):
            continue
        assets = release.get("assets") or []
        normalized = []
        for asset in assets:
            name = asset.get("name") or ""
            dl = (
                asset.get("browser_download_url")
                or asset.get("browser_download")
                or ""
            )
            normalized.append({"name": name, "browser_download_url": dl})
        picked = _pick_apk_asset(normalized)
        if picked:
            return picked
    return None


def resolve_package_id(url: str, source: str | None = None) -> PackageIdResult:
    """Cascade: source tree first, then release APK. Best-effort, never raises."""
    all_hits: list[PackageIdHit] = []
    all_errors: list[str] = []

    source_result = try_from_source_tree(url, source)
    all_hits.extend(source_result.hits)
    all_errors.extend(source_result.errors)
    if source_result.package_id:
        return PackageIdResult(
            source_result.package_id,
            tuple(all_hits),
            tuple(all_errors),
        )

    apk_result = try_from_apk(url, source)
    all_hits.extend(apk_result.hits)
    all_errors.extend(apk_result.errors)
    if apk_result.package_id:
        return PackageIdResult(
            apk_result.package_id,
            tuple(all_hits),
            tuple(all_errors),
        )

    return PackageIdResult(None, tuple(all_hits), tuple(all_errors))


def format_detection_message(result: PackageIdResult) -> str:
    if result.package_id:
        match = next(
            (h for h in result.hits if h.package_id == result.package_id),
            None,
        )
        if match:
            return f"Detected package ID: {result.package_id}  (from {match.source}: {match.detail})"
        return f"Detected package ID: {result.package_id}"
    if result.ambiguous:
        ids = ", ".join(sorted({h.package_id for h in result.hits}))
        return f"Could not auto-detect package ID (ambiguous: {ids})"
    if result.errors:
        return f"Could not auto-detect package ID ({result.errors[0]})"
    return "Could not auto-detect package ID"


def _self_test() -> int:
    failures = 0

    gradle = '''
        android {
            namespace = "io.github.gopher64.gopher64"
            defaultConfig {
                applicationId = "io.github.gopher64.gopher64"
            }
        }
    '''
    extracted = extract_package_ids_from_text(gradle)
    kinds = {k for k, _ in extracted}
    ids = {i for _, i in extracted}
    if "applicationId" not in kinds or "io.github.gopher64.gopher64" not in ids:
        print("FAIL: gradle extraction", extracted)
        failures += 1
    else:
        print("PASS: gradle extraction")

    groovy = 'applicationId "org.dolphinemu.dolphinemu"'
    extracted = extract_package_ids_from_text(groovy)
    if extracted != [("applicationId", "org.dolphinemu.dolphinemu")]:
        print("FAIL: groovy extraction", extracted)
        failures += 1
    else:
        print("PASS: groovy extraction")

    manifest = '<manifest package="com.example.app" />'
    extracted = extract_package_ids_from_text(manifest)
    if ("manifest-package", "com.example.app") not in extracted:
        print("FAIL: manifest extraction", extracted)
        failures += 1
    else:
        print("PASS: manifest extraction")

    minimal_axml = bytes.fromhex(
        "030008001001000001001c00d00000000400000000000000000000002c000000"
        "000000000000000014000000280000004c00000008006d0061006e0069006600"
        "650073007400000007007000610063006b00610067006500000000000f006300"
        "6f006d002e006500780061006d0070006c0065002e0061007000700000000000"
        "2a0068007400740070003a002f002f0073006300680065006d00610073002e00"
        "61006e00640072006f00690064002e0063006f006d002f00610070006b002f00"
        "7200650073002f0061006e00640072006f006900640000000201100038000000"
        "01000000ffffffffffffffff00000000140014000100000000000000ffffffff"
        "01000000020000000800000302000000"
    )
    try:
        pkg = parse_axml_package_id(minimal_axml)
        if pkg != "com.example.app":
            print("FAIL: axml parse", pkg)
            failures += 1
        else:
            print("PASS: axml parse")
    except ValueError as exc:
        print("FAIL: axml parse", exc)
        failures += 1

    return 1 if failures else 0


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Resolve an Android package ID from a repo/release URL.",
        formatter_class=StyledHelpFormatter,
    )
    parser.add_argument("url", nargs="?", help="App repository URL")
    parser.add_argument(
        "--source",
        default=None,
        help="Obtainium source type hint (GitHub, Codeberg, ...)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run offline extraction self-tests",
    )
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    if not args.url:
        parser.error("url is required unless --self-test")

    from utils import detect_source_from_url

    source = args.source or detect_source_from_url(args.url)
    result = resolve_package_id(args.url, source)
    print(format_detection_message(result))
    if result.hits:
        print("Hits:")
        for hit in result.hits:
            print(f"  - {hit.package_id} ({hit.source}: {hit.detail})")
    if result.errors:
        print("Notes:")
        for err in result.errors:
            print(f"  - {err}")
    return 0 if result.package_id else 1


if __name__ == "__main__":
    sys.exit(main())
