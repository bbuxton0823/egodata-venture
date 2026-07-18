# Data Hat — Equipment List & Setup Guide

The rig: a worker's Android phone + a USB-C head-mounted camera + a phone app.
Phone stays in a pocket; the camera clips to a hat/headband angled down at the
hands. On-device hand-tracking preview + local recording + WiFi upload. No
laptop, no SD cards, no post-shift file transfers.

---

## 1. Hardware Bill of Materials

### Core kit (per worker)

| Item | Options | Est. Cost | Notes |
|---|---|---|---|
| **Phone** | Any Android 11+, USB-C OTG, 64GB+ free storage | $0 (worker's own) or $120 (refurb Pixel 5a / OnePlus N200) | Must support UVC camera HAL (standard since Android 9). iOS: USB-C capture is MFI-gated on iPhone 15+ and unreliable — Android-only at launch, iOS later. |
| **Camera module** | Ear-mount USB-C webcam: 1080p, ≥80° FOV HDR, fixed focus at ~40–80cm (hand distance). AliExpress/eBay OEM: "Mini USB-C Camera 1080P UVC" | $18–35 | Key: **wide FOV to keep hands in frame**, manual focus locked at arm's length. Avoid autofocus-seeking-in-the-dark modules. |
| **Hat / headband mount** | Baseball cap w/ sewn Velcro + clip bracket, or elastic headband w/ GoPro-style 1/4" tripod adapter | $8–15 | Camera clips to the brim or front panel. Angle set once with a calibration card (see §3). Stagers and cleaners can wear their own hat — we provide the mount clip. |
| **USB-C cable** | 1M right-angle USB-C, braided, strain relief | $6–10 | Right-angle connector at camera end avoids snagging. Cable runs from hat → collar → pocket. |
| **Bone-conduction mic** (optional) | Mini USB headset or phone's built-in mic (narration capture) | $15–30 | If using phone's mic through clothing, needs testing — bone conduction or lapel mic is cleaner. |
| **Power bank** (optional, long shifts) | 5,000 mAh slim, clips to waist | $12–20 | Phone recording 1080p30 = ~300–400MB/hr; battery drain ~8–12%/hr. A 10k mAh pack covers a full 8-hour shift. |

**Total per worker: ~$59–110** (worker's own phone) or **~$179–230** (dedicated phone).

### Spares / fleet kit (per 10 workers)

| Item | Qty | Cost |
|---|---|---|
| Spare camera modules | 3 | $55–105 |
| Spare USB-C cables | 5 | $30–50 |
| Replacement hat clips | 5 | $25–40 |
| Calibration card (printed) | 3 | $2 |
| **Fleet spares total** | | **~$100–200** |

### Operations gear

| Item | Purpose | Cost |
|---|---|---|
| WiFi router + external SSD NAS | On-prem ingest station (optional — phones can upload directly to cloud) | $150–300 |
| Label printer + barcode stickers | Tag each camera/phone pair so footage is traceable to a rig | $60 |
| Phone charging dock (10-port) | Fleet overnight charging | $40–80 |

---

## 2. Hat Camera Assembly

```
              hat crown
        ┌──────────────────────┐
        │   ┌──────────────┐   │  ← GoPro clip jaw clamps brim
        │   │   hat brim   │   │
        └───┴──────┬───────┴───┘
                   │ GoPro finger mount (hangs below brim)
              ┌────┴─────┐
              │ ELP box  │  ← under-brim mount, angled ~40–55° down
              │ camera   │     hands ~60–80cm ahead and below
              └────┬─────┘
                   │ USB cable
   ────────────────┼────────────────
   │  cable under inner hat band,   │
   │  out the back, down collar     │
   └────────────────────────────────┘
              │
              ▼
        [phone in pocket]
         recording + tracking
```

1. Clamp the GoPro clip jaw onto the hat brim from above.
2. Attach the ELP box housing to the GoPro finger mount hanging below the
   brim using 3M Dual Lock (or a 1/4"-20 GoPro tripod adapter if the housing
   has a threaded boss).
3. Aim the camera **40–55° downward** — the worker's hands at natural working
   height should fill 40–70% of the frame width. The under-brim position
   shields the lens from overhead light and stays out of the sightline.
4. Plug the USB cable into the camera, route it along the hat inner band,
   out the back, down the collar, into the pocket.
5. Worker puts hat on, opens app, taps the calibration screen (see §3).
6. The app shows a live preview with a hand-tracking skeleton — worker adjusts
   camera angle until both hands are reliably detected at their normal working
   posture. One-time ~30-second setup.

---

## 3. Camera Calibration (one-time per shift)

Worker opens the app, taps "Calibrate," and holds their hands out at their
natural working distance. The app:

- Detects both hands with on-device MediaPipe (TensorFlow Lite, runs at 30fps
  on any Snapdragon 600+ / Pixel 3 or newer).
- Draws green skeletons if both hands are in frame and at least 21 keypoints
  per hand are visible.
- Shows a quality score (hand visibility % × tracking confidence %).
- Calibration is stored per camera serial — the worker only recalibrates if
  they change hats or the camera gets bumped.

---

## 4. Phone App — Minimum Viable Feature Set

### Screen 1: Shift Start
- Worker ID + job type (picklist: kitchen clean, bathroom, staging assembly,
  etc.) + home ID (anonymized UUID).
- "Start Recording" — begins video capture from the USB-C camera *and*
  audio from the phone mic (or paired bone-conduction headset).
- Live hand-tracking skeleton overlaid on preview (on/off toggle).
- Total recorded time counter + storage remaining.

### Screen 2: In-Shift
- Narration toggle: hold button to narrate (walkie-talkie style) or always-on
  captioning. Voice is transcribed locally via on-device whisper or sent to
  cloud; transcription appears as live captions on screen.
- Task label quick-tap chips: worker taps "wipe counter," "fold towel," etc.
  to insert timestamped labels (redundant with narration, good for accuracy).
- Red recording dot + time remaining on battery.
- "Pause" (bathroom break, private moment) — stops recording, app logs gap.
- "Privacy Delete" — swipes the last 5 minutes from disk if something
  incidental happened.

### Screen 3: End Shift
- "Stop & Upload" — stops recording, compresses if needed, uploads to S3/R2
  via presigned URL and/or stores locally for later WiFi sync.
- Summary: hours captured, hand coverage %, tasks labeled, estimated QA score.
- Worker rating: thumbs-up/down on session (quality feedback loop).

---

## 5. Cloud Infrastructure (MVP)

```
Phone ──(WiFi)──► ingest API (S3 presigned upload)
                         │
                         ▼
                  S3 / R2 raw bucket
                         │
                         ▼
                  Processing queue (SQS / Redis)
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           Whisper    Hand pose   Task labels
              │          │          │
              └──────────┼──────────┘
                         ▼
                  Enriched episode DB
                         │
                         ▼
                  LeRobot export → Customer delivery bucket
```

All compute is serverless (Lambda / Cloudflare Workers) at this scale. Storage:
~400 MB/hr of raw 1080p30 footage. 1,000 accepted hours = ~400 GB raw → ~$10/mo
on R2/S3.

---

## 6. Why Android (not iPhone) for Launch

| Feature | Android (11+) | iPhone (15/16 USB-C) |
|---|---|---|
| UVC external camera | Native support since Android 9; standard API | Requires third-party app + adapter; MFI-gated for many cameras; unreliable frame access |
| Background recording | Yes (foreground service) | Restricted |
| On-device ML (MediaPipe) | Full TFLite GPU delegate | CoreML limited; MediaPipe iOS works but UVC pipeline kills the use case |
| Cost (refurb) | $100–150 for a capable device | $400+ |
| USB-C OTG power + data | Standard | Power delivery + data simultaneously works but ecosystem is thinner |

iOS is a v2 target. Android-only at launch; we ship the phone if the worker
doesn't own one.

---

## 7. Integration with the Prototype Pipeline

The prototype at `~/egodata-venture/prototype/` expects an MP4 file. The phone
app records to MP4 (H.264) and uploads it. Everything downstream (hand tracking,
transcription, labeling, QA, export) runs as-is — no modification needed.

The live hand-tracking preview in the app uses the same MediaPipe model
(`hand_landmarker.task`) the prototype already bundles.

---

## 8. Shopping List — Concrete Buys

This is what you buy today to put a working rig in someone's hands. All items
work together: camera → USB-C cable → Android phone → app. Total per rig:
**~$44** (worker's own phone) or **~$194** (dedicated phone included).

### Camera (pick one)

| Option | Model | Price | Why |
|---|---|---|---|
| **A — ELP USB box camera (PURCHASED)** | ELP 1080P USB Camera with box housing, 100° wide-angle, UVC. Search "ELP USB camera 100 degree 1080p box" on Amazon | $28–45 | Cased module — more durable than the bare board, better for a fleet. Mounts to the GoPro brim clip via 3M Dual Lock or 1/4"-20 adapter. UVC, plug-and-play on Android. Ships with USB-A cable; add USB-C OTG adapter or swap cable. |
| **B — Ear-mount mini cam** | "Ear-Mounted USB Camera 1080P HDR Mini Webcam" on AliExpress / eBay. USB-C native, 80° FOV, ear clip included | $15–25 | Already clips onto a hat brim. Slightly narrower angle — test that hands fill frame at working distance. |
| **C — Arducam** | Arducam 1080P Mini UVC USB Camera Module, 120° wide-angle | $25–40 | 120° FOV — nearly guarantees hands stay in frame. Larger (38×38mm) but still hat-mountable. |

**Purchased rig (prototype #1):** ELP 1080P USB camera with box housing +
GoPro hat clip, mounted to the **underside of the baseball-cap brim**, angled
down at the hands. The under-brim position shields the lens from overhead
light, keeps the camera out of the worker's sightline, and puts the lens at
the natural "look down at hands" angle. Assembly: GoPro clip jaw clamps the
brim from above → GoPro finger mount hangs below the brim → ELP box housing
attaches via 3M Dual Lock (or 1/4"-20 GoPro tripod adapter if the housing has
a threaded boss). Cable exits the rear of the housing, routes under the hat's
inner band, down the collar, to the phone in a pocket.

### Cable

- USB-C OTG adapter ($4–8) if using ELP/Arducam (they ship with USB-A cables).
- Or right-angle USB-C to USB-C, 1m braided (Anker or Amazon Basics, $6–12).
- Cable runs: camera (hat) → down neck → pocket.

### Phone (if worker doesn't own one)

- **Google Pixel 5a** (Android 14, USB-C OTG, 128GB) — ~$100–130 on Swappa.
- **OnePlus Nord N200** — ~$80–110.
- Any Android 11+ with USB-C OTG. Minimum: 64GB storage, 4GB RAM.
- **No iPhone** — UVC camera support on iOS is MFI-gated and unreliable.

### Hat + Mount

- **Baseball cap** — worker's own or dollar-store ($5).
- **GoPro hat clip** — "GoPro hat clip mount" on Amazon, $8–12. Clips to brim.
- **3M Dual Lock** (SJ3560, 250/250 density) — $8/roll. Holds camera firmly,
  removable. Better than Velcro for this.

### Power (full-shift capture)

- **Anker PowerCore Slim 10,000mAh** — $20–25. Belt-clip. Adds ~8 hrs recording.

### Verification App (free)

- Install **"USB Camera"** by ShenYaoCN from Google Play. Plug camera → open
  app → see live feed. If this works, the Data Hat app will too.

### Two Complete Rigs

**Budget (worker's own phone):**
```
ELP USB box camera               $38
USB-C OTG adapter               $6
GoPro hat clip                  $9
3M Dual Lock tape (1 strip)     $1
Baseball cap (worker's)         $0
Phone (worker's own Android)    $0
───────────────────────────────────
Total:                         ~$54
```

**Dedicated (we supply everything):**
```
ELP USB box camera               $38
USB-C OTG adapter               $6
GoPro hat clip                  $9
3M Dual Lock tape               $1
Baseball cap                    $5
Pixel 5a (refurb)             $115
Anker 10k power bank           $22
Right-angle USB-C cable         $8
───────────────────────────────────
Total:                        ~$204
```

### Where to Buy

| Item | Source | Search term |
|---|---|---|
| ELP box camera | Amazon | "ELP USB camera 1080p 100 degree box housing" |
| Ear-mount cam | AliExpress | "ear mounted USB camera 1080p UVC Android" |
| Pixel 5a | Swappa / Back Market | "Google Pixel 5a unlocked" |
| GoPro hat clip | Amazon | "GoPro hat clip mount" |
| USB-C OTG adapter | Amazon | "USB C OTG adapter" |
| 3M Dual Lock | Amazon | "3M Dual Lock SJ3560" |
