# APG weekly TikTok video run — playbook

> **CONTENT MIX FROM 22 NOV 2026 (Miko): NO STAT VIDEOS until Miko says otherwise.** Each run makes only:
> - **App use-case videos** (about half): a real problem a diaspora buyer has, and how the APG Deal Analyser solves it. See "Use-case track" in section 4.
> - **Realtor videos** (about half): how Jamaican realtors use the Deal Analyser with overseas buyers. See "Realtor track" in section 4.
>
> With 4 slots, make 2 of each; with 3, make 2 use-case + 1 realtor. Where this note conflicts with anything below (stat scenes, "figure in the first 2 seconds", "Jamaica by the numbers", the realtor trial), **this note wins**.

> **FROM 25 NOV 2026 (Miko): MAKE THE WEEKLY VIDEOS IN PICTORY**, not with the GitHub renderer. All other rules in this playbook still apply unchanged: the content mix, hooks, a Jamaican first frame, no invented figures, the realtor offer line, the 8-week no-repeat footage rule, the slots, no clashes with Miko's posts, auto-publish and the report. Only production changes: Pictory stock footage (Getty/Storyblocks), the **Matilda** voice and the **20 Oct framework** (section 8). Steps 5 and 6 are replaced by **section 9**. Use the GitHub renderer only as a fallback if Pictory is unavailable, and flag it in the report.

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
7. **Lead with a monthly £ figure.** This is from Miko's TikTok Studio stats, 28 Sept–9 Nov. Hooks with a "£X a month" figure got 680–1,903 views (30 Sept £2,755/mo, 20 Oct £1,003 net/mo, 9 Nov £1,319/mo). A big £ gap also worked (30 Oct £236k, 682 views). Per-night rates, percentages and listing counts all got only 229–265 views. So put a monthly £ figure in the opening line, and move nightly rates, yields and counts into the stat scenes. A big £ price or gap is the second choice.
8. **Never open on `jamaica-coast-village-aerial`.** It's the shot of beach, fishing boats and shallow turquoise water. Both videos that opened on it got the lowest UK share (5 Nov 66.8%, 7 Nov 58.3%), and up to 23% of viewers came from the French and Dutch Caribbean. Open title scenes on `jamaica-town-mountains-aerial`, `jamaica-hillside-city-aerial` or `jamaica-resort-beach-aerial` (9 Nov, 81% UK) instead. The coast-village clip is fine in later scenes. In title scene tags, avoid "coast", "village" and "negril", which would select it.
9. **Aim at 35 s, under 100 words.** The 45 s+ videos didn't do better.

### Follow and engagement (from Studio stats)
45–67% of viewers had seen the account before, but 97–100% are non-followers. Shares are almost always 0.
- **Series label:** make the title `kicker` "Jamaica by the numbers #N". Count N on from the highest number already in `scripts/`; the first one is #1.
- **Follow line:** the last non-end scene's VO ends with "Follow for a new Jamaica number every other day." The end scene stays unchanged.
- **One specific comment prompt** in the caption, easy to answer, e.g. "Comment your parish and I'll reply with the typical 2-bed rent." No generic "what do you think?" questions.
- **Audience:** 76–90% of viewers are female, mostly aged 25–44, and the UK is 58–88%. Keep the female voice and the people shots (Black women in particular). Write for a UK woman in her 30s thinking about her first property in Jamaica.

### Use-case track (from 22 Nov 2026)
Show **what the Deal Analyser does for a diaspora buyer**, not market statistics.
- **Shape:** problem → what you do in the app → what you find out → end line. 5–6 scenes, ~35 s, under 100 words.
- **Hook:** a concrete, recognisable situation in the first line, with "Jamaica" in it. No teaser hooks, and no stat-led hook. Examples: "Family sent you a house in Jamaica on WhatsApp? Check it before you send a penny." / "Airbnb or long let in Jamaica? Run the same house both ways."
- **First frame:** still a recognisably Jamaican shot (rules 2 and 8 below), with the kicker **"APG Deal Analyser in use"**.
- **Figures:** none needed. If a line states a figure, it must come from this run's Supabase queries, or be exactly what an `app` clip on screen shows (`shows` field).
- **App clips:** use the recordings in `clips/manifest.json` for the "in the app" scenes. Narration over a clip must not contradict what it shows. Don't say a clip's figures are "today's" or "live".
- **Topic bank** (don't repeat a topic used in the last 4 weeks, including Miko's own Pictory posts — 14 Nov "Family sent you a house", 16 Nov "Buying with family"): Airbnb vs long let on the same house; gross vs net (what's left after costs); test your deal at low occupancy; check what tenants actually pay before you buy; see the numbers in US dollars for family in the States; a due diligence checklist before money moves; comparing two properties before you choose; what to check when a listing looks cheap.
- **App clips added 22 Nov** (see `clips/manifest.json` for exactly what each shows): currency switch £/US$/J$ on one deal, strategy switch long let -> Airbnb on the same house, Airbnb occupancy slider, Export PDF options, the finished PDF report, Saved Deals load, Save Deal -> free-account sign-in, Westmoreland/Negril and Manchester/Mandeville Airbnb comps (J$), and the due diligence checklist. Build use-case and realtor videos around these; vary which clips you use across the week.
- **Due diligence clip caveat:** the checklist covers business-level compliance (Real Estate Board/REDDA licensing, Jamaica Tourist Board registration for short lets, GCT, tax, AML, GDPR). Narrate it as "compliance checks before you run an Airbnb or property business in Jamaica", never as title/valuation checks.
- **Never narrate or caption the Pro price**, even though some clips show an "Unlock Pro" banner.
- **Follow line:** the last non-end scene's VO ends with "Follow for more ways to check a Jamaica deal."
- **Caption:** situation line with "Jamaica" + 🇯🇲 · one line on what the app shows · one specific comment prompt 👇 · the standard "Run your own numbers…" line · 6–8 hashtags.
- Free vs Pro: saving deals needs a (free) account — say "create a free account to save your deals". PDF export, due diligence, HMO and the US$/J$ currencies are Pro. Say "free to start", never imply the Pro features are free, and never mention the Pro price.

### Realtor track (from 22 Nov 2026: about half of each run)
Miko wants realtor videos in every run. Still report each realtor video's Jamaica viewer share (Metricool/Studio) in the summary, but don't stop the track on your own. Name tourist hotspots (Montego Bay, Negril, Ocho Rios), which drew the most Jamaica viewers (7–8%).
Videos for **Jamaican realtors** (agents in Jamaica whose buyers are overseas/diaspora investors).
- **Angle:** the tool saves the realtor time when an investor asks "what will it rent for / what's the yield / what's that in pounds?". The realtor gets the answer in seconds instead of pulling comps by hand.
- **What you can claim (confirmed by Miko):** instant live rent and Airbnb comps by parish and bedroom count; deal figures (yield, cashflow, ROI) in £, US$ and J$; a realtor plan/referral offer. **Don't state any price, commission or plan terms for the realtor offer** unless they're written in this playbook. The offer line is exactly: "DM me Realtor if interested in a Realtor plan." Use that wording and nothing more.
- **Branded client report: NOT available yet.** It's a possible future feature, only if enough realtors want it, and it would be on a separate subscription. Never show it, say it exists, or imply it's included. You may use it as a **demand test** in at most one realtor video every other run: e.g. "Would a branded report you can send your buyers help? Comment 'report'." Keep it a question, with no price and no launch date. If you used it, mention that in the report to Miko.
- **Hook:** the realtor's problem in the first line, e.g. "Realtors in Jamaica: your overseas buyer asks what it'll rent for. Answer in 30 seconds." No stat-led hooks while stat videos are off. Jamaican first frame, "Jamaica" on screen. Any figure stated must come from this run's queries or match the `app` clip on screen.
- **Never** state unsourced market claims (e.g. "7 in 10 enquiries are from overseas").
- **Kicker:** "For Jamaican Realtors". Use people footage for the problem line (`["woman","laptop","stressed"]`, `["man","tablet","professional"]`) and `app` clips only where `shows` matches the narration (e.g. `kingston-btl-2bed-comps-usd` with the Kingston 2-bed figures).
- **VO:** add one line before the end scene, exactly: "DM me Realtor if interested in a Realtor plan." The end scene keeps the standard line unchanged.
- **Caption:** first line includes "Jamaica" plus "realtor" or "real estate agent". Add the realtor hashtags #JamaicaRealtor #RealtorTips #RealEstateAgent alongside #RealEstateJamaica #JamaicaProperty. Finish with "DM me Realtor if interested in a Realtor plan 📩"
- **Report:** mark the video's track as "Realtor" in the summary table.

### Footage: no repeats within 8 weeks (Miko, 23 Nov 2026)
**No stock visual (library clip or Pixabay clip) may appear in two videos whose posting dates are less than 8 weeks (56 days) apart**, including within the same run. **App screen recordings (`app` scenes) are exempt** and can be reused freely.
- `render/house.py` enforces this using `render/footage_log.json`, which records every stock clip used per video (by posting date in the file name). It excludes clips used within 56 days either side, records each new render, and **refuses to render** a video if any scene has no fresh clip (`FOOTAGE EXHAUSTED` / `RENDER FAILED` in `render/last_render.log`). Don't edit the log by hand except to remove the entry for a video you deleted.
- Before writing scripts, check `render/footage_log.json` against `library/manifest.json` to see which library clips are still free for your posting dates, and write `tags` that target those. Where no free library clip fits, give the scene good Pixabay `q` terms; the renderer falls back to Pixabay and never reuses a Pixabay clip within 8 weeks either.
- **Title (opening) scenes** only take library clips tagged "jamaica" and never `jamaica-coast-village-aerial`, `caribbean-cay-aerial` or `caribbean-waterfront-homes-aerial`. When the Jamaica aerials are all used, the opener comes from Pixabay with "jamaica" required in its tags. Give title scenes specific Jamaican `q` terms (e.g. "kingston jamaica aerial", "montego bay jamaica", "blue mountains jamaica", "jamaica flag"). **Check the first frame of every Pixabay opener**: if it isn't recognisably Jamaica (generic turquoise sea, another country), don't schedule that video.
- Pixabay openers must match **every** word of a `q` search (so "kingston jamaica" needs both tags). Pixabay's Jamaica footage is thin: on 23 Nov only Jamaican flag clips passed. Searches for Kingston, the Blue Mountains, Jamaica beaches and Montego Bay turned up nothing usable (a cannabis clip, a cartoon, misty jungle, a Mexican beach). Drug, cartoon and other-country tags are now blocked. If an opener looks wrong, or is visually the same as another video's (the same animation on a different background counts), add its id to the scene's `"exclude_pixabay": [ids]`, remove that video's `footage_log.json` entry, and re-render.
- **If a video can't get fresh footage or a recognisably Jamaican opener, make fewer videos** (delete its script and any `footage_log.json` entry, push) and flag it to Miko. Don't reuse footage, and don't post a generic first frame.
- In the report, list which videos used Pixabay footage and say when the library is running low, so Miko can add more clips.

Footage: give each non-app scene `tags` from `library/manifest.json` (e.g. `["jamaica","aerial","montego bay","st james"]`, `["woman","laptop","diaspora","black"]`, `["cleaning","housekeeping","turnover"]`, `["money","pounds"]`). The renderer picks the best library clip not used within 8 weeks (see above), never repeats one within a video, and falls back to Pixabay (`q`) if nothing free scores ≥2. Prefer Jamaica aerials for title/stat scenes, people for problem/benefit lines, money/calculator for numbers, cleaning for cost lines.

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
- Check each video: duration 30–50 s, audio present, and grab a few frames to confirm footage + captions look right. Check `render/last_render.log` for `FOOTAGE EXHAUSTED` / `RENDER FAILED` (see the 8-week footage rule) and confirm `render/footage_log.json` gained an entry per new video.

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

## 8. Videos made in Pictory (Miko, 24 Nov 2026)
When a video is made in Pictory (Pictory MCP, Standard account, "Design it together"), always:
- **Voice:** "Matilda" (account voice, speaker 3017), speed 106.
- **Style (Miko, 25 Nov 2026):** any layout that fits Miko's TikTok posts **since 28 Sep 2026** may be used, and it's fine to vary it from week to week. That covers: the 20 Oct framework below (the reference build); the house style of the automated videos (clip on the top half, a white panel with a small grey label and a bold dark title, word-by-word captions, a white end card with the logo and a green "Link in my bio" button); and the full-screen footage with clean white captions and a big brand-green figure from the Sept/Oct Pictory posts. Whatever the layout, keep: the brand colours (#2D7045 green, #EBB66A gold, white or dark text, no off-brand shapes such as pink or red), a recognisably Jamaican first frame, captions without Pictory's default dark box, and the logo end card.
- **Music (Miko, 25 Nov 2026):** Reggae, Reggaeton or Afrobeat(s) only. Find tracks with `search_music` using `genre: ["Reggae"]`, `["Reggaeton"]` or `["Afrobeat"]` (with `minDuration` + `maxDuration`), pick one that suits the mood, and vary it across the week. Known good tracks: reggae "Solace", "Green Flag", "Strong Roots", "Kingston Dub", "Dub Mojito"; reggaeton "Playa", "Chico Malo", "Te Amos", "So Easy"; afrobeat "Eastern Block". Keep the volume at 0.1 under the narration.
- **Framework (one option):** copy Miko's 20 Oct 2026 TikTok ("Gross income sells the dream"):
  1. Full-bleed footage scenes with a small uppercase white label top-left (DM Sans 20, e.g. "REALITY CHECK", "THE CATCH") and plain white captions with **no box**. The opening scene must still read as Jamaica.
  2. Figures scene: app recording on the top ~45% on a #090A0E black panel, a thin #3E8E41 green rule, a bold white heading (DM Sans 44, e.g. "£756 a month"), a grey #8A8C90 subline and green (#4CAF50) captions.
  3. Quote card: a large green quotation mark and a bold #2D7045 line over footage softened with a 55% white overlay, with dark green captions.
  4. End card: white background, large APG logo, "Free to start. Link in my bio." in small dark text, no captions.
- Pictory adds a 35% black box behind all text and captions by default. After the preview is built, set every text and subtitle `backgroundColor` to `rgba(0,0,0,0)` with `update_preview_elements`, and set caption colours per scene as above.
- Reference build: preview job `9e3e9843-ce4b-4963-b290-be1f0c5a4f4e` (27 Nov "Check the Rent").

## 9. Weekly run in Pictory (from 25 Nov 2026, replaces steps 5–6)
Miko agreed (24 Nov 2026) that scheduled runs may **render without his preview approval**. The run builds the preview, checks it, renders, then schedules it. He can pull any post in Metricool before it goes live.
1. `check_motion_graphics_eligibility` (no projectId). The account is Standard, so use `preview_video_from_text` with `designMode: "together"`, `aspectRatio: "9:16"`, voice Matilda (`speaker "3017"`, speed 106), music on at volume 0.1 (Reggae, Reggaeton or Afrobeat only; see section 8), subtitles on, and `saveProject` false. Check `get_quota` (premium voice minutes) first.
2. **Scenes:** use any style allowed in section 8. For the 20 Oct framework: (1) Jamaican opener: full-bleed stock with a small uppercase label. (2) Problem scene: full-bleed people footage with a label. (3) Split scene: the app recording from `clips/pictory_urls.json` on the top 45% (`left 22%`, `width 56%`, the clip's aspect ratio, `type video`), then a #090A0E panel with a green rule, a bold white figure exactly as the clip shows and a grey subline. (4) Quote card with the last line before the end, which carries the follow or realtor line. (5) White end card with the logo URL from `clips/pictory_urls.json` and "Free to start. Link in my bio.", with no subtitles. Write "Saint" instead of "St" in narration.
3. **App clips:** only use clips that have an entry in `clips/pictory_urls.json`. If a topic needs one that's missing, pick another topic or skip the app scene, and flag the missing clip to Miko. Narration over a clip must match its `shows` in `clips/manifest.json`.
4. **Stock:** find it with `search_media`. Openers must be recognisably Jamaica (Kingston, Montego Bay, Ocho Rios, Negril, Blue Mountains, the flag). Prefer clips whose description names Jamaica, and never use generic turquoise sea or another country. Before choosing, check `render/footage_log.json`: never reuse a `pictory:` id (or library clip) used by a video posted within 56 days. Add each new video's ids to `render/footage_log.json` and commit it.
5. **After the preview completes:** `list_preview_elements`. Check that no text box runs off the frame or overlaps another, and that each media element of the app clip has `type: video`. Fix a Drive URL read as an image with `update_preview_elements` (`visualUrl` + `type: video`). Then set every subtitle's `backgroundColor` to `rgba(0,0,0,0)` and `fontFamily` to DM Sans, colour #FFFFFF on footage, #4CAF50 on the black split scene and #2D7045 on the quote card. Text elements must also have transparent backgrounds.
6. `render_preview`, then poll `get_job_status` every 60 s until it completes. Schedule with `createScheduledPost` using the render's `videoURL` as `media` (Metricool copies the file), with the same caption, title and tiktokData rules as section 6.
7. **Report:** as section 7, plus each video's Pictory share link (`videoShareURL`) and its YouTube clearance code. Say that the finished frames weren't viewable from the run, so Miko should watch each one.
