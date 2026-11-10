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
- `title` — `kicker` (small line, e.g. "Jamaica Airbnb Insights"), `title` (the hook question/statement), `tags`, `vo`.
- `stat` — `big` (e.g. "£129"), `count` `[0, 129, "£{:.0f}"]` for the count-up, `desc` (one line), `tags`, `vo`.
- `broll` — `tags`, `vo` (word-by-word captions are automatic).
- `app` — `clip` + `start` from `clips/manifest.json`. **Only use a recording when the narration matches the figures it shows on screen** (`shows` field). Otherwise skip it.
- `end` — always last, `"captions": true`, vo exactly: **"Run your own numbers free with the APG Deal Analyser, in pounds, US dollars or Jamaican dollars. Link in my bio."**

Structure: 5–7 scenes, **35–45 s** total (~95–120 words of voiceover), aim nearer 35 s. 1–2 stat scenes. Plain, confident British English; no hype, no guarantees, always "gross/before costs" where true.

### Hook and first-frame rules (mandatory — from TikTok analytics)
Most viewers leave in the first 2–3 s, and TikTok only pushes beyond the UK if early retention and shares are strong. The hook decides reach, not posting time.
1. **Figure in the first 2 seconds.** The title scene's `title` and `vo` must contain the actual number (e.g. "£2,755 a month from a 2-bed Airbnb in Jamaica"). No teasers like "might surprise you" or "you won't believe" — the 28 Sept teaser hook averaged 4.8 s watch, 7% left by 0:15, 0 shares. The 30 Sept hard-number hook got 1.9K views and 9 shares.
2. **First frame must read as Jamaica, not generic Caribbean.** Title scene `tags` must pick a recognisably Jamaican shot (landmark, Montego Bay/Ocho Rios/Negril aerial, flag) — never plain turquoise sea. Title `kicker` or `title` must include "Jamaica" on screen. Generic sea footage got the 28 Sept video seeded to a French/Dutch Caribbean travel audience (UK only 41%).
3. **Rankings name the winner up front.** For parish comparisons, say the parish and its figure in the opening line ("St James tops Jamaica's Airbnb rates at £129 a night"), then explain.
4. **Say "Airbnb" or "short-term rental", never "holiday let"** (in vo, on-screen text and captions) — that's what people search ("starting airbnb jamaica").
5. **Prefer island-wide figures** over single-parish or single-property angles; they travel further.
6. Captions: include "Jamaica" and "Airbnb" in the first line of the caption text for search.

### Realtor track (1 video per run)
Each run, make **exactly one** of the 3–4 videos for **Jamaican realtors** (agents in Jamaica whose buyers are overseas/diaspora investors). The rest stay investor videos. If the run makes zero or one video, the investor video takes priority, and the realtor video goes in the next run.
- **Angle:** the tool saves the realtor time when an investor asks "what will it rent for / what's the yield / what's that in pounds?". The realtor gets the answer in seconds instead of pulling comps by hand.
- **What you can claim (confirmed by Miko):** instant live rent and Airbnb comps by parish and bedroom count; deal figures (yield, cashflow, ROI) in £, US$ and J$; a realtor plan/referral offer. **Don't state any price, commission or plan terms for the realtor offer** unless they're written in this playbook. For now, the most you can say is "there's a realtor plan, DM me".
- **Branded client report: NOT available yet.** It's a possible future feature, only if enough realtors want it, and it would be on a separate subscription. Never show it, say it exists, or imply it's included. You may use it as a **demand test** in at most one realtor video every other run: e.g. "Would a branded report you can send your buyers help? Comment 'report'." Keep it a question, with no price and no launch date. If you used it, mention that in the report to Miko.
- **Hook rules still apply.** Put a real figure from this run's queries in the first 2 seconds, framed as the realtor's problem, e.g. "392 two-bed rentals in Kingston, one answer: £1,051 a month. That's the comp your overseas buyer will ask for." Jamaican first frame, "Jamaica" on screen.
- **Kicker:** "For Jamaican Realtors". Use people footage for the problem line (`["woman","laptop","stressed"]`, `["man","tablet","professional"]`) and `app` clips only where `shows` matches the narration (e.g. `kingston-btl-2bed-comps-usd` with the Kingston 2-bed figures).
- **VO:** add one realtor line before the end scene, e.g. "Realtors, there's a plan for you. DM me." The end scene keeps the standard line unchanged.
- **Caption:** first line includes "Jamaica" plus "realtor" or "real estate agent". Add the realtor hashtags #JamaicaRealtor #RealtorTips #RealEstateAgent alongside #RealEstateJamaica #JamaicaProperty. Finish with "Realtors: DM me about the APG realtor plan."
- **Report:** mark the video's track as "Realtor" in the summary table.

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
