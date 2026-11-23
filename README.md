# ark-reader
small bit of software to allow for smoother reading of ARK and any other publications to be posted on sites
# ARK reader

Turns each magazine PDF into a fast page-by-page reader hosted free on GitHub Pages,
ready to embed on arkrca.com.

- Two-page spreads on desktop, single pages on phones
- Swipe, tap the edges, arrow keys, or drag the slider to turn pages
- Pinch, double-tap, or press the zoom button to zoom in on sharp high-resolution pages
- Page overview grid, full screen, and an optional PDF download
- Links can open a specific page, e.g. `…/posthuman/#24`
- Pages load as you read, so readers never wait for the whole magazine

```
issues/
  posthuman/
    ark_posthuman.pdf     <- any file name ending in .pdf
    meta.json             <- optional
  repetition/
    ark_repetition.pdf
reader/                   <- the reader's design (viewer.html) and the issues index page
scripts/build.py          <- turns PDFs into pages (runs on GitHub, you don't run it)
.github/workflows/build.yml
```

## One-time setup (about 10 minutes)

1. **Create the repository.** On GitHub, click **+** then **New repository**. Name it `ark-reader`,
   set it to **Public**, and click **Create repository**.
2. **Upload this kit.** On the new repo page, click **uploading an existing file**. Drag in
   everything from this folder *including the hidden `.github` folder*. On a Mac, press
   Cmd+Shift+. in Finder to show it. Commit.
   - If the `.github` folder won't drag in, create it by hand: **Add file** then **Create new file**,
     type `.github/workflows/build.yml` as the name, and paste in the contents of that file.
3. **Turn on Pages.** Go to **Settings**, then **Pages**. Under **Build and deployment**, set
   **Source** to **GitHub Actions**.

## Publishing an issue

1. **Make the PDF web-sized.** GitHub only accepts files up to **25 MB through the website**
   (100 MB with GitHub Desktop or git). Export a single-page (not spreads) PDF at about 150 dpi.
   In InDesign, use *Smallest File Size* or *High Quality Print* with images downsampled to 150 ppi.
   The reader makes its own images, so the PDF only needs to be good enough to render from.
   200 ppi is a safe middle ground.
2. **Upload it.** In the repo, open `issues`, then `posthuman`. Click **Add file**, then **Upload files**,
   drag in the PDF, and click **Commit changes**.
   - For a new issue, make its folder first: **Add file**, then **Create new file**, and type
     `issues/<name>/meta.json` (typing `/` creates folders). Paste a `meta.json` like the one
     below and commit. Then upload the PDF into that folder.
3. **Wait about 2–4 minutes.** Open the **Actions** tab and watch **Build reader** turn green.
   Click the finished run. Its summary shows the reader link **and the exact embed code** for
   each issue.

Your reader will be at `https://ostara-code.github.io/ark-reader/posthuman/`. All issues are
listed at `https://ostara-code.github.io/ark-reader/`.

### Optional `meta.json`

```json
{
  "title": "ARK | Posthuman",
  "subtitle": "Issue 3 · 2026",
  "order": 3,
  "theme": "dark",
  "download": "compressed",
  "cover_alone": true
}
```

- `order`: higher numbers are listed first on the issues page
- `theme`: `"dark"` or `"light"` (you can also add `?theme=light` to the embed link)
- `download`: `"compressed"` (smaller copy), `"original"`, or `false` to hide the download button
- `cover_alone`: `false` if page 1 should sit beside page 2 in spread view

To fix a typo, upload a corrected PDF with the same name into the same folder. The reader rebuilds itself.

## Putting it on arkrca.com (Squarespace)

Edit the page, click **Add block**, choose **Code**, and paste the embed code. It's also
printed on each Actions run:

```html
<div style="position:relative;width:100%;height:85vh;min-height:520px;">
  <iframe src="https://ostara-code.github.io/ark-reader/posthuman/" title="ARK | Posthuman" loading="lazy"
    style="position:absolute;inset:0;width:100%;height:100%;border:0;"
    allow="fullscreen" allowfullscreen></iframe>
</div>
```

Make the section **full width** so spreads get room. Code Blocks containing iframes need a
Squarespace plan above Personal. On any plan, you can instead point the homepage **READ**
button at the reader link.

## Optional: your own address

To serve the reader at e.g. `read.arkrca.com`: in **Settings**, then **Pages**, enter the custom
domain. Then in Squarespace go to **Domains**, then **DNS settings**, and add a `CNAME` record
`read` → `ostara-code.github.io`.
