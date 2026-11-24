# ClauseGuard — Student Quick Start

This is a school hackathon demo. You do **not** need to write any code — just
follow the steps below.

## What this is

A browser extension that reads Terms & Conditions / Privacy Policy text and
tells you which parts might deserve a closer look — using a small AI model
that runs entirely on your own computer, no internet needed once it's set up.

## Step 1 — One-click start (every time)

1. Unzip the project folder anywhere, e.g. your Desktop (first time only).
2. If you don't have Python yet, install **Python 3.11** from
   [python.org/downloads](https://www.python.org/downloads/release/python-3119/).
   During install, check the box **"Add python.exe to PATH."** (first time only)
3. Double-click **`start_windows.bat`** inside the unzipped folder.
   - The very first time, this installs everything it needs (a few minutes, needs internet).
   - Two small windows open in the background — leave them running.
   - **Chrome opens automatically with the ClauseGuard extension already
     loaded.** You do not need to visit `chrome://extensions` or click
     "Load unpacked" — that's all done for you.
   - Look for the 🛡️ ClauseGuard icon in that Chrome window's toolbar.

That's it — no manual extension installation step.

## Step 2 — Try the fictional demo scenarios

1. On the Scenario Lab page, click **Try Scenario** on any card (e.g. StreamBox Student).
2. Read the Terms & Conditions box on the page.
3. **Tick the checkbox**: "I have reviewed the Terms and Conditions above."

   > 🛡️ **This is the moment the extension kicks in.** As soon as you tick
   > the box, ClauseGuard automatically scans every clause on the page —
   > you don't need to click anything else. Within a second or two, a popup
   > appears telling you how many clauses may need attention (e.g. "⚠️ 7 of
   > 11 clauses may need your attention"), every clause gets highlighted by
   > category, and a results panel slides in on the right.

4. The big page button (e.g. "Start Free Trial") only exists to show how a
   real signup page would feel — it stays disabled until you tick the
   checkbox, and clicking it afterwards only changes its own text to
   "Registration simulated (demo only)." **It never sends anything anywhere.**
5. You can re-run the scan any time via the floating purple **"Scan Terms
   Before Accepting"** button in the bottom-right corner.

## Step 3 — Try it on a REAL website (GitHub, Facebook, ...)

This is different from Step 2 — on real websites, scanning is **click-to-scan
only**, never automatic:

1. Visit any real website (e.g. `github.com`).
2. Click the 🛡️ ClauseGuard icon in Chrome's toolbar.
3. Click **🔍 Scan Terms & Privacy Policy**.
4. If that site has been added to the demo cache (GitHub and Facebook are
   included), a new tab opens: your **Privacy & Terms Dashboard**, showing:
   - A simple **grade (A-D)** with a plain-language explanation of what it
     means (there's a legend on the dashboard itself).
   - A category breakdown in plain language.
   - How many real seconds the analysis took, proving it ran live, not
     from a stored answer.
5. If that site **isn't** cached yet, you'll see an honest "not cached yet"
   message. Ask your teacher to add it (see below), or use **Analyze
   Selected Text** in the popup as a manual fallback.

## Adding a new real website (for teachers, or curious students)

No coding needed:

1. Open `http://127.0.0.1:5500/admin-add-site.html` (also linked from the
   Scenario Lab's navigation bar as **"Add a Website"**).
2. Fill in the site's domain, display name, and its Terms/Privacy URLs.
3. Click **Build Cache for This Site** and wait ~10-20 seconds.
4. Done — it now shows up as scannable from the extension.

## Something not working?

- **No popup when you tick the checkbox on a demo page?** Check the 🛡️ icon
  is visible in Chrome's toolbar — if the window isn't the one
  `start_windows.bat` opened, the extension isn't loaded in it.
- **Popup says "could not reach the local analysis service"?** The two
  background windows from `start_windows.bat` need to stay open.
- **"No cached demo data for `<domain>` yet"?** Expected for sites nobody's
  added — see "Adding a new real website" above.
- More detail in the **Troubleshooting** section of the main `README.md`.

## Remember

This was trained on only 200 made-up example sentences for a school project,
so it won't be perfect on real legal text — that's expected, and it's
explained more in the main `README.md`'s Limitations section. This is an
educational prototype, not legal advice.

## To stop everything

Close the two small "ClauseGuard - API" and "ClauseGuard - Demo" windows
that opened when you ran `start_windows.bat`, and close the ClauseGuard
Chrome window.
