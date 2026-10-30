#!/usr/bin/env python3
"""Gate checks for the built Jekyll site. Exit code 1 = block the deploy."""
import argparse, os, re, sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

errors = []
def fail(msg): errors.append(msg); print(f"  FAIL  {msg}")
def ok(msg): print(f"  ok    {msg}")

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.title = ""; self._in_title = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title": self._in_title = True
        for key in ("href", "src"):
            if a.get(key): self.links.append(a[key])
    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
    def handle_data(self, data):
        if self._in_title: self.title += data

def target_exists(site, path):
    full = os.path.join(site, path.lstrip("/"))
    if path.endswith("/") or path == "": return os.path.isfile(os.path.join(full, "index.html"))
    return (os.path.isfile(full) or os.path.isfile(os.path.join(full, "index.html"))
            or os.path.isfile(full + ".html"))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default="."); p.add_argument("--site", default="_site")
    p.add_argument("--base-path", default=""); p.add_argument("--expect-version")
    a = p.parse_args()
    base = a.base_path.rstrip("/")

    print("1) README activity markers")
    readme = open(os.path.join(a.repo, "README.md"), encoding="utf-8").read()
    s, e = readme.find("<!--START_SECTION:activity-->"), readme.find("<!--END_SECTION:activity-->")
    if s == -1 or e == -1 or e < s: fail("README.md must contain START then END activity markers")
    else: ok("markers present and in order")

    print("2) Homepage")
    home = os.path.join(a.site, "index.html")
    if not os.path.isfile(home): fail("_site/index.html missing (did index.md build?)")
    elif "Recent activity" not in open(home, encoding="utf-8").read():
        fail("homepage does not include README's 'Recent activity' section")
    else: ok("index.html includes README content")

    print("3) HTML basics + 4) internal links")
    pages = [os.path.join(d, f) for d, _, fs in os.walk(a.site) for f in fs if f.endswith(".html")]
    for page in pages:
        rel = os.path.relpath(page, a.site)
        html = open(page, encoding="utf-8").read()
        if not re.match(r"\s*<!doctype html", html, re.I): fail(f"{rel}: missing <!doctype html>")
        parser = Page(); parser.feed(html)
        if not parser.title.strip(): fail(f"{rel}: missing or empty <title>")
        for link in parser.links:
            u = urlsplit(link)
            if u.scheme or link.startswith(("//", "#")): continue   # external / anchor
            path = unquote(u.path)
            if not path: continue
            if path.startswith("/"):
                if base and path.startswith(base): path = path[len(base):] or "/"
            else:
                path = "/" + os.path.normpath(os.path.join(os.path.dirname(rel), path)).replace("\\", "/")
                if link.endswith("/"): path += "/"
            if not target_exists(a.site, path): fail(f"{rel}: broken link -> {link}")
    ok(f"checked {len(pages)} HTML page(s)")

    if a.expect_version:
        print("5) Version stamp")
        vf = os.path.join(a.site, "version.txt")
        v = open(vf).read().strip() if os.path.isfile(vf) else None
        if v != a.expect_version: fail(f"version.txt is {v!r}, expected {a.expect_version!r}")
        else: ok(f"version.txt = {v}")

    print(f"\nRESULT: {'BLOCKED - ' + str(len(errors)) + ' problem(s)' if errors else 'PASSED'}")
    sys.exit(1 if errors else 0)

if __name__ == "__main__": main()
