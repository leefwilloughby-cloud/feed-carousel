# Feed carousel

A small page that shows the 5 newest items from an RSS or Atom feed as a carousel. GitHub rebuilds it once a day and hosts it on GitHub Pages, so you can embed it anywhere with an iframe.

## Setup (about 5 minutes)

1. **Create a repository** on GitHub, for example `feed-carousel`. It must be **public** for free GitHub Pages. (Private repositories need a paid GitHub plan for Pages.)
2. **Upload these files**, keeping the folder structure:
   - `build.py`
   - `template.html`
   - `site/index.html`
   - `.github/workflows/update-carousel.yml`

   Tip: the web uploader skips folders that start with a dot. If `.github` doesn't appear, use **Add file > Create new file**, type `.github/workflows/update-carousel.yml` as the name and paste the contents in.
3. **Set your feed.** Open `.github/workflows/update-carousel.yml` and check `FEED_URL`. It is already set to your Valona feed.
4. **Turn on Pages.** Go to **Settings > Pages**. Under **Source**, pick **GitHub Actions**.
5. **Allow the workflow to save changes.** Go to **Settings > Actions > General > Workflow permissions** and pick **Read and write permissions**.
6. **Run it once.** Go to the **Actions** tab, open **Update feed carousel** and click **Run workflow**. After about a minute, your page is live at:

   `https://<your-github-name>.github.io/feed-carousel/`

From then on it updates every day at 05:17 UTC.

## Embed it

```html
<iframe src="https://<your-github-name>.github.io/feed-carousel/" width="100%" height="320" style="border:0" loading="lazy" title="Latest news"></iframe>
```

The phone tile is square and scales to fit the iframe, so give the iframe the same width and height as the space it replaces. Any spare space is filled with the tile's background colour. The simple card design instead fills whatever height the iframe gives it. Somewhere between 260 and 360 pixels works well. Below 560 pixels wide it switches to a stacked layout (image on top, text below).

## Options

Edit these in the `env:` section of the workflow file:

| Setting | What it does | Default |
|---|---|---|
| `FEED_URL` | The feed to read | (required) |
| `ITEM_COUNT` | How many items to show | 5 |
| `AUTOPLAY_SECS` | Seconds per slide. Use 0 to turn off auto-play | 7 |
| `TEMPLATE` | `template-phone.html` (square phone tile) or `template.html` (simple card) | phone tile |
| `BRAND_HTML` | Header text on the phone tile. Basic HTML allowed | `<i>AH</i>a! Intelligence` |
| `BRAND_TAGLINE` | Small italic text, top right of the phone tile | Animal Health AI Intelligence |
| `PANEL_LABEL_HTML` | Text in the green label. Use `<br>` for a line break | What's trending in Animal Health |
| `CAROUSEL_TITLE` | Heading above the carousel. Leave out to use the feed's title. Set to "" to hide it | feed title |

To change colours or fonts, edit the `:root` block at the top of `template.html`.

## Good to know

- **If the feed is down**, the build fails and yesterday's page stays live. GitHub emails the repository owner about the failed run.
- **Images** come from the feed (media tags, enclosures, or the first image in the item text). Items without an image show text only.
- **Links** open in a new tab, so readers don't leave your dashboard.
- **The schedule stays active** because each run commits the refreshed page. GitHub pauses scheduled workflows in repositories with no activity for 60 days, and the daily commit prevents that.
- **Test locally** with `python build.py https://your-feed-url` and open `site/index.html` in a browser.
