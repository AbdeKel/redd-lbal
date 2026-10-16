"""
BLIND SET 2 - written after engine v0.3 was frozen (rules + calibration), evaluated ONCE.
Plus 5 REAL fake-fine SMS (France, 2026) quoted verbatim by mailarnaque.fr - an
out-of-distribution check on real attacker wording.

Run:  python data/make_blind_set2.py   ->  data/blind_set2.csv
"""
import csv, os

S, L = 1, 0
ROWS = [
# ---- scams (messy, realistic)
(S, "traffic_fine", "dar_ar", "", "تنبيه!! عندك مخالفة السرعة تسجلات عليك نهار 3 اكتوبر. باش تشوف الصورة ديال الرادار و تخلص دخل هنا radar-maroc.info قبل ما يتزاد عليك الثمن"),
(S, "traffic_fine", "fr", "+44 7700 900 461", "Royaume du Maroc. Avis de contravention N 2026/88412. Montant 400 DH. Regularisation obligatoire sous 48h : infractions-maroc.com"),
(S, "bank_phishing", "dar_lat", "", "CIH: chi had dkhl l compte dyalk mn telephone jdid f Rabat. ila machi nta bloqi daba mn hna cih-alerte.com"),
(S, "bank_phishing", "fr", "", "Cher(e) client(e) Chaabi Net, votre session a expiré. Veuillez vous reconnecter afin d'éviter la désactivation de vos services : chaabinet-ma.com/connexion"),
(S, "bank_otp", "dar_ar", "", "مرحبا معاك مصلحة الزبناء، باش نرجعو ليك الفلوس اللي تقتطعو بالغلط خاصنا الكود اللي غادي يوصلك دابا فالرسالة"),
(S, "bank_otp", "fr", "", "Madame, pour annuler le prélèvement de 4 900 DH sur votre compte j'ai besoin du code de confirmation que la banque vient de vous envoyer"),
(S, "parcel", "fr", "", "Barid Al-Maghrib Express: Votre envoi est en attente au bureau de douane. Pour la libération, réglez 18,50 dhs ici avant 23h59 ➡ barid-express-ma.shop"),
(S, "parcel", "dar_lat", "", "Salam, l colis dyalk mn Shein w9ef f douane, khass tkhlles 22dh bach yfot. Lien: shein-maroc-livraison.com"),
(S, "parcel", "msa", "", "تعذر توصيل شحنتكم رقم MA22918. يرجى تحديث عنوان التسليم ودفع رسوم إعادة الإرسال 12 درهم عبر: tinyurl.com/amana-ma22"),
(S, "telecom_prize", "msa", "", "اتصالات المغرب تهنئكم: لقد تم اختيار رقمكم ضمن الفائزين بهاتف iPhone 17 Pro بمناسبة الذكرى السنوية. لاستلام الجائزة: maroctelecom-gift.top"),
(S, "telecom_prize", "fr", "", "Orange Maroc: votre ligne a cumulé 9 850 points. Ils expirent le 31/10. Echangez-les gratuitement contre un smartphone : orange-points-ma.com"),
(S, "gov_aid", "dar_lat", "", "Salam, dkhl smitk w numéro dyal la carte bancaire f had site bach tstafed mn da3m dyal 2000dh dyal dkhoul lmadrassi: da3m-madrasi.online"),
(S, "gov_aid", "fr", "", "Ministère de la Santé: suite à votre dernière consultation, un remboursement AMO de 640 DH vous est dû. Saisissez vos informations bancaires sur amo-sante-ma.com"),
(S, "family", "dar_ar", "", "سلام خالتي، أنا أمين ولد ختك، هادي نمرتي الجديدة. واش ممكن تسلفيني 1000 درهم دابا؟ ضروري بزاف، وما تقولي لماما"),
(S, "family", "dar_lat", "", "baba ana f lkoumissarya, khasni 3000dh dyal l'amende daba, sift lia f wafacash smiya: Hamid Alaoui, ma t3ayetch"),
(S, "family", "fr", "", "Salut tonton c'est Youssef, nouveau numéro. J'ai un souci avec ma carte bancaire, tu peux m'avancer 1500 DH par CashPlus ? Je te rembourse lundi"),
(S, "whatsapp_hijack", "dar_ar", "", "سلام، صيفطت ليك واحد الكود ديال 6 أرقام بلا ما نقصد، عطيه ليا عافاك ضروري"),
(S, "whatsapp_hijack", "en", "", "Hey! sorry, I typed your number by mistake for my WhatsApp, you'll get a 6 digit code. can u send it to me? thx"),
(S, "job", "dar_lat", "", "Wach bghiti tkhdem f Doha? salaire 9000dh + sakan. Ghir sift 1800dh dyal visa l had numéro w ghadi ntsalo bik"),
(S, "job", "fr", "", "Offre spéciale : devenez agent de saisie à domicile, 350 DH/jour. Inscription 200 DH à verser par Wafacash. Contactez Mme Laila sur WhatsApp"),
(S, "job", "msa", "", "فرصة عمل من المنزل: اربح من 300 إلى 900 درهم يوميا فقط بالإعجاب بالمنتجات. للتسجيل راسلنا على التيليغرام t.me/amal_jobs_ma"),
(S, "investment", "fr", "", "Mon conseiller m'a fait gagner 18 000 DH en 2 semaines grâce au trading automatique. Il accepte de nouveaux clients, rendement garanti. Ecris-lui: wa.me/447412345678"),
(S, "investment", "dar_lat", "", "Khoya 7ell compte f had plateforme crypto w 7et 1000dh, ghadi tchouf flousk tdoubla f 7 iyam, ana jarrebtha"),
(S, "lottery", "fr", "", "BRAVO ! Votre numéro est le grand gagnant du tirage Label'Vie : un bon d'achat de 5 000 DH. Frais de dossier : 49 DH. Validez ici : labelvie-gagnant.vip"),
(S, "lottery", "dar_ar", "", "مبروك ربحتي عمرة مجانية مع وكالة الأسفار، خلص غير 300 درهم ديال الملف فوفاكاش وسيفط ليا صورة البطاقة الوطنية"),
(S, "marketplace", "fr", "", "Bonjour, je suis à l'étranger, mon cousin viendra chercher le canapé. J'ai effectué le paiement, confirmez la réception en entrant vos coordonnées bancaires : avito-securepay.net"),
(S, "utility", "fr", "", "ONEE: Avis de coupure. Votre facture d'électricité de 312,40 DH reste impayée. Evitez la coupure de demain en payant ici: onee-payer.com"),
(S, "account", "msa", "", "فيسبوك: تم الإبلاغ عن حسابك بسبب مخالفة المعايير. إذا لم تقم بالتحقق خلال 24 ساعة سيتم حذفه نهائيا: fb-support-center.com"),
(S, "lure_link", "dar_ar", "", "شوفي واش هادي نتي فهاد الفيديو 😱😱 bit.ly/4kLm9P"),
(S, "account", "fr", "", "Votre abonnement Netflix est suspendu: paiement refusé. Mettez à jour votre moyen de paiement sous 24h : netflix-maroc-billing.com"),
(S, "bank_phishing", "en", "+1 415 555 0199", "CIH Bank security: your card has been temporarily blocked. Call our support line immediately."),
# ---- real fake-fine SMS (France 2026, verbatim from mailarnaque.fr)
(S, "traffic_fine", "fr_real", "", "ANTAI: Vous avez un avis de contravention impaye de 35EUR. Regle de majoree dans 48h. Regularisez: amendes-gouv-paiement.fr"),
(S, "traffic_fine", "fr_real", "", "INFO AMENDES: Votre PV n°2026-AF-4892 n'a pas ete regle. Passez au paiement pour eviter la majoration: pv-amendes-france.com/payer"),
(S, "traffic_fine", "fr_real", "", "Mairie de Paris: Votre vehicule a fait l'objet d'un FPS impaye. Regularisez avant majoration: fps-stationnement-paris.fr"),
(S, "traffic_fine", "fr_real", "", "RADAR AUTO: Exces de vitesse constate le 12/02. Montant: 135EUR. Payez avant majoration: radar-amendes.gouv-fr.com"),
(S, "traffic_fine", "fr_real", "", "TRESOR PUBLIC: Votre amende de 68EUR a ete majoree a 180EUR. Dernier delai de paiement: 48h. tresor-public-amendes.fr/payer"),
# ---- legit (hard)
(L, "otp", "dar_ar", "", "الكود ديالك هو 4417، ما تعطيه لحتى واحد حتى لموظف البنك"),
(L, "otp", "fr", "Yassir", "Yassir : votre code de vérification est 5512. Il expire dans 5 minutes."),
(L, "bank_notice", "fr", "SAHAM BANK", "Saham Bank : retrait de 1 000,00 MAD effectué le 08/10 à 19:12 au GAB Berkane Centre."),
(L, "delivery", "dar_lat", "", "salam 3afak wach nta f dar? ana livreur dyal amana 3ndi lik wa7d colis, 3ayet lia 3la 0661223344"),
(L, "delivery", "fr", "AMANA", "AMANA : votre colis CP118266534MA a été livré. Merci d'avoir choisi Amana."),
(L, "family", "dar_ar", "", "ماما راه صيفطت ليك 500 درهم فكاش بلوس، الكود هو 88213، سيري خدهم ملي تفيقي"),
(L, "family", "fr", "", "Papa, j'ai bien reçu l'argent pour l'inscription, merci beaucoup ! Je t'appelle ce soir."),
(L, "chat", "dar_lat", "", "wach 3ndk l code dyal l'examen dyal analyse? bghit nchouf ach jani"),
(L, "chat", "fr", "", "Le code du portail c'est 2580, je serai là vers 19h"),
(L, "chat", "dar_ar", "", "راه ربحنا الماتش أ صاحبي! الله يبارك، ديما مغرب 🇲🇦"),
(L, "chat", "en", "", "Congrats on the new job!! You totally deserve it 🎉"),
(L, "link", "fr", "", "Voici le lien pour suivre la conférence IBM en direct : www.ibm.com/events/z-datathon"),
(L, "link", "dar_lat", "", "drari ra l'emploi du temps jdid t7et f had lien drive.google.com/file/d/1aB2cD3eF4"),
(L, "link", "dar_ar", "", "شوفو هاد المقال على هسبريس، كيهضر على الاحتيال بالرسائل: www.hespress.com/societe"),
(L, "gov", "msa", "", "تذكير من وزارة الصحة: حملة التلقيح ضد الحصبة بالمراكز الصحية من 10 إلى 20 أكتوبر. اللقاح مجاني."),
(L, "gov", "fr", "DGI", "DGI : Rappel - la date limite de paiement de la taxe d'habitation est fixée au 31/10. Paiement sur www.tax.gov.ma ou auprès des percepteurs."),
(L, "promo", "fr", "inwi", "inwi : Profitez de -50% sur le Pass Internet ce week-end. Composez *6# pour l'activer."),
(L, "promo", "dar_ar", "", "تخفيضات كبار عند كيتيا حتى ل 50% غير هاد السيمانة، مرحبا بيكم فالمحل"),
(L, "marketplace", "dar_lat", "", "salam, wach l frigo mazal 3ndk? ila mazal nji nchofo ghda 3la 5, w nkhelsek cash ila 3jbni"),
(L, "warning", "fr", "", "Rappel de votre banque : nous ne vous demanderons jamais vos codes par SMS ou par téléphone. En cas de doute, appelez votre agence."),
(L, "warning", "dar_lat", "", "rdo lbal drari, kayn chi wa7d kaysifet messages smiyto 'Amana' w kaytleb 12dh, ma tclickiwch 3la lien"),
(L, "school", "fr", "", "Massar : les notes du premier contrôle sont disponibles. Consultez l'espace parents sur massar.men.gov.ma"),
(L, "bank_notice", "msa", "", "تم إيداع مبلغ 1.200,00 درهم في حسابكم من طرف الصندوق الوطني للضمان الاجتماعي."),
(L, "chat", "dar_lat", "", "3afak sift lia smiya w numéro dyal plombier li jak, bghit nsl7 robinet"),
(L, "appointment", "dar_ar", "", "سلام، عيادة الدكتور العلوي: موعدك غدا مع 11 صباحا، جيب معاك البطاقة الوطنية وورقة الضمان"),
]

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blind_set2.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "campaign", "lang", "sender", "text"])
        for i, (lab, camp, lang, sender, text) in enumerate(ROWS, 1):
            w.writerow([f"D{i:03d}", lab, camp, lang, sender, text])
    n_s = sum(r[0] for r in ROWS)
    print(f"wrote {out}: {len(ROWS)} rows ({n_s} scams, {len(ROWS) - n_s} legit)")
