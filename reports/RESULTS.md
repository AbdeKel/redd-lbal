# Redd Lbal v0.4.0 - evaluation

| What | Messages | Scams caught (red) | Scams flagged (red+amber) | False alarms (red) | Flagged legit (red+amber) |
|---|---|---|---|---|---|
| REAL Moroccan messages (Darija/Arabic/French, held out) | 18,503 | - | - | 0.005% (1/18,503) | 0.016% (3/18,503) |
| UCI English SMS (held out, 2012 UK marketing spam*) | 971 | 21.8% | 58.1% | 0.1% | 0.4% |
| Scam/legit wordings never seen in training | 2,434 | 97.3% | 100.0% | 0.0% | 6.8% |
| challenge_set (current engine) | 120 | 95.5% | 100.0% | 0.0% | 0.0% |
| blind_set (current engine) | 70 | 95.0% | 100.0% | 0.0% | 0.0% |
| blind_set2 (current engine) | 61 | 100.0% | 100.0% | 0.0% | 0.0% |

*UCI spam is mostly 2012 UK marketing (ringtones, dating, premium numbers). Redd Lbal targets scams: a message with no attack vector (no link, code, money or contact request) is never called a scam, so much of it is 'suspicious' instead.

**Blind sets, first run (written after freezing the engine, evaluated once, before any fix):** blind-1 on v0.2: 92.5% of 40 scams flagged, 1 false alarm in 30 legit; blind-2 on v0.3: 100% of 36 scams flagged, 0 false alarms in 25 legit (raw outputs in reports/blind*_first_run_*.txt). The 'current engine' rows above are after we learned from those misses, so they are no longer blind.

## Scam types never seen in training (leave-one-campaign-out)

The ML brain is retrained WITHOUT any message of the campaign, then tested on it. The rules encode generic red flags (links, codes, money, pressure) written from the official guidance.

| Held-out campaign | n | AI alone caught | Full engine flagged | Full engine red |
|---|---|---|---|---|
| account | 154 | 100.0% | 100.0% | 100.0% |
| bank_otp | 132 | 72.7% | 100.0% | 100.0% |
| bank_phishing | 117 | 100.0% | 100.0% | 100.0% |
| family | 104 | 47.1% | 100.0% | 39.4% |
| gov_aid | 77 | 100.0% | 100.0% | 100.0% |
| investment | 92 | 89.1% | 100.0% | 100.0% |
| job | 116 | 100.0% | 100.0% | 100.0% |
| lottery | 104 | 100.0% | 100.0% | 100.0% |
| lure_link | 154 | 0.0% | 100.0% | 100.0% |
| marketplace | 77 | 100.0% | 100.0% | 100.0% |
| parcel | 116 | 100.0% | 100.0% | 96.6% |
| telecom_prize | 116 | 81.9% | 100.0% | 100.0% |
| traffic_fine | 84 | 100.0% | 100.0% | 100.0% |
| utility | 154 | 100.0% | 100.0% | 95.5% |
| whatsapp_hijack | 92 | 3.3% | 100.0% | 100.0% |

## Original prototype vs Redd Lbal (same messages)

| Set | Original: scams caught | Original: false alarms | Redd Lbal: scams caught (red) | Redd Lbal: false alarms (red) |
|---|---|---|---|---|
| challenge_set | 33.3% | 20.4% | 95.5% | 0.0% |
| blind_set | 45.0% | 20.0% | 95.0% | 0.0% |
| blind_set2 | 38.9% | 36.0% | 100.0% | 0.0% |

* Original prototype on 3,000 real Moroccan messages: **0.3%** false alarms.
* Official Moroccan sites flagged as DANGER by the original: **17/25** (https://www.cihbank.ma, https://www.attijariwafabank.com, https://www.bankofafrica.ma, https://www.groupebcp.com, https://www.sahambank.com, https://www.bmci.ma, https://www.iam.ma, https://www.inwi.ma, https://www.orange.ma, https://www.cnss.ma, https://www.asd.ma, https://www.rsu.ma, https://www.daamsakane.ma, https://www.bkam.ma, https://www.lydec.ma, https://www.avito.ma, https://www.jumia.ma). Redd Lbal: 0/25.
* Latency (pure Python, 1 CPU core): p50 **0.473 ms**, p99 2.173 ms -> ~1,642 messages/second/core.

## Unseen templates by campaign

| Campaign | n | caught (red) | flagged |
|---|---|---|---|
| account | 154 | 100.0% | 100.0% |
| bank_otp | 132 | 100.0% | 100.0% |
| bank_phishing | 117 | 100.0% | 100.0% |
| family | 104 | 66.3% | 100.0% |
| gov_aid | 77 | 100.0% | 100.0% |
| investment | 92 | 100.0% | 100.0% |
| job | 116 | 100.0% | 100.0% |
| lottery | 104 | 100.0% | 100.0% |
| lure_link | 154 | 100.0% | 100.0% |
| marketplace | 77 | 100.0% | 100.0% |
| parcel | 116 | 96.6% | 100.0% |
| telecom_prize | 116 | 100.0% | 100.0% |
| traffic_fine | 84 | 100.0% | 100.0% |
| utility | 154 | 95.5% | 100.0% |
| whatsapp_hijack | 92 | 100.0% | 100.0% |

| Legit category | n | false alarm (red) | flagged |
|---|---|---|---|
| ask_friend | 65 | 0.0% | 0.0% |
| bank_notice | 58 | 0.0% | 0.0% |
| business | 87 | 0.0% | 0.0% |
| chat | 87 | 0.0% | 0.0% |
| delivery | 38 | 0.0% | 0.0% |
| family_money | 52 | 0.0% | 73.1% |
| gov | 58 | 0.0% | 0.0% |
| link_share | 52 | 0.0% | 25.0% |
| otp | 44 | 0.0% | 0.0% |
| promo | 87 | 0.0% | 0.0% |
| telecom | 52 | 0.0% | 0.0% |
| warning | 65 | 0.0% | 0.0% |
