# Redd Lbal (رد البال) — real-time scam detection for Moroccan messages

**Spam filters exist. None of them understand Darija.**
Paste (or share) a suspicious SMS / WhatsApp message in Darija (Arabic or Latin letters), French, Arabic or English.
In under a millisecond you get a verdict (scam / suspicious / no signs), the exact words and links that triggered it,
the scam type, and what to do — in Darija, French, Arabic or English.

IBM Z Datathon 2026 · ENIAD Berkane

---

## Why this matters (cite these in the video)

* **49.3% of scams in Morocco are completed in under 30 minutes; average loss $733 per victim** (global average $504) —
  Kaspersky / Censuswide study, April 2026 ([Morocco World News, 16 Jun 2026](https://www.moroccoworldnews.com/2026/06/320631/kaspersky-ai-fueled-scams-cost-moroccans-733-per-hit-strike-in-under-30-minutes/)).
  A scam check has to be *real-time*: that is the "Real-Time AI for Critical Decisions" track.
* **DGSSI critical alert (Apr 2026)**: fake traffic-fine SMS, often from foreign numbers; authorities never send fines
  from international numbers and only use `.gov.ma` platforms ([InfoMagazine](https://www.infomagazine.ma/cybersecurite/arnaque-aux-amendes-routieres-alerte-critique-de-la-dgssi-au-maroc-14428-2026/)).
* **Ministry of Justice (Jun 2026)**: "Avis d'exécution administrative" SMS threatening account seizure, link to a free domain
  ([TelQuel](https://telquel.ma/instant-t/2026/06/19/le-ministere-de-la-justice-alerte-contre-une-nouvelle-campagne-de-scam-via-sms_1994947)).
* **Maroc Telecom (Apr 2026)**: fake "free 0661 number" offers ([TelQuel](https://telquel.ma/instant-t/2026/04/14/arnaques-numeriques-maroc-telecom-met-en-garde-contre-des-offres-frauduleuses_1984377/)).
* **WhatsApp relative impersonation** is spreading (Le Matin, Sep 2026).

---

## What changed vs. the first prototype (ScamShield)

The first prototype had good instincts (big fonts for seniors, text-to-speech, examples, a typosquatting check, a FastAPI
backend). We kept those ideas. But measured on Moroccan messages it was close to unusable:

| Problem in the original | Measured effect | Redd Lbal |
|---|---|---|
| Text model trained only on 2012 **English** UK spam | caught **33–45%** of Moroccan scams, **20–36%** false alarms on our test sets | Trained on ~118k **real** Darija/Arabic/English messages + ~5k Moroccan scam messages from 15 documented campaigns |
| Typosquat list of **French** sites (ameli.fr, impots.gouv.fr…), Levenshtein ≤ 2 | `orange.ma` flagged as a fake of `orange.fr` | Registry of **real Moroccan official domains** (banks, telecoms, Barid, CNSS, ASD, RSU, *.gov.ma…) |
| URL model learned dataset artifacts ("http://" = malicious) | **17 of 25 official Moroccan sites** (CIH, IAM, CNSS, Bank Al-Maghrib, ASD…) flagged DANGER, while `cih-securite.com` passed as safe | 0 of 25 flagged; impersonation, decoy subdomains, free hosting, shorteners detected |
| Binary Safe/Danger + "you're totally safe" + "visit the site securely" button | dangerous false reassurance | 3 levels (scam / suspicious / no signs), never "100% safe", explains *why* |
| Printed every message to the server console | privacy leak | messages never logged or stored; radar keeps counts only, with differential privacy |
| `app.js` and `emails.csv` missing, duplicated link logic | prototype could not run end to end | runs as API, as a single offline HTML file, and as a published demo |

Full numbers: [`reports/RESULTS.md`](reports/RESULTS.md).

---

## Results (v0.4.0)

| Test | Result |
|---|---|
| **18,503 real held-out Moroccan messages** (DODa, YouTube MYC, Twitter MAC) | **1 false "scam" verdict (0.005%)**, 3 flagged in total (0.016%) |
| Scam wordings **never seen in training** (held-out templates, 1,689 scams) | **97.3% red, 100% flagged** · legit look-alikes (745): **0% red**, 6.8% "suspicious" |
| **Blind sets, first run** (written after freezing the engine, scored once) | blind-1 (v0.2): 92.5% of scams flagged, 1/30 false alarm · blind-2 (v0.3): **100% flagged, 0/25 false alarms** — incl. 5 real fake-fine SMS quoted verbatim by an anti-scam site |
| **Scam types never seen** (leave-one-campaign-out, 15 campaigns) | full engine flags **100% of every unseen type**; the AI alone ranges from 0% (curiosity links) and 3% (WhatsApp hijack) to 100% → why we need two brains |
| Latency (pure Python, 1 core, x86) | **p50 0.41 ms**, p99 2.1 ms · ~1,800 msg/s/core · 2 cores ≈ 3,000 msg/s ≈ 258 M msg/day |
| Python (LinuxONE) vs JavaScript (phone) | **1,760 / 1,760 identical** verdicts, scores, highlights, explanations |

**Be honest in the pitch:** the scam side of the training data is *synthetic* (templates written from the documented 2025–2026
campaigns), and the challenge/blind sets were written by us. The real-message false-alarm rate is fully real. The real exam is
**your collected messages** (`data/real_messages.csv`, see "Next steps") — `training/evaluate.py` picks them up automatically.

---

## How it works

```
message ─► tokenizer (URLs / phones / e-mails protected; Arabic + Arabizi normalisation: أ→ا, ة→ه, 3afak kept)
        ├─► Brain 1 — AI: char n-grams (2-5) + word bigrams → TF-IDF → logistic regression (40k features, 1.2 MB JSON)
        ├─► Brain 2 — rules from official guidance: 43 rules over ~1,200 multilingual phrases + 57 official domains
        │       links: impersonation (cih-securite.top), decoys (cihbank.ma.verify-x.top), typosquats, shorteners,
        │              free hosting, cheap TLDs, gov claim + non-.gov.ma link (DGSSI)
        │       sender: foreign number + "I'm the ministry/bank" (DGSSI) · codes/CVV requests (negation-aware:
        │              "ne le communiquez jamais" is NOT a request) · WhatsApp hijack · new-number relative + money ·
        │              fees to receive a prize/job/parcel · guaranteed investment · task scams · pressure & secrecy
        └─► fusion (calibrated on a dev split): risk = σ(a·AI + b + Σ red flags)
               no attack vector (no link/code/money/contact) → never "scam"
               ambiguous vector only (relative asking for 100 dh) → at most "suspicious"
               official guidance violated (critical rule) → always "scam"
        ─► verdict + scam type + highlighted words + reasons + advice (dar / fr / ar / en) + "warn the family" text
```

Why logistic regression and not a transformer? Every word's contribution is explainable, it runs in **0.4 ms on one core**
with **no numpy** (pure Python on LinuxONE, plain JavaScript on a phone), and the whole model is one JSON file — no binary
pickles, so no s390x big-endian surprises.

### Privacy by design (Privacy-preserving AI track)
* On the phone/demo page the message **never leaves the device**.
* On LinuxONE the message is analysed **in memory** and forgotten — never logged, never stored.
* **Scam Radar**: the server keeps only `(hour, scam type, verdict) → count`. Published numbers get **Laplace noise
  (ε = 1)**, counts under 3 are hidden, snapshots are cached 60 s so noise can't be averaged away, and a spike detector
  raises **"trending" alerts** when a scam type is 3× its usual daily volume → early warning for DGSSI / banks / operators.

---

## Run it

```bash
pip install -r requirements.txt                 # Python 3.9+
python data/build_dataset.py                    # real corpora + synthetic campaigns -> data/processed/
python training/train_ml.py                     # Brain 1 -> model/ml.json
python training/calibrate.py                    # optional: re-tune fusion on a dev split -> model/fusion.json
python -m engine.export                         # knowledge + ML + fusion -> model/redd_lbal.json
python webapp/build_web.py                      # single-file app -> webapp/dist/redd-lbal.html
python training/evaluate.py                     # -> reports/RESULTS.md (+ before/after vs original)
python tests/parity_test.py                     # Python vs JavaScript must be identical (needs node)
```

Serve it (web app at `/`, analysis done by the server):

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000      # FastAPI
python3 server/stdlib_server.py --port 8000            # zero-dependency fallback (stdlib only)
```

API: `POST /api/check {"text","sender","lang"}` · `POST /api/batch {"messages":[...]}` · `GET /api/radar` · `GET /api/health`

`webapp/dist/redd-lbal.html` also works **offline by double-click** (engine + model inside the file).

### On IBM LinuxONE Community Cloud (s390x)
1. Copy the repo (you don't need `data/raw/urls.csv`; it's only for re-running the original prototype).
2. Inference needs **only Python 3** — `python3 server/stdlib_server.py --port 8000` works with zero pip installs.
   FastAPI is nicer for the video (`/docs` page) — try `pip install fastapi uvicorn`; if it fails, use the stdlib server.
3. Run `python3 benchmarks/bench.py` **on LinuxONE** and put the s390x numbers in the video (`/api/health` reports
   "IBM LinuxONE / IBM Z (s390x)", and the web app shows "Checked on IBM LinuxONE … 0.4 ms").
4. Training needs scikit-learn; if it won't install on s390x, train on a laptop and copy `model/redd_lbal.json` — it's portable.

---

## Project layout

```
engine/       text.py (tokenizer/normaliser) · ml.py (pure-Python scorer) · core.py (rules, fusion, explanations)
              knowledge.py  ← EDIT THIS: phrase lists, official domains, rules, Darija/FR/AR/EN texts
              export.py     → model/redd_lbal.json
data/         generator.py (campaign templates) · build_dataset.py · challenge_set.csv · blind_set*.csv
              raw/ DODa sentences, MYC YouTube, MAC tweets, UCI SMS
training/     train_ml.py · calibrate.py · evaluate.py · loco.py (unseen scam types)
server/       service.py (privacy, radar) · app.py (FastAPI) · stdlib_server.py
webapp/       app.html (UI) · engine.js (JS twin of the engine) · build_web.py → dist/redd-lbal.html
tests/        parity_test.py (Python == JavaScript)
benchmarks/   bench.py (run on LinuxONE)
reports/      RESULTS.md, results.json, loco.json, blind first-run outputs
legacy/       the original prototype + its retrained models (for the before/after comparison)
```

Data credits: DODa (github.com/darija-open-dataset, research/educational use), MYC (github.com/MouadJb/MYC),
MAC (github.com/LeMGarouani/MAC), UCI SMS Spam Collection. Cite them in the submission.

---

## Next steps (in this order)

1. **Collect real messages — the single most important thing.** Each teammate asks ~10 relatives for screenshots of scam
   SMS/WhatsApp they received (+ normal messages). Remove names and numbers. Target ≈150 scams + 300 normal. Put them in
   `data/real_messages.csv` (template in `data/real_messages_TEMPLATE.csv`) and run `python training/evaluate.py`.
   **Test only — never train on them.** "Tested on N real messages from Moroccan families" is the line judges remember.
2. **Native-speaker pass on the Darija** in `engine/knowledge.py` (the `TEXT` explanations and phrase lists). You will
   spot phrasings we missed — add them, re-run `python -m engine.export && python webapp/build_web.py`.
3. **Deploy on LinuxONE** and record the benchmark + `/api/health` + a live check from a phone.
4. Optional: add the VISH-DARIJA-TTS text layer (zenodo.org/records/20039126) under `data/raw/vish_darija/` and rebuild
   (loader in `build_dataset.py`; check field names). Don't republish its raw text (license).
5. Optional (Med, Flutter): an Android app that receives **"Share → Redd Lbal"** from WhatsApp/SMS and either calls
   `/api/check` or loads `dist/redd-lbal.html` in a WebView (works offline).

### 3-minute video, suggested beats
0:00 hook — "49% of scams in Morocco succeed in under 30 minutes." · 0:15 problem — spam filters don't read Darija ·
0:30 live demo: fake fine from +44 → red stamp, highlighted words, link X-ray, "warn the family" ·
1:10 family "new number" scam in Arabizi; real bank OTP → no false alarm · 1:40 two brains + unseen-scam-type result ·
2:05 LinuxONE: 0.4 ms, millions/day, privacy + radar with differential privacy · 2:35 numbers vs. first prototype,
real-message test · 2:50 call to action (operators, banks, DGSSI).

**If you clicked or shared details:** call your bank to block the card, then report to the police (19) or on e-blagh.ma.
