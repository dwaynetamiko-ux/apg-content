# APG weekly TikTok video run — playbook

This is the full procedure for the weekly automated run. Follow it exactly. Owner: Miko (Avenues Property Group, UK).
Audience: UK-based Jamaican diaspora considering property in Jamaica. CTA: the APG Deal Analyser (free to start).

**Never invent a figure.** Every number in a script or caption must come from Supabase (or a live FX lookup) in this run.
If something fails and can't be fixed, stop, schedule nothing that is wrong, and message Miko with what happened.

---

## 0. Setup
1. Attach the repo with push access (`add_repo` owner `dwaynetamiko-ux`, repo `apg-content`, access `push`), clone it, pull `main`.
2. Tools needed: Supabase connector, Metricool connector, `gh` CLI (works through the git proxy for this repo). Load `SendUserMessage` / `SendUserFile` early.

## 1. Find the open posting slots
- Metricool brand: blogId/brandId **7118084** (TikTok `tamiko_avenuesproperty`), timezone **Europe/London**.
- `getScheduledPosts` from now to +21 days. Find the **last scheduled post date** (Miko also schedules his own posts — never clash with them).
- New slots: **every other day at 17:00 Europe/London**, starting 2 days after the last scheduled post, **3–4 posts**, all within 14 days of today.
- If the queue already reaches 10+ days ahead, make only enough to keep it ~10–14 days deep (can be zero — then just report).

## 2. Learn from performance
- `getAnalyticsDataByMetrics` for TikTok posts (fields TKPO02 date, TKPO05 description, TKPO07 views, TKPO08 likes, TKPO09 comments, TKPO10 shares, TKPO13 full-watch rate) over the last 60 days.
- Note which hooks/topics got the most views and shares. Lean into those angles; don't copy them word for word.
- Check `scripts/` (file names + titles) and the last 4 weeks of captions — **don't repeat a topic/parish angle used in the last 4 weeks**.

## 3. Pull fresh figures (Supabase project `uykjlqajkupimavnivel`)
Tables:
- `listings` — long-term sale + rental. Use `is_live = true`, `property_type in ('House','Apartment','Townhouse','Villa','Flat','Studio')`, `price_jmd > 0`, `coalesce(is_room_let,false) = false`. Sales: `listing_type='Sale'`. Rents: `listing_type='Rental' and price_period='monthly'` (price_jmd is per month).
- `sa_listings` — holiday/short lets. Use `is_live = true`, `nightly_rate > 0`; `nightly_rate_jmd` per night. Freshness is `last_seen` (not `scraped_at`).
- Use **medians** (`percentile_cont(0.5)`), usually filtered by `bedrooms` (2-bed is the default comparison) and grouped by `parish`.
- **Minimum sample: 15 listings** per figure; drop parishes below that and say "parishes with enough data".
- FX: look up today's GBP→JMD and GBP→USD mid-market rate (web search). Show £ first with US$ alongside (e.g. "£751 a month (about $991 US)").
- Useful derived figures: gross yield = 12 × median rent ÷ median price; holiday-let break-even occupancy = monthly rent ÷ (nightly × 30.4); estimated monthly gross = nightly × 30.4 × occupancy.

## 4. Write the scripts (house style)
One JSON file per post in `scripts/`, named `YYYY-MM-DD-<slug>.json` (the posting date). Copy the structure of `scripts/house-test-stjames.json`:

```json
{ "id": "...", "style": "house", "voice": "en-GB-SoniaNeural", "rate": "+6%",
  "music_style": "track:afro-summer-date", "music_start": 12,
  "scenes": [ {"type": "title", ...}, {"type": "stat", ...}, {"type": "broll", ...}, {"type": "app", ...}, {"type": "end", "captions": true, ...} ] }
```
Scene types (`render/house.py`):
- `title` — `kicker` (small line, e.g. "Holiday Let Insights"), `title` (the hook question/statement), `tags`, `vo`.
- `stat` — `big` (e.g. "£129"), `count` `[0, 129, "£{:.0f}"]` for the count-up, `desc` (one line), `tags`, `vo`.
- `broll` — `tags`, `vo` (word-by-word captions are automatic).
- `app` — `clip` + `start` from `clips/manifest.json`. **Only use a recording when the narration matches the figures it shows on screen** (`shows` field). Otherwise skip it.
- `end` — always last, `"captions": true`, vo exactly: **"Run your own numbers free with the APG Deal Analyser, in pounds, US dollars or Jamaican dollars. Link in my bio."**

Structure: 5–7 scenes, **35–45 s** total (~95–120 words of voiceover). Hook in the first line. 1–2 stat scenes. Plain, confident British English; no hype, no guarantees, always "gross/before costs" where true.

Footage: give each non-app scene `tags` from `library/manifest.json` (e.g. `["jamaica","aerial","montego bay","st james"]`, `["woman","laptop","diaspora","black"]`, `["cleaning","housekeeping","turnover"]`, `["money","pounds"]`). The renderer picks the best library clip, never repeats one within a video, and only falls back to Pixabay (`q`) if nothing scores ≥2. Prefer Jamaica aerials for title/stat scenes, people for problem/benefit lines, money/calculator for numbers, cleaning for cost lines.

Music — vary across the week; pick to fit the topic:
| `music_style` | `music_start` | feel |
|---|---|---|
| `track:afro-champagne` | 2 | big brass, upbeat hooks |
| `track:afro-both-sides` | 22 | laid-back zouk guitar |
| `track:afro-summer-date` | 12 | tropical, holiday lets |
| `track:afro-sunshine` | 0 | bright, CTA-heavy |
| `track:afro-grotesque` | 16 | afro-trap, punchier |
| `reggaeton` (`music_seed` 0) | – | Miko's favourite generated track ("Track D") |

Pronunciation is handled by `render/lexicon.json` (Trelawny → "Trilaani", Montego Bay → "Mon-tee-go Bay", St Ann → "Sent Ann", St → Saint, J$ → Jamaican dollars). Write names normally in scripts. If a new place name is likely to be mispronounced, flag it to Miko in the summary.

## 5. Render
- Commit the new scripts and push to `main` (commit message ending with the usual Co-Authored-By line). The GitHub Action renders them (Sonia voice via edge-tts, licensed music + library + recordings decrypted with the `MUSIC_KEY` secret, Pixabay fallback via `PIXABAY_API_KEY`).
- Poll `gh api repos/dwaynetamiko-ux/apg-content/actions/runs` until the run for your commit completes (first pickup can take a while). Pull, then read `render/last_render.log` for errors.
- Check each video: duration 30–50 s, audio present, and grab a few frames to confirm footage + captions look right.

## 6. Schedule in Metricool
For each video, `createScheduledPost` (blogId `7118084`):
- `media`: `https://raw.githubusercontent.com/dwaynetamiko-ux/apg-content/<commit-sha>/videos/<name>.mp4` (pin the SHA of the render commit).
- `providers`: `[{"network":"tiktok"}]`, `autoPublish: true`, `publicationDate` `{dateTime: "<date>T17:00:00", timezone: "Europe/London"}`.
- `tiktokData`: `privacyOption PUBLIC_TO_EVERYONE`, `commercialContentOwnBrand true`, `autoAddMusic false`, `isAigc true`, `title` (short, Title Case).
- Caption (house style): hook line + emoji 🇯🇲 · 2–4 key figures in £ with US$ in brackets · one "so what" line · a question for comments 👇 · "Run your own numbers in the APG Deal Analyser, in £, $ or J$. Free to start — link in my bio." · 6–8 hashtags from: #JamaicaProperty #JamaicanDiaspora #BuyingInJamaica #PropertyInvesting #DiasporaInvestor #BuyToLet #HolidayLet #ShortTermRental #RentalYield #RealEstateJamaica plus a place tag (#MontegoBay #Negril #OchoRios #KingstonJamaica …).

## 7. Report to Miko
- `SendUserFile` the rendered videos (status `proactive`).
- `SendUserMessage`: table of date/time, title, key figure, track; anything skipped or flagged (thin data, new pronunciations, fallbacks to Pixabay). Remind him he can pull any post in Metricool before it goes live.
- Delete nothing of Miko's. Don't touch posts you didn't create.
