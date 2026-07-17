# Egocentric Home-Task Data Co. — Business & Technical Outline

Working name ideas: **HomeHands Data**, **FirstPerson Chores**, **EgoDomestica**.
Core concept: pay people to record first-person video of real household work (cleaning,
laundry, dishes, organizing, cooking) with a head/hat-mounted camera aimed at their hands.
Enrich that footage with hand tracking, task labels, and narration transcripts. License the
enriched dataset to robotics labs training VLA (vision-language-action) models and humanoid
robots.

---

## 1. Why now (market timing)

- **Data is the bottleneck in embodied AI, not compute.** Every major lab (Physical
  Intelligence, Figure, 1X, Tesla Optimus, NVIDIA GR00T, Google DeepMind) needs real-world
  manipulation data at a scale that doesn't exist.
- **Human egocentric video is proven to transfer.** NVIDIA EgoScale: pretraining on 20k+ hrs
  of egocentric human video improved robot task success ~54%. EgoMimic: 1 hr of human
  egocentric data > 1 hr of robot teleoperation data for co-training.
- **Teleoperation doesn't scale** ($50–200+/hr, robot required per operator). A human with a
  $250 camera produces data while doing work they'd do anyway.
- **Competitors exist but are generalists** (Claru, iMerit, Scale-adjacent annotation shops,
  Ant Group's AoE smartphone system). Nobody owns the *domestic tasks* niche with deep
  hand-centric annotation. Domestic manipulation is exactly where humanoid robots are aimed
  first (folding, loading dishwashers, tidying).
- **The buyer market is growing faster than supply.** Every new humanoid startup = a new
  dataset customer.

## 2. Product definition

You sell **enriched egocentric episodes**, not raw video. One episode = one task instance.

Per episode deliverable:
- First-person video (1080p+, 30–60fps, wide FOV, hands in frame)
- Time-synced 2D + 3D hand pose (MANO-format hand meshes via HaMeR/WiLoR-style models)
- Task segmentation + labels from a controlled taxonomy
  (e.g., `pick_up(object)`, `wipe(surface)`, `fold(cloth)`, `pour(container)`)
- Narration transcript (worker narrates what/why while working → Whisper → time-aligned text)
- Object detections / interaction hotspots
- Metadata: home type, lighting, camera rig ID, worker ID (pseudonymous), quality scores
- Export formats: **LeRobot** (parquet + mp4 — the emerging standard), Open X-Embodiment
  RLDS as secondary

The enrichment is the moat. Raw video is approaching commodity; synced 3D hand trajectories
+ language + task structure is what labs actually pay for.

## 3. Hardware kit (the "Data Hat")

Target: <$300/unit, idiot-proof, 2+ hr battery, one-button operation.

| Component | Option A (quality) | Option B (budget) |
|---|---|---|
| Camera | GoPro Hero / DJI Action (used ~$180–250) | Worker's own Android phone (AoE model — $0) |
| Mount | Headband/hat clip w/ fixed downward pitch (~$25) | same |
| Mic | Bone-conduction or clip-on lav (~$30) for narration | phone mic |
| Storage | SD card, upload at home on WiFi | direct app upload |
| Extras | IMU from phone if used; QR-coded calibration card | — |

Key spec decisions:
- **Fixed camera angle aimed at hands** — consistency across workers matters more than
  resolution. A standardized mount = standardized data = premium pricing.
- **Narration is mandatory** — it becomes free language labels after Whisper transcription.
- Start with Option B (phones) for the pilot to prove the pipeline at near-zero capex;
  move to standardized cams for the quality tier.

## 4. Software pipeline

```
[Worker app/camera] → [Upload + ingest (S3/R2)] → [Transcode/normalize (ffmpeg)]
   → [Auto-enrichment workers]
        ├─ Whisper: narration → timestamped transcript
        ├─ Hand pose: MediaPipe/HaMeR → 2D/3D hand keypoints + MANO meshes
        ├─ Objects: Grounding-DINO/YOLO → interacted-object boxes
        └─ Task segmentation: model pretrained on Ego4D / EPIC-KITCHENS → draft labels
   → [Human QA station (Label Studio / CVAT, self-hosted)]
        └─ verify/correct task boundaries + labels (1 reviewer : ~4–6 hrs footage/day)
   → [Dataset compiler → LeRobot-format shards + manifest + license metadata]
   → [Delivery: versioned dataset releases to customers]
```

Phase-0 buildable with off-the-shelf open source. Nothing here requires novel ML — the
novelty is operational (workforce + consistency + QA + contracts).

Privacy pipeline (non-negotiable, runs before anything is stored long-term):
- Face blur for anyone other than the consenting worker (homeowners, kids, bystanders)
- Audio bleep for names/addresses; transcript PII scrub
- On-device or at-ingest "private moment" delete gesture (worker covers lens / app button)
- No recording in bathrooms/bedrooms per protocol

## 5. Workforce model

Three sourcing tiers:
1. **Partner with cleaning services** (best): cleaners already work in varied homes daily.
   Pay the company + worker a royalty per accepted data-hour. They clean anyway — camera is
   passive. Requires homeowner consent addendum (see §6).
2. **Gig workers in their own homes**: lowest legal friction (their own home), decent task
   variety, easy onboarding. Pay per verified hour (~$20–25/hr equivalent).
3. **Home stagers staging vacant homes** (partner channel — see §5a): stagers
   physically furnish empty homes for real-estate listings — assembling furniture,
   making beds, arranging kitchens, hanging art, placing decor. That is hours of
   dense, bimanual manipulation in *empty* homes with one consented party (the
   seller) and no residents. Potentially the best data channel we have.
## 5a. Home-stager channel (deep dive)

Why it's structurally attractive:
- **The privacy problem inverts.** Occupied homes need homeowner + family consent,
  face blurring, PII scrubbing. A vacant staged home has one counterparty: the
  seller (via the listing agent). The staging company already holds a signed
  contract to work in that home — we add a recording rider. No kids, no
  bystanders, no personal belongings in frame. Cleanest possible consent chain,
  and consent-chain quality is the moat (§9).
- **The work is manipulation-dense.** Furniture assembly (hex keys, cam locks,
  drawer slides), bed-making, hanging/leveling frames, unboxing, placing decor,
  arranging table settings, steaming linens. These are exactly the long-horizon,
  bimanual, tool-use tasks humanoid demos struggle with — and they're scarce in
  existing datasets (Ego4D is heavy on cooking/social, not furniture assembly).
- **Every home is a new environment.** Stagers rotate constantly across floor
  plans, lighting, and furniture styles → environment diversity for free, the
  property labs pay a premium for.
- **Aligned economics.** Stagers are paid by the staging company per job; we pay
  a per-accepted-hour royalty on top. They're already working — the camera is
  passive. Same math as the cleaning-company tier, but with zero-occupant homes.
- **No bathroom/bedroom exclusions needed** — nobody lives there. Whole-home
  capture is in protocol, including closet organization and garage tasks.

What's different vs. cleaning footage (the tradeoff):
- Staging is **setup** work (assemble, place, arrange), not **maintenance** work
  (wipe, wash, fold, tidy). Buyers want both; staging complements cleaning data
  rather than replacing it. Tool-use and assembly make it arguably the premium
  tier, not the cheaper one.
- Staging jobs are episodic (a home stages in 1–2 days, then de-stages weeks
  later) → throughput per worker is lower than a cleaner's daily route. Mitigate
  by signing the *company*, not individuals: one mid-size staging firm runs many
  concurrent jobs, and we equip the whole crew.
- Staging companies have low headcount per metro (a handful of crews) → this is
  a relationships business: 5–10 signed staging partners could anchor the
  channel; you don't need hundreds.

Revenue/expense notes:
- Staging is a $2.5k–4k-per-job service industry (30–90 day furniture rental
  contracts); companies are operationally sophisticated and margin-hungry → a
  per-hour data royalty is a genuinely interesting side-revenue pitch for them.
- Equipment: same ~$250 hat-cam kits; crews are small, so kit cost is trivial.
- Also capture **de-staging** (disassembly, packing, loading) — doubles the
  episode yield per home and adds pack/unpack tasks buyers can't get elsewhere.

Positioning: this becomes the **premium tier** in the catalog — "Assembly &
Arrangement, captured in real vacant homes" — sold alongside (not instead of)
the cleaning/maintenance corpus.

Ops mechanics: task assignment app ("today: kitchen deep-clean, 2 loads laundry, narrate"),
upload queue, per-hour acceptance criteria (hands visible ≥70%, narration coverage ≥50%,
label QA pass), payment on acceptance.

## 5b. Overseas workforce (labor arbitrage + market access)

Collecting data in developing countries multiplies the business on two axes:
**cost per data-hour drops ~60–80%**, and **tasks not common in Western homes**
(washing by hand, floor-sweeping with brooms, clothesline work, charcoal/kerosene
cooking) fill gaps in the training distribution that US-only data misses.

### Country candidates (ranked by existing annotation workforce + staging/cleaning ecosystem)

| Country | Cleaning/staging industry | Labor rate (gig/hr) | Smartphone penetration | Annotation workforce | Risk factors |
|---|---|---|---|---|---|
| **Philippines** | Strong — large domestic-worker sector, active real-estate staging market, English-speaking narration | $3–6 | Very high (Android dominant) | Existing BPO/annotation hubs (TaskUs, Scale AI vendors) | Typhoons disrupt ops; some regions have spotty power |
| **Vietnam** | Growing — domestic cleaning services in HCMC/Hanoi; staging nascent but real estate is booming | $2–5 | High (Xiaomi/Samsung Android) | Growing annotation sector (FPT Software, VNG) | Language: narration in Vietnamese needs separate Whisper model (works fine, just not English) |
| **India** | Massive — domestic workers + Gurgaon/Mumbai/Bangalore staging market, English-speaking workforce | $2–5 | High (Android dominant) | World's largest annotation workforce | Home quality variance extreme (mansion → slum in one data day); caste dynamics in domestic work |
| **Colombia** | Strong — domestic service sector in Bogota/Medellin + growing staging market, Spanish narration | $3–6 | High (Android) | Growing BPO sector (Teleperformance, Lean Staffing) | Security: some neighborhoods unsafe for equipment; content insurance needed |
| **Mexico** | Strong — domestic workers + CDMX/Monterrey staging, proximity to US buyers | $4–8 | High (Android) | Mature annotation hubs (nearshoring for US tech) | Narration in Spanish; higher labor cost than SE Asia |
| **South Africa** | Moderate — domestic workers + Cape Town/JHB staging, English-English narration, strong labor laws | $4–7 | Moderate-high (Android) | Small but growing annotation sector | Equipment theft risk; labor-law complexity |

### Channel comparison: domestic vs. overseas

| Metric | US domestic workers | US stagers | Overseas (Philippines/Vietnam/India) |
|---|---|---|---|
| **Labor cost per data-hour** | $20–30 | $25–35 (stagers are skilled) | $2–6 |
| **All-in cost per enriched hour** | $35–55 | $40–60 | $8–18 |
| **Consent complexity** | High (homeowners) | Low (seller via agent) | Medium (varies by country; simpler if worker films own home) |
| **Narration language** | English | English | English (PH/IN), Vietnamese, Spanish → multi-language corpus is a positive differentiator for global robot deployment |
| **Task diversity** | Western homes | Vacant Western homes | Adds hand-wash, floor-sweep, charcoal cooking, bucket laundry — distribution edge |
| **Equipment logistics** | Ship domestically | Ship domestically | Ship + local partner handles distribution + replacement |
| **Buyer perception** | "US data = premium" | "US data = premium" | "overseas data = cheaper but less controlled" → mitigate with rigorous QA + consent docs |

### Operational model

**Don't try to run overseas ops directly.** Partner with an existing annotation
company that already has a workforce in-country and is looking to expand into
video data collection (they're all looking — iMerit, Sama, Scale vendors,
local BPOs). They bring:

- Existing workforce with smartphones
- HR/payroll/payment rails
- Physical office for equipment staging and returns
- On-the-ground QA supervisors

You bring: the hat-cam kits, the app, the pipeline, the consent framework, and
the buyer relationships. Revenue split: you keep the buyer contract; they get
~40–55% of the data-hour price for sourcing the workforce + local ops.

### Narration strategy

- **Philippines / India**: English narration works; no additional pipeline work.
- **Vietnam / Colombia / Mexico**: narrate in local language. Whisper handles
  Vietnamese and Spanish with good accuracy; task labels map to the same
  taxonomy (the taxonomy is language-agnostic — `wipe(plate)` = `lau đĩa` =
  `limpiar plato`). The multi-language corpus is a *selling point*, not a bug:
  "our data is multilingual because your robot ships globally."

### Equipment notes for overseas

- Same kit works everywhere — USB-C is universal, Android phones are dominant.
- Use refurb phones if workers don't own one (identical to US fleet).
- SIM card with data plan for upload (cheap in all candidate countries).
- Power banks more important (less reliable grid in some regions).

### Risk: data quality perception

The biggest risk is that a US lab looks at an overseas dataset and thinks
"cheap, uncontrolled, probably not real." Mitigations:

- Same camera rig, same app, same pipeline, same QA gate. The data looks
  identical to US-captured data to a dataloader — it's a LeRobot episode with
  the same schema.
- Publish QA reports per episode; make the QA gate public (open-source the
  metrics).
- Lead with US + staging data as the flagship; add overseas as a volume tier
  once the brand is established.
- Do NOT market it as "cheap overseas data." Market it as "multi-country,
  multi-language, multi-home-type training corpus." Last line of the slide:
  "Collected in the United States, Philippines, Vietnam, India, Colombia, and
  Mexico." That's a strength, not a disclosure.

### Recommendation

Start US-only (stagers + cleaners) for brand + quality anchors. Add overseas
in Phase 2 via a single partner-country pilot — **Philippines** is the obvious
first pick: English narration, existing annotation workforce, strong
cleaning/staging sectors, US-aligned legal framework. One 6-month pilot with
10–20 workers → validate cost/quality/consent chain → then add Vietnam and
Colombia if the numbers hold.
## 6. Legal & privacy (the make-or-break section)

- **Worker consent**: employment/contractor agreement covering recording, likeness, data
  licensing. Workers are authors of nothing — work-for-hire or explicit assignment.
- **Homeowner consent**: written addendum for every home filmed. Partner cleaning companies
  already have contracts — add a recording rider with opt-out (opt-out homes simply aren't
  recorded). Offer homeowners a discount as incentive.
- **Bystanders**: face-blur pipeline + contractual ban on filming other people up close.
- **Jurisdiction**: two-party consent states (CA!) affect audio — get homeowner audio consent
  or strip environmental audio and keep only worker narration mic channel.
- **Data licensing to labs**: you grant commercial training licenses; your upstream consents
  must explicitly permit this. This is where naive competitors die — a lab will audit your
  consent chain before paying.
- **GDPR/CCPA**: pseudonymize worker IDs, honor deletion (hard with trained models — bake
  this into license terms: licenses cover models trained before deletion request).
- Get a real attorney before the first paid hour. Budget $10–20k for the consent stack.

## 7. Unit economics (estimates, validate in pilot)

Cost per enriched, accepted data-hour:
- Worker pay: $20–25 (gig) or $8–15 (royalty split via cleaning partner)
- QA labor: $4–8 (15–20 min reviewer time per footage hour at $20/hr)
- Compute/storage/bandwidth: $1–3
- Amortized hardware: $1–2
- **All-in: ~$30–45/hr** (gig model), **~$15–30/hr** (partner model at scale)

Revenue: market rates are opaque, but enriched, rights-clean egocentric data with 3D hand
annotation commands a large premium over raw video. Anchors: teleop data costs labs
$50–200+/hr to produce internally; annotation shops charge $5–15/hr of footage for labeling
alone. Realistic early pricing: **$75–150+/licensed hour** for pilot customers, with volume
discounts and exclusivity premiums (e.g., 6-month exclusive on a task category = 2–3x).

Break-even sketch: 10k enriched hours/yr at $100 avg = $1M revenue against ~$350–450k
direct cost. The business is a margin game won on acceptance rate and QA efficiency.

## 8. Go-to-market

Phase 1 customers = design partners, not revenue:
- Offer 100–500 free/cheap hours to 1–2 labs (a humanoid startup, a university lab, or an
  open-source VLA team) in exchange for quality feedback and a logo/testimonial.
- Publish a small open sample dataset (50–100 hrs, one task category) to GitHub/HuggingFace
  in LeRobot format — this is the demo, the SEO, and the credibility engine. DROID and OXE
  made their labs famous; a "OpenHomeHands-100" dataset makes you the category name.
- Then sell: expanding licenses to the design partners + inbound from the open dataset.
- Buyers' procurement trigger: they're launching a home-robot demo and need kitchen/bedroom
  manipulation data yesterday. Be findable when that moment hits.

## 9. Competition & differentiation

| Player | Their model | Your edge |
|---|---|---|
| Claru, iMerit, Shaip | General-purpose egocentric collection services | Domestic-task specialization + deeper hand/task annotation |
| Ant Group AoE (research) | Always-on smartphone collection | You're commercial + rights-clean for Western labs |
| Labs collecting in-house | Teleop rigs, slow, expensive | 5–10x cheaper per hour, faster scale |
| Ego4D / EPIC-KITCHENS (academic) | Free but non-commercial / weakly licensed | Commercial license + richer labels + custom task coverage |

Differentiators to defend: (1) consent chain clean enough to survive a lab's legal audit,
(2) hand-centric enrichment quality, (3) task taxonomy matched to what humanoid product
teams actually demo, (4) custom-collection SLA ("500 hours of dishwasher loading, 3 weeks").

## 10. Honest risks

- **Embodiment gap**: human hands ≠ robot grippers. Mitigation: retargeting research is
  moving fast (EgoMimic etc.); optionally add a "gripper-proxy" tool workers hold for
  some tasks, or instrumented gloves on the premium tier.
- **Data commoditization**: if labs decide raw internet-scale egocentric video is enough,
  enrichment margin shrinks. Mitigation: stay on the quality/rights end, not volume.
- **Privacy incident**: one viral "cleaner filmed my kid" story can kill the brand.
  Mitigation: blur pipeline, protocols, insurance, never cheap out on §6.
- **Buyer concentration**: ~20 serious buyers worldwide. Mitigation: open dataset builds
  inbound; also sell to robot-hardware cos, insurers (task verification), and later
  license the taxonomy/QA platform itself.
- **Platform risk**: a big player (Scale, Appen) copies you. Mitigation: speed + the
  cleaning-company partner network is a real operational moat that takes years to build.

## 11. Phased roadmap

**Phase 0 — Spike (2–3 weeks, <$1k):** one person (you), one phone/GoPro, 10–20 hrs of your
own chores. Build the ingest → Whisper → hand-pose → Label Studio pipeline end-to-end.
Deliverable: one LeRobot-format episode + a verdict on auto-label quality.

**Phase 1 — Pilot (2–3 months, ~$30–60k):** 5–10 gig workers in their own homes, 300–500
hrs, real consent docs (attorney), QA station, open 50-hr sample dataset, 1–2 design-partner
labs. Validate: acceptance rate, cost/hour, whether a lab will actually pay.

**Phase 2 — Commercial (6–12 months):** first cleaning-company partnership, plus
1–2 home-staging company pilots (§5a) as the premium "Assembly & Arrangement"
tier; 5–10k hrs/yr run-rate across channels, paid licenses, task-category
exclusives, premium tier (gloves/gripper-proxy, staged capture homes).

**Phase 3 — Platform:** self-serve custom-collection marketplace; license the QA/labeling
stack; expand to non-home verticals (restaurant kitchens, hotel housekeeping — commercial
consent is simpler than residential).

## 12. Immediate next steps

1. Phase 0 spike — buildable today with open source (I can scaffold the pipeline: ingest +
   Whisper narration transcripts + MediaPipe/HaMeR hand tracking + Label Studio config +
   LeRobot exporter).
2. Talk to 2–3 robotics labs' data teams (cold email works; they're hungry) — validate what
   they'd pay for before spending on workers.
3. Talk to 1–2 local cleaning company owners — would they take a per-hour royalty for
   camera-equipped crews with consenting customers?
4. Attorney consult on the consent stack (CA two-party consent for audio!).
