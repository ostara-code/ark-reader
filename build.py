#!/usr/bin/env python3
"""
Builds the ARK reader site.

  issues/<slug>/<anything>.pdf   (+ optional issues/<slug>/meta.json)
      ->  _site/<slug>/index.html      the reader
          _site/<slug>/manifest.json   page list for the reader
          _site/<slug>/p/0001.jpg      screen-size pages
          _site/<slug>/hd/0001.jpg     high-res pages (used when zooming)
          _site/<slug>/t/0001.jpg      thumbnails
          _site/<slug>/<slug>.pdf      download copy (compressed if Ghostscript is installed)
      ->  _site/index.html             a simple library of all issues

Needs poppler-utils (pdftoppm, pdfinfo). Ghostscript is optional.

Usage:  python3 scripts/build.py [--base-url https://user.github.io/repo/]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "issues"
OUT = ROOT / "_site"
TEMPLATES = ROOT / "reader"

# Long-edge sizes in pixels. Raise SCREEN for sharper pages, lower it for faster loading.
SIZES = {"p": 1500, "hd": 2800, "t": 360}
QUALITY = {"p": 82, "hd": 80, "t": 72}


def log(msg):
    print(msg, flush=True)


def page_sizes(pdf):
    """Return [(w, h), ...] in points for every page, honouring page rotation."""
    out = subprocess.run(
        ["pdfinfo", "-f", "1", "-l", "100000", str(pdf)],
        capture_output=True, text=True, check=True,
    ).stdout
    sizes = {int(n): (float(w), float(h))
             for n, w, h in re.findall(r"Page\s+(\d+)\s+size:\s+([\d.]+) x ([\d.]+)", out)}
    rots = {int(n): int(r) for n, r in re.findall(r"Page\s+(\d+)\s+rot:\s+(\d+)", out)}
    result = []
    for n in sorted(sizes):
        w, h = sizes[n]
        if rots.get(n, 0) % 180 == 90:
            w, h = h, w
        result.append((round(w, 1), round(h, 1)))
    if not result:
        raise RuntimeError(f"Could not read pages from {pdf}")
    return result


def render(pdf, n_pages, kind, dest):
    """Render all pages at one size into dest/0001.jpg ... using all CPU cores."""
    dest.mkdir(parents=True, exist_ok=True)
    tmp = dest / "_tmp"
    tmp.mkdir(exist_ok=True)
    workers = max(1, os.cpu_count() or 1)
    chunk = max(1, -(-n_pages // workers))
    ranges = [(a, min(a + chunk - 1, n_pages)) for a in range(1, n_pages + 1, chunk)]

    def job(rng):
        first, last = rng
        subprocess.run([
            "pdftoppm", "-jpeg",
            "-jpegopt", f"quality={QUALITY[kind]},progressive=y,optimize=y",
            "-scale-to", str(SIZES[kind]),
            "-f", str(first), "-l", str(last),
            str(pdf), str(tmp / f"r{first}"),
        ], check=True)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(job, ranges))

    # pdftoppm names files prefix-<n>.jpg with varying zero padding; normalise.
    count = 0
    for f in tmp.iterdir():
        m = re.search(r"-(\d+)\.jpg$", f.name)
        if m:
            f.rename(dest / f"{int(m.group(1)):04d}.jpg")
            count += 1
    shutil.rmtree(tmp)
    if count != n_pages:
        raise RuntimeError(f"{kind}: expected {n_pages} pages, rendered {count}")


def ink_ratio(pdf, page):
    """Share of non-white pixels on a page, from a small greyscale render."""
    raw = subprocess.run(
        ["pdftoppm", "-gray", "-scale-to", "160", "-f", str(page), "-l", str(page), str(pdf)],
        capture_output=True, check=True,
    ).stdout
    # Binary PGM: "P5\n<w> <h>\n<max>\n<pixels>"
    m = re.match(rb"P5\s+(\d+)\s+(\d+)\s+\d+\s", raw)
    w, h = int(m.group(1)), int(m.group(2))
    pixels = raw[m.end():m.end() + w * h]
    return sum(1 for v in pixels if v < 235) / (w * h)


def hidden_pages(pdf, n, meta):
    """Pages (1-based) not to show: blank pages at the very start and end, plus any listed in meta."""
    hide = set(int(x) for x in meta.get("hide_pages", []))
    if meta.get("trim_blank", True) and n > 4:
        blank = lambda pg: ink_ratio(pdf, pg) < 0.001
        pg = 2                                  # page 1 is the cover
        while pg < n // 2 and blank(pg):
            hide.add(pg); pg += 1
        pg = n if blank(n) else n - 1           # last page may be the back cover
        while pg > n // 2 and blank(pg):
            hide.add(pg); pg -= 1
    return sorted(p for p in hide if 1 <= p <= n)


def download_copy(pdf, target, mode):
    """mode: 'compressed' (default), 'original', or False for no download."""
    if mode is False or mode == "none":
        return None
    if mode == "compressed" and shutil.which("gs"):
        log("   compressing PDF for download…")
        subprocess.run([
            "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.6",
            "-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dBATCH", "-dQUIET",
            f"-sOutputFile={target}", str(pdf),
        ], check=True)
        if target.stat().st_size < pdf.stat().st_size:
            return target.name
    shutil.copyfile(pdf, target)
    return target.name


def build_issue(folder, base_url):
    slug = folder.name
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        log(f"-- {slug}: no PDF found, skipping")
        return None
    pdf = pdfs[0]
    meta_file = folder / "meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    title = meta.get("title") or "ARK | " + slug.replace("-", " ").replace("_", " ").title()

    log(f"== {slug}: {pdf.name} ({pdf.stat().st_size / 1e6:.1f} MB)")
    sizes = page_sizes(pdf)
    n = len(sizes)
    out = OUT / slug
    out.mkdir(parents=True, exist_ok=True)
    hide = hidden_pages(pdf, n, meta)
    if hide:
        log(f"   hiding blank/unwanted pages: {', '.join(map(str, hide))}")
    for kind in ("p", "t", "hd"):
        log(f"   rendering {n} pages → {kind}/")
        render(pdf, n, kind, out / kind)

    dl = download_copy(pdf, out / f"{slug}.pdf", meta.get("download", "compressed"))

    manifest = {
        "title": title,
        "slug": slug,
        "coverAlone": meta.get("cover_alone", True),
        "theme": meta.get("theme", "dark"),
        "download": dl,
        "pages": [dict(w=w, h=h, **({"hidden": True} if i + 1 in hide else {}))
                  for i, (w, h) in enumerate(sizes)],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")))
    html = (TEMPLATES / "viewer.html").read_text().replace("{{TITLE}}", title)
    (out / "index.html").write_text(html)

    url = f"{base_url.rstrip('/')}/{slug}/" if base_url else f"{slug}/"
    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    log(f"   done: {url}  ({total / 1e6:.1f} MB published)")
    return {"slug": slug, "title": title, "pages": n - len(hide), "url": url,
            "order": meta.get("order", 0), "subtitle": meta.get("subtitle", "")}


def embed_code(url, title):
    return (
        '<div style="position:relative;width:100%;height:85vh;min-height:520px;">\n'
        f'  <iframe src="{url}" title="{title}" loading="lazy"\n'
        '    style="position:absolute;inset:0;width:100%;height:100%;border:0;"\n'
        '    allow="fullscreen" allowfullscreen></iframe>\n'
        '</div>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("BASE_URL", ""))
    args = ap.parse_args()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    issues = []
    folders = sorted(p for p in SRC.iterdir() if p.is_dir()) if SRC.exists() else []
    for folder in folders:
        info = build_issue(folder, args.base_url)
        if info:
            issues.append(info)
    if not issues:
        log("No issues yet. Upload a PDF to issues/<name>/ to publish one.")

    issues.sort(key=lambda i: (-i["order"], i["slug"]))
    (OUT / "issues.json").write_text(json.dumps(issues))
    shutil.copyfile(TEMPLATES / "index.html", OUT / "index.html")

    # Embed codes: printed in the log and shown on the Actions run summary page.
    lines = ["# ARK reader built", ""]
    for i in issues:
        lines += [f"## {i['title']} ({i['pages']} pages)", "",
                  f"Reader: {i['url']}", "", "Squarespace embed code:", "",
                  "```html", embed_code(i["url"], i["title"]), "```", ""]
    summary = "\n".join(lines)
    log("\n" + summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(summary)


if __name__ == "__main__":
    main()
