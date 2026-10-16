"""
Hand-written CHALLENGE SET (test-only, never used for training).

Written separately from the training templates, in a different style, to
approximate real messages Moroccans receive. Scams are modelled on the
campaigns documented by DGSSI, the Ministry of Justice, Maroc Telecom,
Bank Al-Maghrib and the Moroccan press in 2025-2026. Legit messages are
deliberately tricky "hard negatives" (real OTPs, real bank/Amana/CNSS
notices, family money talk, messages that *warn* about scams...).

The real exam is still data/real_messages.csv: messages your team collects
from family WhatsApp groups (numbers and names removed).

Run:  python data/make_challenge_set.py   ->  data/challenge_set.csv
"""
import csv, os

S = 1  # scam
L = 0  # legit

ROWS = [
# ---------------------------------------------------------------- traffic fines
(S, "traffic_fine", "msa", "+44 7520 113 284", "المملكة المغربية - وزارة العدل. إشعار بالتنفيذ الإداري رقم 4471/2026: تم رصد مخالفة مرورية بواسطة كاميرا المراقبة. يتعين أداء الغرامة داخل أجل 48 ساعة تفاديا للحجز على حسابكم البنكي. للاطلاع على الفيديو والأداء: https://justice-amendes.icu/v/4471"),
(S, "traffic_fine", "fr", "+63 917 552 0193", "Avis d'exécution administrative n°2026-11873 : une infraction au code de la route a été constatée par radar. Montant dû : 300 DH. Sans règlement sous 24h, une majoration et une saisie seront appliquées. Consultez la vidéo : narsa-infractions.top/dossier"),
(S, "traffic_fine", "dar_ar", "", "عندك مخالفة ديال الرادار مازال ما خلصتيهاش، إلا ما خلصتيش اليوم غادي تدوبل عليك. خلص من هنا: amende-radar-ma.live"),
(S, "traffic_fine", "fr", "", "NARSA: Dernier rappel. Votre contravention n° 88231 n'a pas été réglée. Évitez les poursuites judiciaires en payant ici: http://bit.ly/narsa-pv-88231"),
(S, "traffic_fine", "msa", "", "إشعار نهائي: لديكم غرامة مرورية غير مسددة بقيمة 700 درهم. يرجى التسديد فورا عبر الرابط لتجنب تحويل الملف إلى المحكمة https://tgr-paiement.cfd"),
(S, "traffic_fine", "en", "+1 202 555 0147", "Kingdom of Morocco traffic enforcement: unpaid speeding fine of 450 MAD. Pay within 24 hours to avoid license suspension: https://gov-ma-fines.com"),
# ---------------------------------------------------------------- bank phishing
(S, "bank_phishing", "fr", "+33 7 56 12 98 40", "CIH BANK: Une opération de 6 980,00 MAD a été initiée depuis un nouvel appareil. Si vous n'êtes pas à l'origine de cette opération, annulez-la immédiatement : https://cih-annulation.com/secure"),
(S, "bank_phishing", "fr", "", "Attijariwafa bank : votre accès Attijarinet sera désactivé aujourd'hui. Merci de confirmer votre identité pour le conserver : attijari-verif.web.app"),
(S, "bank_phishing", "dar_ar", "", "البنك الشعبي: تم توقيف البطاقة ديالك مؤقتا بسبب محاولة دخول مشبوهة. دخل للرابط باش تفعلها من جديد http://chaabi-secure.xyz"),
(S, "bank_phishing", "msa", "", "عميلنا العزيز، تم تعليق حسابكم لدى بريد بنك لعدم تحديث المعطيات. المرجو تحديث بياناتكم عبر الرابط التالي داخل 12 ساعة: https://albaridbank-ma.online"),
(S, "bank_phishing", "en", "", "Bank of Africa alert: unusual login detected on your account. Secure your account now: https://boa-ma-security.net/login"),
(S, "bank_phishing", "mix", "", "Bonjour, l compte dyalk f Saham Bank t bloqua. Khassk t confirmer les informations dyalk f had lien: sahambank-ma.site"),
# ---------------------------------------------------------------- fake bank agent asking for codes
(S, "bank_otp", "dar_lat", "", "Salam, m3ak Karim mn service client dyal CIH. Kayn wa7d l opération machi normal f la carte dyalk. Daba ghayjik code f SMS, 3tih lia bach nlghiwha"),
(S, "bank_otp", "dar_ar", "", "السلام، أنا موظف فالبنك ديالك. باش نحميو الحساب ديالك صيفط ليا الرمز اللي غيوصلك دابا فالميساج"),
(S, "bank_otp", "fr", "", "Service sécurité Banque Populaire : pour bloquer la transaction frauduleuse, communiquez-nous le code reçu par SMS ainsi que les 3 chiffres au dos de votre carte."),
(S, "bank_otp", "dar_lat", "", "khouya ana mn bank, 3tini ghir les 3 ar9am li mor la carte w date d'expiration bach n7bes l prélèvement"),
# ---------------------------------------------------------------- parcels
(S, "parcel", "fr", "", "Barid Al-Maghrib : votre colis est bloqué au centre de tri de Casablanca suite à une adresse incomplète. Réglez 12,99 DH pour reprogrammer la livraison : https://poste-ma-livraison.top"),
(S, "parcel", "msa", "", "بريد المغرب: طردكم في انتظار أداء رسوم الجمارك (19 درهم). يرجى الأداء قبل منتصف الليل وإلا سيتم إرجاع الطرد: https://barid-colis.cfd"),
(S, "parcel", "dar_ar", "", "عندك كوليس فأمانة ما قدرناش نوصلوه ليك، أكد العنوان ديالك وخلص 10 دراهم ديال التوصيل هنا amana-suivi.shop"),
(S, "parcel", "en", "", "DHL Express: your package from Spain is awaiting customs clearance. Pay 25 MAD to release it: dhl-ma-customs.com/pay"),
(S, "parcel", "fr", "", "AMANA: dernière tentative de livraison aujourd'hui. Confirmez vos coordonnées et payez les frais de 7 DH ➡ cutt.ly/amana-livr"),
# ---------------------------------------------------------------- telecom prizes
(S, "telecom_prize", "fr", "", "Maroc Telecom vous remercie ! Vos 18 700 points fidélité expirent ce soir. Convertissez-les en Samsung Galaxy : iam-points.top"),
(S, "telecom_prize", "dar_ar", "", "مبروك عليك! تختاريتي باش تاخد نمرة 0661 مميزة فابور من اتصالات المغرب. دخل معلوماتك هنا قبل ما تسالي العرض"),
(S, "telecom_prize", "dar_lat", "", "inwi: rbe7ti 50 Go internet b blash! Clicki 3la had lien w dkhel numéro dyal la carte bach t activi l cadeau: inwi-cadeau.click"),
(S, "telecom_prize", "fr", "", "Orange Maroc: Félicitations, vous êtes le gagnant d'un iPhone 17. Pour recevoir votre cadeau, réglez seulement 19 DH de frais d'envoi : orange-ma-gift.com"),
# ---------------------------------------------------------------- government aid / refunds
(S, "gov_aid", "msa", "", "الدعم الاجتماعي المباشر: ملفكم غير مكتمل. لتفادي توقيف الدعم المرجو تحيين المعطيات البنكية عبر الرابط: https://asd-maroc.online"),
(S, "gov_aid", "dar_ar", "", "خبار زوينة: تقبل الطلب ديالك فدعم السكن 70000 درهم، غير أكد الرقم ديال البطاقة البنكية باش يتحول ليك المبلغ daam-sakane.info"),
(S, "gov_aid", "fr", "", "CNSS : un remboursement AMO de 1 245,60 DH est en attente. Pour le recevoir, confirmez votre RIB et votre carte bancaire : cnss-remboursement.site"),
(S, "gov_aid", "msa", "", "السجل الاجتماعي الموحد: تم اختياركم للاستفادة من منحة استثنائية قدرها 2500 درهم. أدخل رقم بطاقتك الوطنية وبطاقتك البنكية هنا rsu-minha.top"),
(S, "gov_aid", "fr", "", "Direction Générale des Impôts : vous êtes éligible à un remboursement de 980 DH. Remplissez le formulaire avant le 20/10 : impots-ma.info/remb"),
# ---------------------------------------------------------------- family impersonation
(S, "family", "dar_lat", "+212 6 47 22 18 90", "salam mama, ana Yassine, hadi nmra jdida dyali, tilifoun l9dim t3attal. 3afak sajliha"),
(S, "family", "dar_lat", "", "baba 3afak sift liya 1500 dh daba f Wafacash, ana f mochkil kbir, ghadi nfhamek mn b3d. matgoul l 7ta wa7ed"),
(S, "family", "dar_ar", "", "ماما، هادي نمرتي الجديدة. عافاك ديري ليا تعبئة ديال 200 درهم ضروري، التيليفون ديالي ما فيهش الصولد"),
(S, "family", "fr", "", "Coucou c'est moi, j'ai changé de numéro. Tu peux me faire un virement de 3000 DH aujourd'hui ? Je t'expliquerai, c'est urgent"),
(S, "family", "dar_lat", "", "khti rani f sbitar w ma 3ndich lflous, sifti liya 800dh f cash plus 3la smiya dyal had sa7bi, 3afak bla matsowli"),
(S, "family", "dar_ar", "", "خويا راني ف المطار و تشدات ليا الباليزة، خاصني 2000 درهم دابا دابا، صيفطهم ليا فهاد الرقم ديال الحساب"),
# ---------------------------------------------------------------- WhatsApp account hijack
(S, "whatsapp_hijack", "dar_lat", "", "salam, sme7 lia ghlatt w sifet lik wa7d l code dyal 6 dyal ar9am, 3afak 3awd sifto liya"),
(S, "whatsapp_hijack", "fr", "", "Bonjour, je vous ai envoyé un code à 6 chiffres par erreur, pouvez-vous me le transférer svp ? C'est urgent"),
(S, "whatsapp_hijack", "dar_ar", "", "سمح ليا صيفطت ليك واحد الكود بالغلط فالميساج، عافاك صيفطو ليا"),
(S, "whatsapp_hijack", "en", "", "Hi, I accidentally sent my verification code to your number, can you forward it to me please?"),
# ---------------------------------------------------------------- job scams
(S, "job", "fr", "", "Recrutement urgent pour la récolte des fraises à Huelva (Espagne). Contrat de 6 mois, logement offert. Frais de dossier : 1 800 DH par Cash Plus. Places très limitées !"),
(S, "job", "dar_lat", "", "Khdma f Canada, contrat w visa mdmonin, salaire 25000dh. Khass ghir t sifet 3000dh dyal dossier w passeport dyalk f WhatsApp"),
(S, "job", "dar_ar", "", "خدمة من الدار: غادي تربح 600 درهم فالنهار غير بالجيمات على فيديوهات يوتيوب. تواصل معانا فتيليغرام"),
(S, "job", "fr", "", "Bonjour ! Nous recrutons des assistants en ligne, 2h/jour, 400 DH par jour. Contactez notre RH sur WhatsApp : wa.me/447700900123"),
(S, "job", "msa", "", "مطلوب عمال للعمل في قطر برواتب مغرية، التأشيرة مضمونة 100%. لحجز مكانك أرسل 2500 درهم رسوم الملف"),
# ---------------------------------------------------------------- investment
(S, "investment", "fr", "", "Investissez 2 000 DH aujourd'hui et retirez 15 000 DH dans 10 jours grâce à notre robot de trading. Gains garantis, rejoignez le groupe Telegram"),
(S, "investment", "dar_lat", "", "drari bghiti tdobbel flousk f simana? 7tt 1000dh f crypto m3ana w nrje3hom lik 5000dh, mdmon 100%"),
(S, "investment", "dar_ar", "", "استثمر معانا 500 درهم و غادي توصلك 3000 درهم من بعد 3 أيام، ربح مضمون بلا مخاطرة"),
(S, "investment", "en", "", "Earn 30% daily returns with our Bitcoin mining plan. Minimum deposit 200 USD. Guaranteed profit, withdraw anytime: crypto-maroc-invest.com"),
# ---------------------------------------------------------------- lotteries, tickets, giveaways
(S, "lottery", "fr", "", "Félicitations ! Votre numéro a été tiré au sort pour une Omra gratuite. Pour confirmer, payez les frais de dossier de 500 DH avant demain."),
(S, "lottery", "dar_ar", "", "تذاكر ماتش المنتخب الوطني متوفرين عندي بثمن مناسب، صيفط الفلوس فوفاكاش و نصيفط ليك التذكرة فواتساب"),
(S, "lottery", "dar_lat", "", "Marjane kat7tafel b 20 3am, rbe7 bon d'achat dyal 3000dh! Jawb 3la 3 dyal les questions w partagi m3a 10 dyal sshab: marjane-cadeau.xyz"),
(S, "lottery", "fr", "", "Coupe du Monde 2030 : devenez bénévole officiel ! Inscription ouverte, frais de 250 DH à régler ici : fifa2030-maroc-benevoles.com"),
(S, "lottery", "msa", "", "مبروك! لقد ربحت 50000 درهم في السحب الشهري. للحصول على الجائزة أرسل رقم بطاقتك البنكية ورمز التحقق"),
# ---------------------------------------------------------------- marketplace (Avito)
(S, "marketplace", "dar_lat", "", "salam, ana mehtam b la télé li 3ndk f Avito, ghadi nkhelsek daba b CIH, dkhel l had lien w 7et ma3lomat la carte bach tqbed lflous: avito-paiement.top"),
(S, "marketplace", "fr", "", "Bonjour, j'ai payé votre article via Avito Livraison. Pour recevoir l'argent, validez le paiement en saisissant votre carte ici : avito-ma-pay.com"),
(S, "marketplace", "dar_ar", "", "خويا صيفط ليا 200 درهم ديال العربون باش نحبس ليك الطوموبيل، كاين بزاف ديال الناس باغيينها"),
# ---------------------------------------------------------------- utilities
(S, "utility", "fr", "", "LYDEC : facture impayée de 486,30 DH. Votre compteur sera coupé demain à 9h. Régularisez maintenant : lydec-paiement.online"),
(S, "utility", "msa", "", "المكتب الوطني للكهرباء والماء الصالح للشرب: سيتم قطع التيار الكهربائي عن منزلكم اليوم بسبب فاتورة غير مؤداة. ادفع الآن عبر الرابط onee-facture.top"),
# ---------------------------------------------------------------- misc
(S, "account", "fr", "", "Votre compte WhatsApp sera supprimé dans 24 heures. Vérifiez votre numéro ici : whatsapp-verify.sbs"),
(S, "lottery", "dar_lat", "", "Salam, sme7 lia, wach nta li kont 3ndi f la liste dyal les gagnants? 3ayt lia daba 3la had numéro +44 7911 123456"),
(S, "account", "en", "", "URGENT: Your Netflix payment failed. Update your card within 24h to avoid suspension: netflix-billing-ma.com"),
(S, "bank_phishing", "msa", "", "تنبيه أمني من بنك المغرب: تم رصد عملية احتيالية على حسابكم. يرجى تأكيد هويتكم بإدخال معلومات البطاقة البنكية عبر الرابط bkam-securite.com"),
(S, "bank_phishing", "fr", "", "Bank Al-Maghrib : suite à la nouvelle réglementation, tous les comptes doivent être vérifiés avant le 31/10. Vérifiez le vôtre : bkam-verification.top"),
(S, "lure_link", "dar_ar", "", "سلام، شفت تصاور ديالك فهاد الموقع، شوف واش نتا هادا 😱 http://bit.ly/3xk9Pq"),
(S, "lure_link", "dar_lat", "", "wach hada nta f had video? 😂 shof: tinyurl.com/video-maroc-2026"),

# ================================================================ LEGIT (hard negatives)
(L, "otp", "fr", "CIH BANK", "Votre code de validation CIH Mobile est 739214. Ne le communiquez jamais à personne, même à un conseiller CIH."),
(L, "bank_notice", "fr", "AWB", "Attijariwafa bank: Paiement CB de 312,50 MAD chez MARJANE BERKANE le 09/10/2026 à 18:42."),
(L, "otp", "msa", "BMCE", "رمز التحقق الخاص بك هو 5841. لا تشارك هذا الرمز مع أي شخص."),
(L, "otp", "fr", "WhatsApp", "Votre code WhatsApp : 482-913. Ne partagez pas ce code."),
(L, "otp", "en", "Google", "G-582913 is your Google verification code."),
(L, "bank_notice", "fr", "CHAABI", "Banque Populaire : votre virement de 1 500,00 MAD vers M. AMINE a été exécuté avec succès."),
(L, "bank_notice", "fr", "", "Cher client, votre nouvelle carte bancaire est disponible en agence Oujda Centre. Merci de vous présenter muni de votre CIN."),
(L, "delivery", "fr", "AMANA", "AMANA : votre envoi CB847120395MA est disponible à l'agence Berkane Principale. Retrait sur présentation de la CIN."),
(L, "delivery", "fr", "Jumia", "Jumia : votre commande n°318842 sera livrée aujourd'hui entre 14h et 18h. Préparez 249 DH en espèces."),
(L, "delivery", "dar_lat", "0661 23 45 67", "salam, ana livreur dyal Jumia, ana 9dam dar, fin nta?"),
(L, "delivery", "msa", "BARID", "بريد المغرب: وصل طردكم رقم RR123456789MA إلى الوكالة. يرجى الحضور مع البطاقة الوطنية. تتبع الطرد على www.poste.ma"),
(L, "telecom", "fr", "IAM", "Maroc Telecom : votre recharge de 50 DH a bien été effectuée. Vous bénéficiez de 5 Go valables 7 jours."),
(L, "telecom", "fr", "inwi", "inwi: Félicitations ! Vous avez reçu 1 Go offert pour votre fidélité, valable 3 jours. Merci d'utiliser inwi."),
(L, "telecom", "msa", "Orange", "أورنج: تم تفعيل باقة الإنترنت الخاصة بك بنجاح. للاطلاع على رصيدك اتصل بـ 555."),
(L, "gov", "msa", "CNSS", "الصندوق الوطني للضمان الاجتماعي: تمت معالجة ملف التعويض رقم 2026-55120 وتحويل مبلغ 420 درهم إلى حسابكم البنكي."),
(L, "gov", "fr", "CNSS", "CNSS : votre dossier de remboursement n°88412 a été traité. Montant viré : 356,20 DH. Détails sur www.cnss.ma"),
(L, "gov", "msa", "", "تذكير: آخر أجل للتسجيل في السجل الاجتماعي الموحد هو 30 أكتوبر. التسجيل يتم حصريا عبر الموقع الرسمي www.rsu.ma أو لدى الملحقات الإدارية."),
(L, "gov", "fr", "", "Ministère de la Justice : vous pouvez consulter vos amendes radar sur le site officiel amendes.justice.gov.ma"),
(L, "family", "dar_lat", "+33 6 12 34 56 78", "salam mama, ana f France labas 3liya, sifett lik 2000dh f Wafacash, code howa 5521, sir qbdihom mn b3d l3sr"),
(L, "family", "dar_ar", "", "بابا عافاك صيفط ليا 100 درهم ديال الطاكسي، نهار الاثنين نرجعهم ليك"),
(L, "chat", "dar_lat", "", "khouya fin wslti? rana kantsnawk f l9ahwa"),
(L, "chat", "dar_ar", "", "ماما شنو نجيب معايا من الحانوت؟ الخبز و الحليب؟"),
(L, "chat", "fr", "", "Salut, tu peux m'envoyer le cours d'analyse de ce matin ? Merci !"),
(L, "chat", "dar_lat", "", "a sa7bi l match lyoum m3a 9 f l9ahwa dyal derb, matnsach"),
(L, "chat", "dar_ar", "", "مبروك عليك النجاح خويا، الله يكمل عليك بالخير"),
(L, "chat", "dar_lat", "", "wach 3ndek l code dyal wifi dyal dar? nsit"),
(L, "chat", "fr", "", "N'oublie pas de payer la facture d'électricité avant vendredi stp"),
(L, "chat", "dar_lat", "", "3afak sift liya la photo dyal la carte grise dyal tomobil, bghit n assuriha"),
(L, "chat", "dar_ar", "", "عيط ليا ملي تفضى، عندي ليك خبار مزيانة 😊"),
(L, "chat", "dar_lat", "", "rbe7na l match!!! 3-0 ya lwlad 😂🔥"),
(L, "chat", "fr", "", "Félicitations pour ton nouveau poste ! On fête ça samedi ?"),
(L, "chat", "dar_ar", "", "خويا راني فالمستشفى مع الواليدة، ماشي حتى حاجة خطيرة، غير الفحص العادي"),
(L, "appointment", "fr", "", "Bonjour M. Benali, votre rendez-vous chez le Dr Alaoui est confirmé pour demain à 10h30. Cabinet dentaire Al Amal."),
(L, "appointment", "msa", "", "تذكير: اجتماع أولياء التلاميذ يوم السبت على الساعة العاشرة صباحا بمقر المؤسسة."),
(L, "school", "fr", "", "ENIAD : les résultats du semestre sont affichés sur l'ENT. Bonne continuation à tous."),
(L, "school", "dar_lat", "", "salam, chi 7ad 3ndo l pdf dyal TD 3? sifto f groupe 3afak"),
(L, "chat", "en", "", "Hey, are we still on for dinner tonight? Let me know"),
(L, "promo", "fr", "MARJANE", "Promo Marjane : -30% sur l'électroménager jusqu'au dimanche. Voir le catalogue sur marjane.ma"),
(L, "chat", "dar_ar", "", "اليوم عندنا ضياف، جيبي معاك الحلوى من عند خالتي"),
(L, "transport", "fr", "ONCF", "ONCF : votre billet Casa Voyageurs - Oujda du 12/10 à 07h30 est confirmé. Voiture 5, place 42. Bon voyage."),
(L, "chat", "msa", "", "جمعة مباركة، تقبل الله منا ومنكم صالح الأعمال"),
(L, "chat", "dar_lat", "", "Ach had l3jab, chafti chi video dyal l match lbare7?"),
(L, "utility", "fr", "LYDEC", "Votre facture Lydec d'octobre est disponible : 236,40 DH. Paiement en agence, sur l'application Lydec ou sur www.lydec.ma"),
(L, "marketplace", "dar_lat", "", "salam khouya, nta bghiti tbi3 dak tilifoun dyalk? ana mehtam, nchoufo f lqahwa ghda?"),
(L, "marketplace", "fr", "", "Bonjour, je suis intéressé par votre annonce Avito pour l'appartement. Est-il encore disponible ? On peut visiter samedi ?"),
(L, "chat", "dar_ar", "", "عافاك سيفط ليا الرقم ديال السباك اللي جا عندكم"),
(L, "transport", "en", "Uber", "Your Uber is arriving in 3 minutes. Look for a white Dacia Logan."),
(L, "chat", "fr", "", "Rappel : la réunion de l'association est reportée à jeudi 18h. Merci de confirmer votre présence."),
(L, "chat", "dar_lat", "", "lyoum l3id, mbrok l3id 3likom w 3la l3a2ila kamla ❤️"),
(L, "gov", "msa", "TGR", "الخزينة العامة للمملكة: تم تسجيل أدائكم للضريبة بنجاح. رقم الإيصال 2026-88412."),
(L, "chat", "fr", "", "Hello, voici le lien du Google Meet pour la réunion de 15h : meet.google.com/abc-defg-hij"),
(L, "chat", "dar_lat", "", "ra sifetlek l lien dyal live dyal ENIAD 3la youtube, chofo daba: youtube.com/watch?v=dQw4w9WgXcQ"),
(L, "otp", "fr", "Glovo", "Votre code de confirmation Glovo : 4419. Donnez-le au livreur à la réception de votre commande."),
(L, "chat", "dar_ar", "", "حضي راسك، كاين ميساجات ديال النصب كيدورو على الغرامات، ما تكليكي على حتى رابط"),
]

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "challenge_set.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "campaign", "lang", "sender", "text"])
        for i, (lab, camp, lang, sender, text) in enumerate(ROWS, 1):
            w.writerow([f"C{i:03d}", lab, camp, lang, sender, text])
    n_s = sum(r[0] for r in ROWS)
    print(f"wrote {out}: {len(ROWS)} rows ({n_s} scams, {len(ROWS) - n_s} legit)")
