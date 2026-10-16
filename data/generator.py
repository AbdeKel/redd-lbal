"""
Synthetic message generator for Redd Lbal.

WHY: there is no public dataset of Moroccan scam SMS/WhatsApp messages.
So we encode what is *documented* (DGSSI, Ministry of Justice, NARSA,
Maroc Telecom, Bank Al-Maghrib alerts and press reports, 2025-2026) as
templates, and generate many variations (spelling, script, code-switching,
amounts, links). Every template has an id so we can hold out whole
templates for testing (= new wording the model never saw).

Template syntax:  [a|b|c] -> random choice (empty choice allowed: [a|])
                  {slot}  -> filled by SLOTS below

IMPORTANT: this is *seed* data. Replace/extend it with:
  - VISH-DARIJA-TTS text (zenodo.org/records/20039126) - scammer turns
  - real messages your team collects (data/real_messages.csv) -> TEST ONLY
"""
import random
import re

# ------------------------------------------------------------------ slot values
BANKS = ["CIH BANK", "CIH Bank", "Attijariwafa bank", "Attijariwafa", "Banque Populaire", "Chaabi Bank",
         "Bank of Africa", "BMCE Bank", "BMCI", "Crédit du Maroc", "Saham Bank", "Al Barid Bank",
         "CFG Bank", "Crédit Agricole du Maroc"]
BANKS_SHORT = ["CIH", "Attijari", "Chaabi", "BMCE", "Al Barid Bank", "Saham", "BMCI", "CDM"]
BANKS_AR = ["التجاري وفا بنك", "البنك الشعبي", "القرض العقاري والسياحي", "بنك أفريقيا", "بريد بنك",
            "مصرف المغرب", "القرض الفلاحي", "سي آي إتش بنك", "الشعبي", "صحام بنك"]
CARRIERS = ["Barid Al-Maghrib", "AMANA", "Amana Express", "Poste Maroc", "DHL", "Aramex", "CTM Messagerie"]
CARRIERS_AR = ["بريد المغرب", "أمانة", "البريد", "الشركة الوطنية للبريد", "أرامكس"]
TELCOS = ["Maroc Telecom", "IAM", "inwi", "Orange", "Orange Maroc"]
TELCOS_AR = ["اتصالات المغرب", "إنوي", "أورنج", "ماروك تيليكوم"]
NAMES = ["Youssef", "Fatima", "Khadija", "Mohamed", "Hamza", "Salma", "Imane", "Ayoub", "Omar", "Zineb",
         "Nadia", "Rachid", "Hicham", "Karim", "Meryem", "Sara", "Yassine", "Mehdi", "Soukaina", "Anas",
         "Hajar", "Othmane", "Ilyas", "Amine", "Houda", "Reda", "Samir", "Latifa", "Nabil", "Ghizlane"]
FAMILY_LAT = ["mama", "mami", "baba", "bba", "khouya", "khoya", "khti", "3emti", "khalti", "3ammi", "khali",
              "a l7aja", "a l7aj", "lalla", "a benti", "a wlidi"]
FAMILY_AR = ["ماما", "مامي", "بابا", "خويا", "ختي", "عمتي", "خالتي", "عمي", "خالي", "الحاجة", "الحاج", "وليدي", "بنتي"]
FAMILY_FR = ["maman", "papa", "tata", "tonton", "ma soeur", "mon frère", "mamie"]
MONEY = ["Wafacash", "Cash Plus", "Western Union", "MoneyGram", "Damane Cash", "Barid Cash", "CIH Mobile",
         "virement", "Jibi", "Chaabi Cash"]
MONEY_AR = ["وفاكاش", "كاش بلوس", "ويسترن يونيون", "البريد كاش", "داماني كاش", "تحويل بنكي"]
COUNTRIES_FR = ["Espagne", "Canada", "Italie", "Allemagne", "France", "Qatar", "Belgique", "Pays-Bas", "Arabie saoudite", "Émirats"]
COUNTRIES_LAT = ["sbanya", "Canada", "italia", "lalmanya", "fransa", "Qatar", "belgique", "holanda", "Dubai"]
COUNTRIES_AR = ["إسبانيا", "كندا", "إيطاليا", "ألمانيا", "فرنسا", "قطر", "بلجيكا", "الإمارات", "السعودية"]
CITIES = ["Casablanca", "Rabat", "Fès", "Marrakech", "Tanger", "Oujda", "Berkane", "Nador", "Agadir", "Meknès",
          "Kénitra", "Tétouan", "Salé", "Safi", "El Jadida", "Beni Mellal", "Taza", "Laâyoune"]
CITIES_AR = ["الدار البيضاء", "الرباط", "فاس", "مراكش", "طنجة", "وجدة", "بركان", "الناظور", "أكادير", "مكناس", "القنيطرة", "تطوان"]
MERCHANTS = ["MARJANE", "Marjane", "Carrefour", "BIM", "Label'Vie", "Acima", "Jumia", "Kitea", "Decathlon",
             "Afriquia", "Zara", "LC Waikiki", "Electroplanet", "Bricoma"]
ITEMS = ["la télé", "tilifoun", "l pc", "tomobil", "lmotor", "frigo", "la machine", "canapé", "iPhone", "PS5"]
ITEMS_AR = ["الطوموبيل", "التيليفون", "التلفزة", "الموطور", "الفريجيدير", "البيسي", "الماكينة"]
DAYS_LAT = ["tnin", "tlat", "larb3", "lkhmis", "jem3a", "sebt", "l7ed"]
DAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

SUS_TLDS = ["top", "xyz", "icu", "cfd", "sbs", "live", "click", "shop", "online", "site", "club", "vip", "buzz",
            "rest", "cyou", "bond", "win", "info", "cc", "pw", "link", "work", "today", "store", "life", "world",
            "space", "website", "lol", "mom", "quest"]
GEN_TLDS = ["com", "net", "org", "co", "me"]
SHORTENERS = ["bit.ly", "cutt.ly", "tinyurl.com", "rb.gy", "t.ly", "is.gd", "s.id", "shorturl.at", "tiny.cc", "v.gd"]
FREEHOST = ["web.app", "firebaseapp.com", "netlify.app", "vercel.app", "pages.dev", "github.io", "weebly.com",
            "wixsite.com", "blogspot.com", "000webhostapp.com", "glitch.me", "workers.dev", "onrender.com"]

BRAND_WORDS = {
    "traffic_fine": ["justice", "amendes", "amende", "amendes-maroc", "narsa", "radar", "infractions", "pv-maroc",
                     "mahakim", "tgr", "gov-ma", "e-amende", "contravention", "moukhalafa", "justice-ma", "radar-ma"],
    "bank_phishing": ["cih", "cihbank", "attijari", "attijariwafa", "awb", "chaabi", "bcp", "gbp", "bmce", "boa",
                      "bankofafrica", "albarid", "albaridbank", "sahambank", "saham", "bmci", "cdm", "bkam",
                      "attijarinet", "chaabinet", "cihnet", "banque-populaire"],
    "parcel": ["barid", "poste", "poste-ma", "amana", "colis", "livraison", "suivi", "tracking", "dhl", "aramex",
               "baridmaroc", "amana-ma"],
    "telecom_prize": ["iam", "maroctelecom", "inwi", "orange", "points-iam", "cadeau", "bonus", "recharge", "0661"],
    "gov_aid": ["asd", "asd-maroc", "daam", "daam-sakane", "rsu", "cnss", "amo", "dgi", "impots", "tax-ma", "minha",
                "aide-sociale", "da3m", "cnops"],
    "utility": ["lydec", "onee", "redal", "amendis", "facture", "one-ma"],
    "lottery": ["marjane", "omra", "hajj", "fifa2030", "can2025", "tickets", "cadeau", "gagnant", "carrefour", "bim"],
    "marketplace": ["avito", "avito-ma", "paiement", "livraison", "pay", "securepay"],
    "account": ["whatsapp", "netflix", "google", "facebook", "instagram", "meta", "apple"],
    "investment": ["crypto", "invest", "trading", "bitcoin", "forex", "binance"],
    "job": ["jobs", "recrutement", "emploi", "work", "visa"],
}
DEFAULT_WORDS = ["secure", "verify", "login", "update", "support", "service", "online", "client"]
SUFFIXES = ["", "-ma", "-maroc", "-secure", "-securite", "-verif", "-verification", "-online", "-paiement",
            "-pay", "-login", "-client", "-service", "-update", "-info", "-officiel", "-gov", "-2026", "ma",
            "-suivi", "-cadeau", "-confirm"]
PATHS = ["", "", "/", "/pay", "/paiement", "/login", "/verify", "/secure", "/suivi", "/v/{n}", "/?id={n}",
         "/ma/", "/dossier/{n}", "/index.php", "/{r}", "/fr/", "/ar/", "/confirm"]


def _rand_code(rng, n=6):
    return "".join(rng.choice("abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(n))


def scam_link(rng, campaign):
    words = BRAND_WORDS.get(campaign, DEFAULT_WORDS)
    w = rng.choice(words)
    kind = rng.random()
    path = rng.choice(PATHS).replace("{n}", str(rng.randint(1000, 99999))).replace("{r}", _rand_code(rng, 5))
    if kind < 0.14:   # URL shortener
        return f"{rng.choice(['https://', 'http://', ''])}{rng.choice(SHORTENERS)}/{rng.choice([w + '-', ''])}{_rand_code(rng, rng.randint(4, 7))}"
    if kind < 0.26:   # free hosting
        return f"{rng.choice(['https://', ''])}{w}{rng.choice(SUFFIXES)}.{rng.choice(FREEHOST)}{path}"
    if kind < 0.31:   # raw IP
        return f"http://{rng.randint(5, 220)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}/{w}{path}"
    if kind < 0.40:   # official-looking subdomain of attacker domain
        lure = rng.choice(["gov.ma", "ma", "justice.gov.ma", "cihbank.ma", "poste.ma", "iam.ma", "cnss.ma", "barid.ma"])
        return f"{rng.choice(['https://', 'http://', ''])}{lure}.{rng.choice(['secure', 'verify', 'portail', 'service', 'login'])}-{_rand_code(rng, 4).lower()}.{rng.choice(SUS_TLDS + GEN_TLDS)}{path}"
    tld = rng.choice(SUS_TLDS) if rng.random() < 0.62 else rng.choice(GEN_TLDS)
    if rng.random() < 0.25:
        w = w + rng.choice(["-", ""]) + rng.choice(words + DEFAULT_WORDS)
    return f"{rng.choice(['https://', 'http://', '', '', 'www.', 'https://www.'])}{w}{rng.choice(SUFFIXES)}.{tld}{path}"


def chat_link(rng):
    r = rng.random()
    if r < 0.45:
        cc = rng.choice(["44", "34", "1", "33", "39", "49", "971", "966", "225", "234", "63"])
        return f"wa.me/{cc}{rng.randint(10**8, 10**9)}"
    if r < 0.75:
        return f"t.me/{rng.choice(['invest', 'crypto', 'jobs', 'khdma', 'trading', 'vip', 'rbe7'])}_{_rand_code(rng, 5).lower()}"
    return scam_link(rng, "investment")


OFFICIAL_LINKS = {
    "bank": ["www.cihbank.ma", "https://www.attijariwafabank.com", "www.bankofafrica.ma", "www.groupebcp.com",
             "www.albaridbank.ma", "https://www.sahambank.com", "www.bmci.ma"],
    "telco": ["www.iam.ma", "https://www.inwi.ma", "www.orange.ma"],
    "post": ["www.poste.ma", "bam-tracking.barid.ma", "www.barid.ma"],
    "gov": ["www.rsu.ma", "www.asd.ma", "www.cnss.ma", "amendes.justice.gov.ma", "www.tax.gov.ma",
            "infractionsroutieres.narsa.gov.ma", "www.tgr.gov.ma", "www.narsa.ma"],
    "fine": ["amendes.justice.gov.ma", "infractionsroutieres.narsa.gov.ma", "www.tgr.gov.ma"],
    "merchant": ["www.marjane.ma", "www.jumia.ma", "www.avito.ma", "www.decathlon.ma", "www.kitea.com"],
    "misc": ["meet.google.com/{r}", "youtube.com/watch?v={r}", "www.youtube.com/@ENIAD", "drive.google.com/file/d/{r}",
             "www.instagram.com/p/{r}", "www.facebook.com/groups/eniad", "maps.app.goo.gl/{r}", "www.hespress.com",
             "fr.le360.ma", "www.ump.ma", "github.com/{r}"],
}


BENIGN_WORDS = ["dar", "atlas", "riad", "zitoun", "nakhil", "chez-ali", "la-petite-epicerie", "academy", "club-sportif",
                "jam3iya-amal", "cafe-de-france", "restaurant-assiya", "hotel-atlas", "berkane-events", "eniad-club",
                "tech-blog", "my-portfolio", "recettes-de-lalla", "studio-photo", "auto-ecole-nour", "pharmacie-alamal"]


def benign_link(rng):
    w = rng.choice(BENIGN_WORDS) + rng.choice(["", "-" + rng.choice(CITIES).lower().replace("è", "e").replace("â", "a").replace("é", "e")])
    return f"{rng.choice(['https://', 'https://www.', 'www.', ''])}{w}.{rng.choice(['com', 'ma', 'net', 'org', 'com', 'ma'])}{rng.choice(['', '/', '/menu', '/fr', '/inscription', '/blog/' + _rand_code(rng, 6).lower()])}"


def official_link(rng, kind):
    return rng.choice(OFFICIAL_LINKS[kind]).replace("{r}", _rand_code(rng, rng.randint(6, 11)))


def amount(rng, lo, hi, step=1):
    v = rng.randrange(lo, hi, step)
    return f"{v:,}".replace(",", rng.choice([" ", "", "."])) if v >= 1000 else str(v)


def dh(rng):
    return rng.choice(["DH", "DH", "dh", "MAD", "Dhs", "dhs", "DHS"])


def date(rng):
    d, m = rng.randint(1, 28), rng.randint(1, 12)
    return rng.choice([f"{d:02d}/{m:02d}/2026", f"{d:02d}/{m:02d}", f"{d}/{m}"])


SLOTS = {
    "link": lambda r, c: scam_link(r, c),
    "short_link": lambda r, c: f"{r.choice(['https://', ''])}{r.choice(SHORTENERS)}/{_rand_code(r, 6)}",
    "chat_link": lambda r, c: chat_link(r),
    "amount_fine": lambda r, c: str(r.choice([150, 200, 300, 400, 500, 700, 750, 900, 1000, 1200, 1500])),
    "amount_small": lambda r, c: r.choice(["7", "9,90", "10", "12,50", "14", "15", "19", "19,99", "20", "25", "29"]),
    "amount_small2": lambda r, c: str(r.choice([20, 30, 50, 100, 150, 200, 300])),
    "amount_small3": lambda r, c: str(r.choice([100, 150, 200, 300, 500, 1000])),
    "amount_mid": lambda r, c: str(r.choice([300, 500, 800, 1000, 1500, 2000, 2500, 3000, 4000, 5000])),
    "amount_big": lambda r, c: amount(r, 1000, 80000, 50),
    "amount_bill": lambda r, c: f"{r.randint(80, 1200)},{r.randint(0, 99):02d}",
    "amount_job": lambda r, c: str(r.choice([500, 800, 1000, 1500, 1800, 2000, 2500, 3000, 5000])),
    "amount_task": lambda r, c: str(r.choice([200, 300, 400, 500, 600, 800, 1000])),
    "amount_salary": lambda r, c: str(r.choice([1200, 1500, 1800, 2000, 2500, 3000, 15000, 20000, 25000])),
    "amount_tx": lambda r, c: f"{r.randint(15, 9000)},{r.choice(['00', '50', str(r.randint(10, 99))])}",
    "amount_bal": lambda r, c: f"{r.randint(100, 50000)},{r.randint(10, 99)}",
    "cur": lambda r, c: r.choice(["€", "euros", "DH", "$"]),
    "dh": lambda r, c: dh(r),
    "hours": lambda r, c: str(r.choice([12, 24, 24, 48, 48, 72])),
    "days": lambda r, c: str(r.choice([3, 5, 7, 10, 14])),
    "months": lambda r, c: str(r.choice([3, 6, 9, 12])),
    "years": lambda r, c: str(r.choice([10, 15, 20, 25, 30])),
    "pct": lambda r, c: str(r.choice([5, 10, 15, 20, 30, 40, 50])),
    "go": lambda r, c: str(r.choice([1, 2, 5, 10, 15, 20])),
    "date": lambda r, c: date(r),
    "time": lambda r, c: f"{r.randint(7, 21):02d}:{r.choice(['00', '15', '30', '45', str(r.randint(10, 59))])}",
    "ref": lambda r, c: r.choice([f"{r.randint(100, 99999)}/2026", f"2026-{r.randint(1000, 99999)}", f"{r.randint(10000, 999999)}"]),
    "n5": lambda r, c: str(r.randint(10000, 99999)),
    "n1": lambda r, c: str(r.randint(1, 12)),
    "n2": lambda r, c: str(r.randint(1, 80)),
    "n3": lambda r, c: str(r.randint(100, 999)),
    "otp": lambda r, c: str(r.randint(1000, 999999)).zfill(r.choice([4, 6])),
    "otp3": lambda r, c: str(r.randint(100, 999)),
    "otp4": lambda r, c: str(r.randint(1000, 9999)),
    "points": lambda r, c: r.choice(["12 450", "8 900", "18 700", "25 000", "5600", "10 300", "31 250"]),
    "tracking": lambda r, c: f"{r.choice(['CB', 'RR', 'EE', 'CP', 'LX'])}{r.randint(100000000, 999999999)}MA",
    "order": lambda r, c: str(r.randint(100000, 999999)),
    "h1": lambda r, c: str(r.choice([9, 10, 11, 14])),
    "h2": lambda r, c: str(r.choice([13, 16, 18, 20])),
    "bank": lambda r, c: r.choice(BANKS),
    "bank_short": lambda r, c: r.choice(BANKS_SHORT),
    "bank_ar": lambda r, c: r.choice(BANKS_AR),
    "carrier": lambda r, c: r.choice(CARRIERS),
    "carrier_ar": lambda r, c: r.choice(CARRIERS_AR),
    "telco": lambda r, c: r.choice(TELCOS),
    "telco_ar": lambda r, c: r.choice(TELCOS_AR),
    "name": lambda r, c: r.choice(NAMES),
    "family_lat": lambda r, c: r.choice(FAMILY_LAT),
    "family_ar": lambda r, c: r.choice(FAMILY_AR),
    "family_fr": lambda r, c: r.choice(FAMILY_FR),
    "money_service": lambda r, c: r.choice(MONEY),
    "money_service_ar": lambda r, c: r.choice(MONEY_AR),
    "country_fr": lambda r, c: r.choice(COUNTRIES_FR),
    "country_lat": lambda r, c: r.choice(COUNTRIES_LAT),
    "country_ar": lambda r, c: r.choice(COUNTRIES_AR),
    "city": lambda r, c: r.choice(CITIES),
    "city_ar": lambda r, c: r.choice(CITIES_AR),
    "merchant": lambda r, c: r.choice(MERCHANTS),
    "item": lambda r, c: r.choice(ITEMS),
    "item_ar": lambda r, c: r.choice(ITEMS_AR),
    "day_lat": lambda r, c: r.choice(DAYS_LAT),
    "day_ar": lambda r, c: r.choice(DAYS_AR),
    "brand_any": lambda r, c: r.choice(BANKS_SHORT + ["WhatsApp", "Google", "Facebook", "Instagram", "Jumia", "Glovo", "inwi", "IAM", "Orange", "Avito", "CNSS"]),
    "official_bank_link": lambda r, c: official_link(r, "bank"),
    "official_telco_link": lambda r, c: official_link(r, "telco"),
    "official_post_link": lambda r, c: official_link(r, "post"),
    "official_gov_link": lambda r, c: official_link(r, "gov"),
    "official_fine_link": lambda r, c: official_link(r, "fine"),
    "official_merchant_link": lambda r, c: official_link(r, "merchant"),
    "misc_link": lambda r, c: official_link(r, "misc"),
    "benign_link": lambda r, c: benign_link(r),
    "thing_lat": lambda r, c: r.choice(["l3ers", "lwalida", "la carte grise", "tomobil", "dar", "l'examen", "lbaby", "lmatch", "la facture"]),
    "thing_ar": lambda r, c: r.choice(["العرس", "الدار", "الطوموبيل", "الامتحان", "الدري الصغير", "الفاتورة"]),
    "thing_fr": lambda r, c: r.choice(["la voiture", "l'appartement", "la facture", "l'examen", "la fête", "ton chat"]),
    "thing_en": lambda r, c: r.choice(["the car", "the flat", "the cake", "the trip"]),
    "person_lat": lambda r, c: r.choice(["plombier", "trisian", "lmikanisyan", "tbib", "l prof", "sa7bek", "l'avocat", "moul taxi", "l3attar"]),
    "person_ar": lambda r, c: r.choice(["السباك", "الطبيب", "الأستاذ", "الميكانيسيان", "صاحبك", "المحامي"]),
    "person_fr": lambda r, c: r.choice(["ton plombier", "ton médecin", "l'électricien", "ton prof", "l'avocat"]),
    "person_en": lambda r, c: r.choice(["the plumber", "your doctor", "the teacher", "the mechanic"]),
    "ma_phone": lambda r, c: r.choice(["05", "06", "07"]) + "".join(r.choice(" 0123456789") if i in (2, 5, 8) and r.random() < 0.5 else r.choice("0123456789") for i in range(8)),
}

# ------------------------------------------------------------------ SCAM templates
# (campaign, lang, template)
SCAM_TEMPLATES = [
# --- traffic fines (DGSSI critical alert Apr 2026; Ministry of Justice alerts Apr & Jun 2026)
("traffic_fine", "fr", "[Royaume du Maroc|Ministère de la Justice|NARSA|Avis officiel|Rappel] : [vous avez|il existe à votre nom] une amende [impayée|non réglée|en attente] de {amount_fine} {dh}. [Réglez-la|Payez-la|Veuillez la régler] [avant le {date}|sous {hours}h|ce soir] pour éviter [des poursuites|une majoration|la saisie de votre compte|des pénalités] : {link}"),
("traffic_fine", "fr", "Avis d'exécution [administrative|] n°{ref} : une infraction [routière|au code de la route] a été [enregistrée|constatée] par [radar fixe|caméra de surveillance|vidéosurveillance]. [Consultez la vidéo et réglez|Payez] [votre amende|le montant de {amount_fine} {dh}] [sous {hours}h|avant le {date}] : {link}"),
("traffic_fine", "fr", "[URGENT|DERNIER RAPPEL|NOTIFICATION] : votre dossier d'infraction n°{ref} sera transmis au tribunal [sous {hours}h|demain]. [Évitez les frais supplémentaires|Régularisez votre situation] [ici|en ligne] : {link}"),
("traffic_fine", "fr", "Excès de vitesse [détecté|constaté] le {date} [sur l'autoroute|à {city}]. Montant de l'amende : {amount_fine} {dh}. [Payez en ligne|Paiement sécurisé] [avant majoration|] : {link}"),
("traffic_fine", "msa", "[وزارة العدل|المملكة المغربية|الوكالة الوطنية للسلامة الطرقية|إشعار رسمي]: [لديكم|لديك] [مخالفة مرورية|غرامة مرورية|مخالفة سير] غير [مؤداة|مسددة] [بقيمة {amount_fine} درهم|]. [يرجى|المرجو] [الأداء|التسديد] [قبل {date}|خلال {hours} ساعة|فورا] [لتفادي المتابعة القضائية|لتجنب الحجز على حسابكم|لتفادي الغرامات الإضافية]: {link}"),
("traffic_fine", "msa", "إشعار بالتنفيذ الإداري رقم {ref}: تم [تسجيل|رصد] مخالفة [بواسطة الرادار|بكاميرا المراقبة]. [للاطلاع على الفيديو|للاطلاع على التفاصيل] [وأداء الغرامة|والأداء] [اضغط على الرابط|عبر الرابط]: {link}"),
("traffic_fine", "msa", "[تنبيه|آخر إشعار]: سيتم إحالة ملف مخالفتكم رقم {ref} على المحكمة [خلال {hours} ساعة|غدا] في حالة عدم الأداء. [ادفع الآن|سدد الآن]: {link}"),
("traffic_fine", "dar_ar", "[السلام عليكم،|سلام،|] عندك [غرامة|مخالفة|مخالفة ديال الرادار] [ما خلصتيهاش|مازال ما تخلصاتش] [ديال {amount_fine} درهم|]، [خلصها|خلص] [دابا|اليوم|قبل {hours} ساعة] [باش ما تزادش عليك|ولا غادي يتحبس ليك الحساب|ولا غادي تمشي للمحكمة]: {link}"),
("traffic_fine", "dar_ar", "[تصوراتي|شدك] الرادار [ف{city_ar}|فالطريق السيار]، [الغرامة|الخلاص] {amount_fine} درهم، [خلص من هاد الرابط|دخل هنا باش تخلص] {link}"),
("traffic_fine", "dar_lat", "[salam,|slm|] 3ndk [mokhalafa|amende|ghrama] [dyal radar|dyal sir|] [ma khlsthach|mazal ma tkhlsat], [khlsha|khlles] [daba|lyoum|9bel {hours} sa3a] [wla ghadi tdobel|wla ghadi ytbloka lik l compte|bach matmchich l m7kama]: {link}"),
("traffic_fine", "en", "[Kingdom of Morocco|Ministry of Justice|Traffic Police]: you have an unpaid [traffic fine|speeding ticket] of {amount_fine} MAD. Pay [within {hours} hours|before {date}] to avoid [legal action|a penalty|account seizure]: {link}"),
# --- bank phishing with link (Bank Al-Maghrib / Hespress 2025-2026)
("bank_phishing", "fr", "{bank} : [votre carte|votre compte|votre accès en ligne] [a été|est] [suspendu|bloqué|temporairement désactivé] [suite à|en raison d'] [une activité suspecte|une tentative de connexion inhabituelle|un défaut de mise à jour]. [Réactivez-le|Vérifiez votre identité|Mettez à jour vos informations] [ici|via ce lien|immédiatement] : {link}"),
("bank_phishing", "fr", "{bank} : une [opération|transaction|tentative de paiement] de {amount_big} {dh} [a été détectée|est en cours] sur votre compte. Si ce n'est pas vous, [annulez-la|bloquez-la|contestez-la] [immédiatement|maintenant] : {link}"),
("bank_phishing", "fr", "[Cher client|Chère cliente], [conformément à la nouvelle réglementation de Bank Al-Maghrib|pour des raisons de sécurité], [vous devez|merci de] [confirmer|mettre à jour] vos [données|informations] bancaires [avant le {date}|sous {hours}h] [sinon votre compte sera clôturé|pour éviter la suspension] : {link}"),
("bank_phishing", "fr", "[Alerte sécurité|Sécurité] {bank} : nouvel appareil connecté à votre compte. [Ce n'était pas vous ?|Pas vous ?] [Sécurisez votre compte|Cliquez ici] : {link}"),
("bank_phishing", "msa", "{bank_ar}: تم [توقيف|تعليق|تجميد] [بطاقتكم البنكية|حسابكم] [بسبب نشاط مشبوه|لعدم تحديث المعطيات|لدواعي أمنية]. [المرجو|يرجى] [تحديث بياناتكم|تأكيد هويتكم|إعادة التفعيل] عبر الرابط [التالي|] [خلال {hours} ساعة|قبل {date}]: {link}"),
("bank_phishing", "msa", "[تنبيه أمني|إشعار]: تم رصد عملية [سحب|أداء] بقيمة {amount_big} درهم من حسابكم. إذا لم تقوموا بهذه العملية [قوموا بإلغائها|اضغطوا هنا] [فورا|الآن]: {link}"),
("bank_phishing", "dar_ar", "{bank_ar}: [الكارط|البطاقة] ديالك [تبلوكات|توقفات] [حيت كاينة شي عملية ماشي عادية|بسبب عملية مشبوهة|]، [دخل|كليكي] [للرابط|هنا] باش [تفعلها|ترجعها|تأكد المعلومات ديالك] [دابا|قبل {hours} ساعة]: {link}"),
("bank_phishing", "dar_ar", "[سلام،|] الحساب ديالك ف{bank_ar} [غادي يتسد|تبلوكا] إلا ما [حدثتيش|أكدتيش] المعلومات ديالك [اليوم|دابا]: {link}"),
("bank_phishing", "dar_lat", "{bank}: la carte dyalk [tbloquat|t7bsat|tsuspendat] [7it kayn wa7d l'opération machi normal|], [dkhel|clicki 3la] had lien bach [t activiha|tconfirmi les infos dyalk|trj3ha] [daba|9bel {hours}h]: {link}"),
("bank_phishing", "dar_lat", "[slm|salam], l compte dyalk f {bank} [ghadi ytbloka|tbloqua] ila [ma confirmitich|ma mettitich à jour] les informations dyalk [lyoum|daba]: {link}"),
("bank_phishing", "en", "{bank}: your [card|account|online banking access] has been [suspended|locked|restricted] due to [suspicious activity|an unusual sign-in]. [Verify your identity|Reactivate it|Update your details] [now|within {hours} hours]: {link}"),
("bank_phishing", "mix", "{bank}: [salam,|] l compte dyalk [t bloqua|t suspenda] [à cause d'une activité suspecte|], [merci de|khassk] [confirmer|t confirmer] [vos|les] informations [dyalk|] [ici|f had lien]: {link}"),
# --- fake bank agent asking for codes (no link)
("bank_otp", "dar_lat", "[salam|slm|allo], [m3ak|ana] {name} [mn|dyal] [service client|la sécurité|l'agence] dyal {bank}. [kayn|kayna] [wa7d l'opération|transaction] [machi normal|mashkouk fiha] f [la carte|l compte] dyalk. [ghadi yjik|daba ghayjik|wsslek] [wa7d l code|code] f sms, [3tih lia|sifto lia|9rah lia] bach [nbloquiwha|nlghiwha|n7miw l compte dyalk]"),
("bank_otp", "dar_lat", "[khouya|a lalla|a sidi], ana mn {bank_short}, [3tini|sift lia] [les 3 ar9am li mor la carte|l code secret|l code li jak f sms|numéro dyal la carte w date d'expiration] bach [n7bes l prélèvement|nrje3 lik lflous|n activi lik l compte]"),
("bank_otp", "dar_ar", "[السلام،|سلام،|] [أنا|معاك] {name} من [خدمة الزبناء|المصلحة الأمنية] ديال {bank_ar}. [كاينة|كاين] عملية [مشبوهة|ماشي عادية] فالحساب ديالك، [غيوصلك|دابا غيجيك] [كود|رمز] فالميساج، [عطيه ليا|صيفطو ليا|قراه ليا] باش [نوقفوها|نلغيوها|نحميو الحساب ديالك]"),
("bank_otp", "dar_ar", "[عافاك|من فضلك] [عطيني|صيفط ليا] [الأرقام اللي مورا البطاقة|الكود السري ديال الكارط|الرمز اللي وصلك] باش [نحبسو العملية|نرجعو ليك الفلوس|نفعلو ليك الحساب]"),
("bank_otp", "fr", "[Bonjour,|Allô,] [ici|je suis] {name} du [service sécurité|service client|service fraude] {bank}. [Pour bloquer|Afin d'annuler] [la transaction frauduleuse|l'opération suspecte], [merci de me communiquer|veuillez me transmettre|envoyez-moi] [le code reçu par SMS|votre code de validation|les 3 chiffres au dos de votre carte|votre numéro de carte et la date d'expiration]"),
("bank_otp", "msa", "[مرحبا،|] نحن [المصلحة الأمنية|مصلحة الزبناء] لدى {bank_ar}. [لحماية حسابكم|لإلغاء العملية المشبوهة] [يرجى|المرجو] [إرسال|تزويدنا ب] [رمز التحقق الذي توصلتم به|الرمز السري للبطاقة|الأرقام الثلاثة الموجودة خلف البطاقة]"),
("bank_otp", "en", "[Hello,|] this is {name} from {bank} [security|fraud] team. To [block|cancel] the [suspicious|fraudulent] transaction please [send me|share] [the code you just received|your card number and CVV|your PIN]"),
# --- parcels (Barid Al-Maghrib / Amana / customs)
("parcel", "fr", "{carrier} : votre colis [n°{ref}|] [est en attente|n'a pas pu être livré|est bloqué] [en raison d'une adresse incomplète|suite à des frais impayés|au centre de tri]. [Réglez|Payez] [{amount_small} {dh}|les frais de livraison|les frais de douane] [pour reprogrammer la livraison|pour le recevoir|avant {hours}h] : {link}"),
("parcel", "fr", "[Livraison|Colis] : [dernière tentative|votre livreur n'a pas pu vous joindre]. [Confirmez votre adresse|Choisissez un créneau] et [réglez|payez] {amount_small} {dh} [ici|] : {link}"),
("parcel", "fr", "[Douane|{carrier}] : un colis [en provenance de|de] {country_fr} [vous attend|est retenu]. Frais [de dédouanement|de douane] : {amount_small} {dh}. [Payez en ligne|Paiement] : {link}"),
("parcel", "msa", "{carrier_ar}: [طردكم|شحنتكم] [في انتظار|متوقفة بسبب] [أداء رسوم|رسوم] [التوصيل|الجمارك|الشحن] ({amount_small} درهم). [يرجى|المرجو] الأداء [قبل {date}|خلال {hours} ساعة] [وإلا سيتم إرجاع الطرد|لتفادي الإرجاع]: {link}"),
("parcel", "msa", "[لم نتمكن|تعذر علينا] من توصيل طردكم [بسبب عنوان غير مكتمل|]. [يرجى تأكيد العنوان|المرجو تحديث العنوان] [وأداء {amount_small} درهم|]: {link}"),
("parcel", "dar_ar", "[عندك|كاين ليك] [كوليس|طرد|كولي] [ف{carrier_ar}|] [ما قدرناش نوصلوه ليك|واقف فالديوانة|محبوس]، [أكد|صحح] العنوان ديالك [وخلص|و خلص] {amount_small} درهم [ديال التوصيل|ديال الديوانة] [هنا|من هاد الرابط]: {link}"),
("parcel", "dar_lat", "[salam,|] 3ndk [colis|koli] [f {carrier}|] [ma9dernach nwslouh lik|wa9ef f diwana], [confirmi|akked] l'adresse dyalk w [khlles|khlss] {amount_small}dh [dyal livraison|dyal diwana]: {link}"),
("parcel", "en", "{carrier}: your parcel [is on hold|could not be delivered] [due to an incomplete address|due to unpaid customs fees]. Pay {amount_small} MAD [to reschedule delivery|to release it] [within {hours} hours|today]: {link}"),
# --- telecom prizes (Maroc Telecom alert on fake 0661 offers, Apr 2026)
("telecom_prize", "fr", "{telco} : [félicitations|bonne nouvelle] ! [Vos {points} points fidélité expirent aujourd'hui|Vous avez gagné un smartphone|Vous avez gagné {amount_big} {dh} de recharge|Vous avez gagné 100 Go]. [Échangez-les|Récupérez votre cadeau|Profitez-en] [ici|maintenant] : {link}"),
("telecom_prize", "fr", "{telco} : obtenez [gratuitement|sans frais] un numéro [0661|en or|VIP] [en remplissant le formulaire|en confirmant vos informations] : {link}"),
("telecom_prize", "fr", "[Votre solde bonus|Votre bonus] {telco} de {amount_big} {dh} [expire|sera perdu] [ce soir|dans {hours}h]. [Activez-le|Réclamez-le] : {link}"),
("telecom_prize", "dar_ar", "مبروك! [ربحتي|تختاريتي باش تربح] [تيليفون جديد|{amount_big} درهم ديال التعبئة|نمرة 0661 فابور|100 جيغا] من {telco_ar}. [دخل|كليكي] [هنا|على الرابط] [وأكد المعلومات ديالك|ودخل المعلومات ديال الكارط] [قبل ما يسالي العرض|اليوم]: {link}"),
("telecom_prize", "dar_ar", "{telco_ar}: النقط ديالك ({points} نقطة) غادي [يتمحاو|يمشيو] [الليلة|اليوم]، [بدلهم|حولهم] [بهدية|بتيليفون] [هنا|من هاد الرابط]: {link}"),
("telecom_prize", "dar_lat", "{telco}: [mabrouk|mbrok]! rbe7ti [tilifoun jdid|{points} points|100 Go|recharge dyal {amount_big}dh] [b blash|fabor]. [clicki|dkhel] 3la [had lien|lien] w [confirmi les infos dyalk|dkhel numéro dyal la carte] [bach t activih|9bel ma ysali l3ard]: {link}"),
("telecom_prize", "msa", "{telco_ar}: تهانينا! [لقد ربحت|فزت ب] [هاتفا ذكيا|{amount_big} درهم رصيد|رقما مميزا مجانا]. [للحصول على الجائزة|لتفعيل الهدية] [يرجى تأكيد بياناتكم|أدخل معلوماتك] عبر الرابط: {link}"),
("telecom_prize", "en", "{telco}: congratulations! You've won [a new smartphone|{amount_big} MAD credit|a free 0661 number]. Claim your gift [here|now] before it expires: {link}"),
# --- government aid / refunds (ASD, Daam Sakane, RSU, CNSS/AMO, DGI)
("gov_aid", "msa", "[الدعم الاجتماعي المباشر|السجل الاجتماعي الموحد|برنامج دعم السكن|الصندوق الوطني للضمان الاجتماعي]: [ملفكم غير مكتمل|تم قبول طلبكم|لديكم مبلغ {amount_big} درهم في انتظار التحويل]. [المرجو|يرجى] [تحيين|تأكيد|إدخال] [المعطيات البنكية|رقم البطاقة البنكية|معلومات الحساب] [عبر الرابط|من خلال الرابط التالي] [قبل {date}|خلال {hours} ساعة] [لتفادي توقيف الدعم|لتوصلكم المنحة|]: {link}"),
("gov_aid", "msa", "[تهانينا|إشعار]: تم اختياركم للاستفادة من [منحة استثنائية|دعم مالي] قدره {amount_big} درهم. [سجلوا|أدخلوا] [رقم البطاقة الوطنية والبطاقة البنكية|معلوماتكم] هنا: {link}"),
("gov_aid", "dar_ar", "[خبار زوينة|مبروك]: [تقبل|تقبلات] [الطلب ديالك|الملف ديالك] ف[الدعم المباشر|دعم السكن|المنحة]، [غير|خاصك] [أكد|دخل] [الرقم ديال البطاقة البنكية|المعلومات ديال الحساب|الريب ديالك] باش [يتحول ليك المبلغ|توصلك الفلوس] [{amount_big} درهم|]: {link}"),
("gov_aid", "fr", "[CNSS|AMO|Aide Sociale Directe|DGI|Direction des Impôts] : [un remboursement|une aide] de {amount_big} {dh} [est en attente|vous a été attribuée]. [Pour le recevoir|Afin de le percevoir], [confirmez|renseignez] [votre RIB|vos coordonnées bancaires|votre numéro de carte] [ici|avant le {date}] : {link}"),
("gov_aid", "fr", "[Aide au logement|Daam Sakane] : votre dossier est validé ({amount_big} {dh}). [Confirmez vos coordonnées bancaires|Finalisez votre demande] [sous {hours}h|avant le {date}] : {link}"),
("gov_aid", "dar_lat", "[mbrok|mabrouk], t9bel [dossier|talab] dyalk f [da3m|l'aide] [dyal sakan|l mobachir], [dkhel|confirmi] [numéro dyal la carte|RIB dyalk] bach [twslek|ytransfera lik] {amount_big}dh: {link}"),
# --- family impersonation (new number + money; Le Matin Sept 2026)
("family", "dar_lat", "[salam|slm|cc] {family_lat}, [ana|hada] {name}, [hadi|hada] [nmra|numéro] jdida dyali, [tilifoun|portable] [l9dim|lqdim] [t3attal|tkhser|tsre9]. [sajliha 3afak|sajli had nmra|]"),
("family", "dar_lat", "{family_lat} [3afak|wlah ila] sift liya {amount_mid} dh [daba|daba daba|db] f {money_service}, [ana f mochkil|rani f wa7ed lmochkil|w9e3 lia chi haja], [ghadi nfhmek mn b3d|nchr7 lik mn b3d|nrj3hom lik ghda]. [matgoul l 7ta wa7ed|ma t3ayetch 3liya daba|]"),
("family", "dar_lat", "{family_lat}, [dir liya|sift liya] recharge dyal {amount_small2} dh [f had numéro|3afak], [tilifoun dyali ma fih sold|dharouri|]"),
("family", "dar_lat", "[a {family_lat}|{family_lat}] rani f [sbitar|lkoumissarya|l'aéroport|lmatar], [ma 3ndich lflous|t7bsat lia lbaliza], sift liya {amount_mid}dh [3la smiya dyal had sa7bi|f had rib] [3afak|daba]"),
("family", "dar_ar", "[سلام|السلام عليكم] {family_ar}، [أنا|هادا] {name}، هادي [نمرة|الرقم] [جديدة|الجديد] ديالي، [التيليفون|البورطابل] [القديم|] [تخسر|تسرق|طاح ليا]. [سجلها عافاك|سجل هاد النمرة|]"),
("family", "dar_ar", "{family_ar} عافاك صيفط ليا {amount_mid} درهم [دابا|دابا دابا] [ف{money_service_ar}|فهاد الحساب]، [راني فمشكل|وقع ليا مشكل]، [غادي نفهمك من بعد|نرجعهم ليك غدا]. [ما تقول لحتى واحد|ما تعيطش ليا دابا|]"),
("family", "dar_ar", "{family_ar} [ديري ليا|دير ليا|صيفط ليا] تعبئة ديال {amount_small2} درهم [فهاد الرقم|ضروري]، [التيليفون ديالي ما فيه صولد|]"),
("family", "fr", "[Salut|Coucou|Bonjour] {family_fr}, c'est {name}, [j'ai changé de numéro|voici mon nouveau numéro], [l'ancien est cassé|j'ai perdu mon téléphone]. [Enregistre-le stp|]"),
("family", "fr", "{family_fr} [tu peux|peux-tu] me [faire un virement|envoyer] de {amount_mid} {dh} [aujourd'hui|maintenant] [par {money_service}|] ? [Je t'expliquerai|C'est urgent|Je suis dans le pétrin], [ne dis rien à personne|ne m'appelle pas pour l'instant|]"),
# --- WhatsApp account takeover
("whatsapp_hijack", "dar_lat", "[salam|slm], [sme7 lia|smhli], [sifet|sifte|seft] lik [wa7d l code|code] [dyal 6 ar9am|dyal whatsapp|] [bl ghalat|bghalat|bla ma nqsed], [3afak|wlah ila] [3awd sifto|sifto] liya"),
("whatsapp_hijack", "dar_ar", "[سمح ليا|سمحي ليا]، صيفطت ليك [واحد الكود|الرمز] [ديال 6 أرقام|ديال الواتساب|] بالغلط، عافاك [صيفطو|عاود صيفطو] ليا"),
("whatsapp_hijack", "fr", "[Bonjour|Salut], [désolé,|] je vous ai envoyé un code [à 6 chiffres|de vérification|WhatsApp] par erreur, [pouvez-vous|tu peux] me le [renvoyer|transférer] [svp|stp] ?"),
("whatsapp_hijack", "en", "[Hi|Hello], sorry I [sent|accidentally sent] a [6-digit|verification|WhatsApp] code to your number by mistake, [can you|could you] [send|forward] it [back|to me] please?"),
("whatsapp_hijack", "msa", "عذرا، [أرسلت|لقد أرسلت] إليك رمز [التحقق|التأكيد] عن طريق الخطأ، [هل يمكنك|المرجو] [إعادة إرساله|إرساله] لي"),
# --- job scams (abroad with fees, task scams)
("job", "fr", "[Recrutement|Offre d'emploi|Urgent] : [cueillette de fraises|travail agricole|chantier|hôtellerie] en {country_fr}. [Contrat de {months} mois|Contrat légal], [visa garanti|logement offert], salaire {amount_salary} {cur}/mois. [Frais de dossier|Frais d'inscription] : {amount_job} {dh} [par {money_service}|à envoyer par {money_service}]. [Places limitées|Inscrivez-vous vite] !"),
("job", "fr", "Travail à domicile : gagnez {amount_task} {dh} par jour en [aimant des vidéos|notant des hôtels|regardant des pubs]. [Contactez-nous|Écrivez-nous] sur [WhatsApp|Telegram] : {chat_link}"),
("job", "dar_lat", "[khdma|5edma] f {country_lat}, [contrat w visa|visa w l'hébergement] [mdmonin|garanti], [salaire|khlass] {amount_salary} {cur}. [khass ghir|ghir] t sift {amount_job}dh [dyal dossier|dyal l'inscription] [f {money_service}|] [w passeport dyalk|]"),
("job", "dar_lat", "[bghiti|wach bghiti] [trbe7|dakhal] {amount_task}dh f nhar [mn dar|b telephone dyalk]? [ghir dir like l videos|ghir b jaimet]. [twasel m3ana|sift lina] f [whatsapp|telegram]: {chat_link}"),
("job", "dar_ar", "خدمة [ف{country_ar}|فالخارج] بعقد [وفيزا مضمونة|قانوني]، الخلصة {amount_salary} {cur}. [خاصك غير|غير] تصيفط {amount_job} درهم [ديال الملف|ديال التسجيل] [ف{money_service_ar}|]"),
("job", "dar_ar", "خدمة من الدار: [غادي تربح|ربح] {amount_task} درهم فالنهار [غير بالجيمات|غير بالبارطاج] [على الفيديوهات|]. [تواصل معانا|صيفط لينا] [فالواتساب|فتيليغرام]: {chat_link}"),
("job", "msa", "[مطلوب|فرصة عمل] [عمال|موظفين] للعمل في {country_ar} براتب {amount_salary} {cur}، [التأشيرة مضمونة|السكن مجاني]. [لحجز مكانك|للتسجيل] أرسل {amount_job} درهم [رسوم الملف|رسوم التسجيل] [عبر {money_service_ar}|]"),
("job", "en", "[Hiring now|Job offer]: [work from home|remote assistant], earn {amount_task} MAD per day [just liking videos|rating products]. [Message our HR|Contact us] on [WhatsApp|Telegram]: {chat_link}"),
# --- investment
("investment", "fr", "[Investissez|Placez] {amount_mid} {dh} [aujourd'hui|maintenant] et [recevez|retirez] {amount_big} {dh} [en {days} jours|dans {days} jours]. [Gains garantis|Sans risque|100% sécurisé], [rejoignez notre groupe|contactez notre conseiller] [Telegram|WhatsApp] : {chat_link}"),
("investment", "dar_lat", "[bghiti|wach bghiti] [tdobbel|tdoubli] flousk [f {days} ayam|f simana]? [7tt|dir] {amount_mid}dh [f crypto|f trading|m3ana] w [nrj3oulk|ghadi twslek] {amount_big}dh, [mdmon|garanti] 100%"),
("investment", "dar_ar", "[استثمر|حط] معانا {amount_mid} درهم و [غادي توصلك|ترجع ليك] {amount_big} درهم [من بعد {days} أيام|فسيمانة]، [ربح مضمون|بلا مخاطرة|مضمونة 100%]: {chat_link}"),
("investment", "en", "[Earn|Make] {pct}% [daily|weekly] [returns|profit] with our [crypto|forex|bitcoin] [plan|robot]. [Minimum deposit|Start with] {amount_mid} MAD. [Guaranteed profit|No risk]: {chat_link}"),
("investment", "msa", "[استثمر|ضاعف أموالك] مع [منصتنا|خبرائنا] في [العملات الرقمية|التداول] واربح {pct}% [يوميا|أسبوعيا]. [أرباح مضمونة|بدون مخاطرة]. [انضم الآن|تواصل معنا]: {chat_link}"),
# --- lotteries, giveaways, tickets
("lottery", "fr", "[Félicitations|Bravo] ! [Votre numéro a été tiré au sort|Vous avez été sélectionné] [pour|et gagnez] [une Omra gratuite|un voyage à La Mecque|un bon d'achat {merchant} de {amount_big} {dh}|{amount_big} {dh}]. [Pour confirmer|Pour recevoir votre gain], [payez|réglez] [les frais de dossier de|seulement] {amount_mid} {dh} [avant demain|ici] : {link}"),
("lottery", "fr", "[{merchant}|{merchant} Maroc] fête ses {years} ans : [gagnez|recevez] un bon d'achat de {amount_big} {dh} ! [Répondez à 3 questions|Partagez avec 10 amis] : {link}"),
("lottery", "fr", "[Billets|Tickets] [Coupe du Monde 2030|CAN|match du Maroc] [disponibles|à prix réduit] ! [Paiement par|Envoyez le montant par] {money_service} [et recevez vos billets sur WhatsApp|]"),
("lottery", "dar_ar", "مبروك! [ربحتي|تختاريتي باش تربح] [عمرة فابور|بون ديال {amount_big} درهم من {merchant}|{amount_big} درهم]. [باش تاخد الجائزة|باش تأكد]، [خلص|صيفط] {amount_mid} درهم [ديال الملف|ديال المصاريف] [هنا|]: {link}"),
("lottery", "dar_ar", "[تذاكر|بياي] [ماتش المنتخب|كاس العالم 2030] [متوفرين|كاينين] [بثمن مزيان|]، [صيفط الفلوس|خلص] [ف{money_service_ar}|] و [نصيفط ليك|توصلك] [التذكرة|البياي] [فالواتساب|]"),
("lottery", "dar_lat", "{merchant} [kat7tafel|kay7tafel] b {years} 3am, [rbe7|rb7] bon d'achat dyal {amount_big}dh! [jawb 3la 3 les questions|partagi m3a 10 dyal s7abk]: {link}"),
("lottery", "dar_lat", "[mbrok|mabrouk], rbe7ti [3omra fabor|{amount_big}dh|iphone], [khlles|sift] ghir {amount_mid}dh [dyal frais|dyal dossier] bach [twslek|takhdha]: {link}"),
("lottery", "msa", "مبروك! لقد [ربحت|فزت ب] {amount_big} درهم في [السحب الشهري|المسابقة]. [للحصول على الجائزة|لاستلام الجائزة] [أرسل|أدخل] [رقم بطاقتك البنكية|معلوماتك البنكية ورمز التحقق|بياناتك] [عبر الرابط|]: {link}"),
("lottery", "en", "Congratulations! You [have won|were selected for] [{amount_big} MAD|a free Umrah trip|a {merchant} gift card]. To claim, pay a [{amount_mid} MAD processing fee|small fee] [here|now]: {link}"),
# --- marketplace (Avito fake buyers / deposits)
("marketplace", "dar_lat", "[salam|slm], [ana mehtam|3jbatni] b [l'annonce|{item}] dyalk f Avito, [ghadi nkhelsek|khelstek] [daba|] b {bank_short}, [dkhel|clicki 3la] had lien w [7et|dkhel] [ma3lomat la carte|numéro dyal la carte] bach [tqbed lflous|twslek lflous]: {link}"),
("marketplace", "dar_lat", "[salam|] khouya, [sift lia|sifet lia] {amount_small3} dh [dyal l3arboun|avance] bach [n7bes lik|nkhebi lik] {item}, [kayn bzaf dyal nas bghawha|kaynin nas akhrin]"),
("marketplace", "fr", "[Bonjour|Salam], j'ai [payé|réglé] votre [article|annonce] via [Avito Livraison|un paiement sécurisé]. Pour [recevoir l'argent|valider la vente], [confirmez|saisissez] votre carte [ici|sur ce lien] : {link}"),
("marketplace", "fr", "[Bonjour|Salut], l'article [est encore dispo|est réservé pour vous] mais [envoyez|il faut] un acompte de {amount_small3} {dh} par {money_service} pour le [réserver|bloquer]"),
("marketplace", "dar_ar", "[سلام|] [خويا|أختي]، [صيفط ليا|سيفط ليا] {amount_small3} درهم ديال العربون باش [نحبس ليك|نخبي ليك] {item_ar}، [كاين بزاف ديال الناس باغيينها|كاينين ناس آخرين]"),
("marketplace", "dar_ar", "[سلام|] [خلصتك|غادي نخلصك] على {item_ar} [ب{bank_ar}|]، دخل لهاد الرابط و [حط|دخل] معلومات البطاقة باش [توصلك الفلوس|تقبض]: {link}"),
# --- utilities
("utility", "fr", "[LYDEC|ONEE|REDAL|AMENDIS] : facture impayée de {amount_bill} {dh}. [Votre compteur sera coupé|Coupure prévue] [demain|aujourd'hui|sous {hours}h]. [Régularisez|Payez] [maintenant|ici] : {link}"),
("utility", "msa", "[المكتب الوطني للكهرباء والماء الصالح للشرب|ليديك|ريضال|أمانديس]: سيتم قطع [التيار الكهربائي|الماء] [عن منزلكم|] [اليوم|غدا] بسبب فاتورة غير مؤداة ({amount_bill} درهم). [ادفع الآن|سدد الآن] [عبر الرابط|]: {link}"),
("utility", "dar_ar", "[الضو|الما] غادي [يتقطع|يقطعوه] عليك [غدا|اليوم] حيت [الفاتورة|الفاكتورة] ما تخلصاتش ({amount_bill} درهم)، خلص [من هنا|دابا]: {link}"),
# --- generic account security
("account", "fr", "Votre compte [WhatsApp|Facebook|Instagram|Netflix|Google] sera [supprimé|suspendu|désactivé] [dans {hours}h|aujourd'hui]. [Vérifiez|Confirmez] [votre compte|votre numéro|votre paiement] [ici|] : {link}"),
("account", "en", "[URGENT|Alert]: your [WhatsApp|Facebook|Instagram|Netflix|Apple ID] account will be [suspended|deleted|locked] [in {hours} hours|today]. [Verify|Update your payment|Confirm your identity] [here|now]: {link}"),
("account", "dar_ar", "الحساب ديالك [فالواتساب|فالفيسبوك|فالأنستغرام] غادي [يتمسح|يتبلوكا] [من هنا {hours} ساعة|اليوم]، [أكد|فعل] الحساب ديالك [هنا|من هاد الرابط]: {link}"),
# --- curiosity lure links
("lure_link", "dar_lat", "[wach hada nta|chouf wach hadi nti|chofi had tsawer] [f had video|f had tsawer|] [😱|😂|] {short_link}"),
("lure_link", "dar_ar", "[شوف|شوفي] [واش هادا نتا|التصاور ديالك|هاد الفيديو] [فهاد الموقع|هنا] [😱|😂|] {short_link}"),
("lure_link", "fr", "[C'est toi sur cette vidéo ?|Regarde cette photo de toi] [😱|😂|] {short_link}"),
]

# ------------------------------------------------------------------ LEGIT templates (hard negatives)
LEGIT_TEMPLATES = [
# --- real OTPs (contain "code" but say NOT to share it)
("otp", "fr", "[Votre code|Code] [de validation|de vérification|d'activation|de confirmation] {brand_any} [est|:] {otp}. [Ne le communiquez à personne.|Ne le partagez jamais.|Valable 5 minutes.|Il expire dans 10 min.]"),
("otp", "fr", "{otp} est votre code de [vérification|connexion] {brand_any}. [Ne le communiquez jamais, même à un conseiller.|]"),
("otp", "fr", "<#> Votre code WhatsApp : {otp3}-{otp3}. Ne partagez pas ce code."),
("otp", "msa", "رمز [التحقق|التأكيد] [الخاص بك|] [هو|:] {otp}. [لا تشاركه مع أي شخص.|صالح لمدة 5 دقائق.]"),
("otp", "en", "[Your|] {brand_any} [verification|security|login] code is {otp}. [Do not share it with anyone.|It expires in 10 minutes.|]"),
("otp", "fr", "Votre code de confirmation [Glovo|Jumia|Yassir] : {otp4}. [Donnez-le au livreur à la réception.|Communiquez-le au livreur uniquement à la livraison.]"),
# --- bank notifications
("bank_notice", "fr", "{bank} : [Paiement CB|Retrait GAB|Achat] de {amount_tx} MAD [chez {merchant}|à {city}] le {date} à {time}. [Solde disponible : {amount_bal} MAD|]"),
("bank_notice", "fr", "{bank} : votre virement de {amount_tx} MAD [vers {name}|] a été exécuté [avec succès|]."),
("bank_notice", "fr", "{bank} : votre [nouvelle carte|chéquier] est disponible [en agence|à l'agence {city}]. [Merci de vous présenter avec votre CIN.|]"),
("bank_notice", "fr", "{bank} : [un crédit|un versement] de {amount_tx} MAD a été effectué sur votre compte [le {date}|]."),
("bank_notice", "fr", "{bank} vous informe que l'agence {city} sera [fermée|exceptionnellement ouverte] [samedi|lundi] [de 9h à 12h|]. [Merci de votre compréhension.|]"),
("bank_notice", "fr", "{bank} : téléchargez notre nouvelle application [mobile|] sur {official_bank_link} [ou sur votre store|]."),
("bank_notice", "msa", "{bank_ar}: تم [خصم|أداء] مبلغ {amount_tx} درهم [من بطاقتكم|] [لدى {merchant}|] بتاريخ {date}."),
("bank_notice", "en", "{bank}: card payment of {amount_tx} MAD at {merchant} on {date}."),
("bank_notice", "fr", "[Rappel|Info] {bank} : votre échéance de crédit de {amount_tx} MAD sera prélevée le {date}. [Merci de vérifier votre solde.|]"),
# --- delivery
("delivery", "fr", "[AMANA|Barid Al-Maghrib|Poste Maroc] : votre envoi {tracking} [est disponible|est arrivé] à l'agence {city} [Principale|Centre|]. [Retrait sur présentation de la CIN.|Merci de vous présenter avec votre CIN.|]"),
("delivery", "fr", "[Jumia|Glovo|Avito Livraison|Kitea|Decathlon] : votre commande n°{order} [sera livrée|est en cours de livraison] [aujourd'hui|demain] [entre {h1}h et {h2}h|]. [Préparez {amount_tx} DH en espèces.|Le livreur vous appellera.|]"),
("delivery", "fr", "Suivez votre colis {tracking} sur {official_post_link}"),
("delivery", "msa", "بريد المغرب: [وصل|يوجد] طردكم رقم {tracking} [إلى|في] وكالة {city_ar}. [يرجى الحضور مع البطاقة الوطنية.|]"),
("delivery", "dar_lat", "[salam,|] ana [livreur|moul livraison] dyal [Jumia|Glovo|amana], [ana 9dam dar|wselt l {city}|fin nta]? [wajed {amount_small3}dh|]"),
("delivery", "dar_ar", "[سلام،|] أنا الليفرور ديال [جوميا|أمانة|كلوفو]، [راني قدام الدار|فين نتا؟|غادي نوصل من هنا ساعة]"),
# --- telecom
("telecom", "fr", "{telco} : votre recharge de {amount_small2} DH [a bien été effectuée|est confirmée]. [Vous bénéficiez de {go} Go valables {days} jours.|]"),
("telecom", "fr", "{telco} : [Félicitations|Bonne nouvelle] ! [Vous avez reçu|Profitez de] {go} Go [offerts|bonus] [pour votre fidélité|] [valables {days} jours|]. [Merci de votre confiance.|]"),
("telecom", "fr", "{telco} : votre facture de {amount_bill} DH est disponible. [Payez-la dans l'application|Consultez-la sur {official_telco_link}]."),
("telecom", "msa", "{telco_ar}: تم تفعيل [باقة الإنترنت|العرض] [بنجاح|]. [صالحة لمدة {days} أيام.|للاطلاع على رصيدك اتصل ب *{n3}#]"),
("telecom", "dar_ar", "{telco_ar}: [تشارجات ليك|دخلات ليك] التعبئة ديال {amount_small2} درهم، [عندك|ربحتي] {go} جيغا [صالحة|] [{days} أيام|]"),
# --- government (real notices: no request for card details)
("gov", "msa", "الصندوق الوطني للضمان الاجتماعي: تمت معالجة [ملف التعويض|ملفكم] رقم {ref} [وتحويل مبلغ {amount_tx} درهم إلى حسابكم|]."),
("gov", "fr", "CNSS : votre dossier [de remboursement|AMO] n°{n5} a été traité. [Montant viré : {amount_tx} DH.|] [Détails sur www.cnss.ma|]"),
("gov", "msa", "تذكير: [التسجيل|الأداء] يتم حصريا عبر الموقع الرسمي {official_gov_link} [أو لدى الملحقات الإدارية|]."),
("gov", "fr", "[Ministère de la Justice|NARSA] : vous pouvez consulter vos amendes sur le site officiel {official_fine_link}"),
("gov", "fr", "DGI : la date limite de dépôt de votre déclaration est le {date}. Rendez-vous sur www.tax.gov.ma"),
("gov", "msa", "الخزينة العامة للمملكة: تم تسجيل أدائكم بنجاح. رقم الإيصال {ref}."),
("gov", "msa", "[وزارة الداخلية|السلطة المحلية|الجماعة]: [تخبر|تعلن] الساكنة أن [عملية التلقيح|توزيع البطاقات|الإحصاء] [ستنطلق|ستجري] [يوم {date}|غدا] [بمقر الملحقة الإدارية|]."),
("gov", "fr", "Rappel : votre rendez-vous pour la CIN électronique est fixé au {date} à {time} au commissariat de {city}."),
# --- family money (legit)
("family_money", "dar_lat", "[salam|slm] {family_lat}, [sifett|sift] lik {amount_mid}dh f {money_service}, [code|l code] [howa|hwa] {otp4}, [sir|siri] [qbdihom|9bedhom] [mn b3d|ghda]"),
("family_money", "dar_lat", "{family_lat} [3afak|] [sift liya|3tini] {amount_small2} dh [dyal taxi|dyal tran|l kraa], [nrj3hom lik|ghadi nrdhom lik] [nhar {day_lat}|ghda]"),
("family_money", "dar_ar", "{family_ar} عافاك [صيفط ليا|عطيني] {amount_small2} درهم [ديال الطاكسي|ديال الكتب|]، [نرجعهم ليك|غادي نردهم ليك] [نهار {day_ar}|غدا]"),
("family_money", "fr", "[Maman|Papa], je t'ai envoyé {amount_mid} DH par {money_service}, le code est {otp4}."),
("family_money", "dar_ar", "[ماما|بابا] صيفطت ليك {amount_mid} درهم [فوفاكاش|فكاش بلوس]، الكود هو {otp4}"),
# --- promos (official links or none)
("promo", "fr", "{merchant} : [-{pct}%|Promo] sur [l'électroménager|les vêtements|toute la boutique] [jusqu'à dimanche|ce week-end]. [Plus d'infos sur {official_merchant_link}|En magasin uniquement|]"),
("promo", "fr", "{telco} : profitez du Pass [Internet|Réseaux sociaux] {go} Go à {amount_small2} DH. [Composez *{n3}#|Plus d'infos sur {official_telco_link}]"),
("promo", "dar_ar", "[تخفيضات|بروموسيون] عند {merchant} حتى ل {pct}% [هاد السيمانة|هاد الويكاند]، [مرحبا بيكم|]"),
# --- appointments / school / transport
("appointment", "fr", "Rappel : votre rendez-vous [chez le Dr {name}|au centre de santé|à la banque] est [prévu|confirmé] [demain|le {date}] à {time}."),
("appointment", "msa", "تذكير: موعدكم [بالمستشفى|بمركز التلقيح|مع الطبيب] [يوم {date}|غدا] على الساعة {time}."),
("transport", "fr", "ONCF : votre billet {city} - {city} du {date} à {time} est confirmé. Voiture {n1}, place {n2}."),
("school", "fr", "[ENIAD|La faculté|L'école] : [les examens|le rattrapage|la réunion] [commencent|aura lieu] le {date} à {time}. [Consultez l'ENT.|]"),
("school", "dar_lat", "[salam|slm] [drari|lwlad], [l prof|l'examen] [ma ghadich yji|t2ejjel] [lyoum|ghda], [sifto lkhbar|chofo l groupe]"),
("chat", "fr", "[Voici|Je t'envoie] le lien [de la réunion|du cours|du document] : {misc_link}"),
("chat", "dar_lat", "[chouf|chof|ra sifetlek] [had lien|l lien] [dyal l cours|dyal live|dyal video]: {misc_link}"),
("chat", "dar_ar", "[شوف|هاك] [الرابط|اللينك] [ديال الدرس|ديال الفيديو|ديال الاجتماع]: {misc_link}"),
# --- ordinary requests between friends/family ("send me the photo/number/pdf") - hard negatives
("ask_friend", "dar_lat", "[3afak|wlah ila|] [sift lia|sifto lia|sifti liya] [la photo dyal {thing_lat}|l pdf dyal {thing_lat}|numéro dyal {person_lat}|l'adresse dyal {person_lat}|la localisation|les cours dyal lyoum|smiya w numéro dyal {person_lat}] [3afak|daba ila 9diti|mli tfra8|]"),
("ask_friend", "dar_ar", "[عافاك|الله يخليك|] [صيفط ليا|صيفطي ليا] [الصورة ديال {thing_ar}|الرقم ديال {person_ar}|العنوان ديال {person_ar}|اللوكاليزاسيون|الدروس ديال اليوم] [ملي تفضى|دابا إلا قدرتي|]"),
("ask_friend", "fr", "[Tu peux m'envoyer|Envoie-moi|Peux-tu me transférer] [la photo de {thing_fr}|le numéro de {person_fr}|l'adresse de {person_fr}|le cours de ce matin|la localisation] [stp|svp|quand tu peux|] ?"),
("ask_friend", "en", "[Can you send me|Please send me|Send me] [the photo of {thing_en}|{person_en}'s number|the address|the notes from class] [when you can|please|]"),
# --- sharing ordinary links (unknown but harmless sites) and business contacts
("link_share", "fr", "[Regarde|Voici] [le site|la page|le menu|l'article] [du restaurant|de l'hôtel|du club|de l'association|dont je t'ai parlé] : {benign_link}"),
("link_share", "dar_lat", "[chouf|chof|hak] [l site|la page|menu|l'article] dyal [restaurant|l'hôtel|l club|l jam3iya|li gltlek 3lih]: {benign_link}"),
("link_share", "dar_ar", "[شوف|هاك] [الموقع|الصفحة|المينو] ديال [الريسطو|الأوطيل|الجمعية|النادي] [اللي قلت ليك عليه|]: {benign_link}"),
("link_share", "en", "[Check out|Here's] [the website|the menu|the article|the page] [I told you about|for the event|]: {benign_link}"),
("link_share", "fr", "[Inscriptions ouvertes|Nouvelle saison] [au club|à l'académie|à l'atelier] ! [Plus d'infos|Programme et horaires] sur {benign_link}"),
("business", "fr", "[Pour réserver|Pour toute information|Livraison à domicile], appelez le {ma_phone} [ou passez nous voir à {city}|]. [Merci de votre confiance.|]"),
("business", "dar_lat", "[ila bghiti tcommandi|bach t réservi|l ay ma3loma] [3ayet|appeli] l {ma_phone}, [ghadi nwslouha lik|kayn livraison] f {city}"),
("business", "dar_ar", "[للحجز|للطلب|لأي معلومة] [عيط|اتصل] على {ma_phone}، [كاين التوصيل|مرحبا بيكم] ف{city_ar}"),
# --- anti-scam warnings (contain scam vocabulary but are protective)
("warning", "dar_ar", "[حضي راسك|ردو البال]، كاينين [ميساجات|رسائل] ديال [النصب|الاحتيال] [على الغرامات|على الكوليات|باسم البنك]، [ما تكليكيش|ما تكليكيو] على [حتى رابط|الروابط] [وما تعطيو الكود لحتى واحد|]"),
("warning", "dar_lat", "[3ndak|rdo lbal], kayna [arnaque|nasba] [b smiya dyal|f smiya dyal] [CIH|amana|l3adala|inwi], [matclickich 3la 7ta lien|ma t3ti l code l 7ta wa7ed]"),
("warning", "fr", "[Attention|Prudence] : [des SMS frauduleux|une arnaque] [circulent|circule] au nom de [la NARSA|Barid Al-Maghrib|votre banque]. Ne cliquez sur aucun lien et ne communiquez jamais vos codes."),
("warning", "msa", "[تحذير|تنبيه]: [تنتشر|انتشرت] رسائل [احتيالية|نصب] باسم [وزارة العدل|البريد|الأبناك]. لا تضغطوا على الروابط ولا تشاركوا رمز التحقق مع أي أحد."),
]

# short chat lines (SMS style) to complement the real Darija corpora
CHAT_LINES = [
    "fin nta?", "ana jay f tri9", "wach klina?", "3ayet lia mli tfra8", "chno katdir lyoum?", "rani f dar",
    "ghda nchofk inchallah", "safi ok", "wakha a sa7bi", "mbrok 3lik", "l7amdolilah", "baraka lah fik", "bslama",
    "rak m3ana l3cha?", "jib m3ak lkhobz", "fin ghadi tkoun 3la 8?", "nsit tilifoun f dar", "wach mzyan l cours dyal lyoum?",
    "sifet lik les photos f whatsapp", "ra l prof ma jach", "kayn exam nhar tnin", "jib l pc dyalk ghda", "safi ana mchit",
    "rah lmatch bda", "wach rak mrid?", "lah ychafik", "tsbe7 3la khir", "mbrok l3id", "rmdan mbarak", "wach wselti?",
    "ana f l9ahwa", "fin l9itha?", "ma3ndich rsid", "3awd 3ayet lia", "ghadi nta3tal chwiya", "kolchi bikhir?",
    "Je suis en retard, j'arrive dans 10 min", "Tu es où ?", "On se voit demain à la fac", "Merci pour ton aide !",
    "Bonne nuit", "Tu peux m'appeler quand tu es libre ?", "J'ai oublié mes clés", "Le cours est annulé demain",
    "Bon anniversaire !", "Tu as vu le match hier ?", "Je t'envoie le document ce soir", "On mange ensemble ?",
    "Ok ça marche", "Je suis arrivé", "Appelle-moi stp", "Tu rentres à quelle heure ?", "C'est noté, merci",
    "فين نتا؟", "أنا جاي فالطريق", "شنو كتدير؟", "عيط ليا ملي تفضى", "غدا نشوفك إن شاء الله", "مبروك عليك",
    "الحمد لله", "بارك الله فيك", "صباح الخير", "رمضان مبارك", "عيد مبارك سعيد", "شكرا جزيلا", "تقبل الله منا ومنكم",
    "واش وصلتي؟", "جيب معاك الخبز", "راني فالدار", "الله يشافيك", "تصبح على خير", "واش كلا الدرس؟",
]


def render(template, rng, campaign):
    out = re.sub(r"\[([^\[\]]*)\]", lambda m: rng.choice(m.group(1).split("|")), template)
    out = re.sub(r"\{(\w+)\}", lambda m: SLOTS[m.group(1)](rng, campaign), out)
    return re.sub(r"\s{2,}", " ", out).replace(" ,", ",").replace(" .", ".").strip()


EMO_SCAM = ["⚠️", "🚨", "❗", "📦", "🎁", "💰", "✅", "🔔", "👉", "⏰", "🔒"]
EMO_LEGIT = ["😂", "❤️", "🙏", "😊", "👍", "🤲", "😅", "🌹"]


def strip_accents_fr(s):
    table = str.maketrans("éèêëàâäîïôöùûüçÉÈÊÀÂÎÔÙÛÇ", "eeeeaaaiioouuucEEEAAIOUUC")
    return s.translate(table)


def noise(text, rng, scam):
    r = rng.random()
    if r < 0.18:
        text = (rng.choice(EMO_SCAM if scam else EMO_LEGIT) + " " + text) if rng.random() < 0.5 else (text + " " + rng.choice(EMO_SCAM if scam else EMO_LEGIT))
    if rng.random() < 0.20:
        text = strip_accents_fr(text)
    if rng.random() < 0.08:
        text = text.upper() if scam and rng.random() < 0.5 else text.lower()
    if rng.random() < 0.10:
        text = text.replace(", ", " ").replace(". ", " ")
    if scam and rng.random() < 0.07:
        text = rng.choice(["URGENT: ", "IMPORTANT : ", "ALERTE : ", "عاجل: ", "تنبيه: "]) + text
    return text


def generate(templates, n_per_template, seed, scam):
    rng = random.Random(seed)
    rows = []
    for tid, (campaign, lang, tpl) in enumerate(templates):
        seen = set()
        for _ in range(n_per_template * 3):
            if len([1 for r in rows if r["template_id"] == f"{'S' if scam else 'L'}{tid:03d}"]) >= n_per_template:
                break
            t = noise(render(tpl, rng, campaign), rng, scam)
            if t in seen:
                continue
            seen.add(t)
            rows.append({"text": t, "label": int(scam), "campaign": campaign, "lang": lang,
                         "template_id": f"{'S' if scam else 'L'}{tid:03d}", "source": "synthetic"})
    return rows


if __name__ == "__main__":
    rng = random.Random(0)
    for c in ["traffic_fine", "bank_phishing", "parcel", "family", "whatsapp_hijack"]:
        tpls = [t for t in SCAM_TEMPLATES if t[0] == c]
        for _ in range(2):
            ca, la, tp = rng.choice(tpls)
            print(f"[{ca}/{la}] {noise(render(tp, rng, ca), rng, True)}")
    print("---- legit")
    for _ in range(8):
        ca, la, tp = rng.choice(LEGIT_TEMPLATES)
        print(f"[{ca}/{la}] {noise(render(tp, rng, ca), rng, False)}")
    print(len(SCAM_TEMPLATES), "scam templates,", len(LEGIT_TEMPLATES), "legit templates,", len(CHAT_LINES), "chat lines")
