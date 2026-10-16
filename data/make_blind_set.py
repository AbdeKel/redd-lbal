"""
BLIND SET - written AFTER the rules were frozen and never used to tune anything.
Its numbers are reported as-is. (Still written by us: the real test is
data/real_messages.csv, the messages your team collects.)

Run:  python data/make_blind_set.py   ->  data/blind_set.csv
"""
import csv, os

S, L = 1, 0
ROWS = [
(S, "traffic_fine", "fr", "", "Bonjour, ici le service des amendes. Un dossier de contravention est ouvert à votre nom. Pour éviter une procédure, payez en ligne sur paiement-pv.ma-gouv.org avant vendredi."),
(S, "traffic_fine", "dar_lat", "", "slm 3ndek amende dyal stationnement b 150dh, ila makhlsthach f 48h ghadi twli 450dh. khlss hna: amende-maroc.net"),
(S, "traffic_fine", "msa", "", "عزيزي المواطن، تم تسجيل مخالفة باسمكم. يرجى الاطلاع على ملفكم وتسوية وضعيتكم عبر البوابة: http://mahakim-ma.com/check"),
(S, "bank_phishing", "fr", "", "BMCI: Votre carte Visa expire bientôt. Pour éviter toute interruption, mettez à jour vos informations : bmci-carte.info"),
(S, "bank_phishing", "dar_ar", "", "عميلنا العزيز، تم تسجيل دخول جديد لحسابك فالتطبيق. إلا ماشي نتا عيط دابا ل +44 20 3966 1234"),
(S, "bank_otp", "dar_lat", "", "salam a sidi, ana mn l'agence dyal Al Barid Bank. Bach nkmlo l mise à jour dyal compte dyalk 3tini l code li wslk db"),
(S, "bank_phishing", "en", "", "Attijariwafa Bank: We detected a payment of 3,450 MAD at AMAZON. If this wasn't you, cancel here: attijari-cancel.com"),
(S, "parcel", "fr", "", "Votre colis Amana N° MA88712 attend un paiement de 11 DH (frais de réexpédition). Délai : 24h. https://amana-ma.delivery-help.com"),
(S, "parcel", "dar_ar", "", "سلام، الكوليس ديالك وصل لمراكز الفرز ولكن خاص تخلص 15 درهم ديال الديوانة باش يخرج. خلص هنا: bit.ly/3kD9ma"),
(S, "parcel", "en", "", "Aramex: Delivery failed. Your shipment is held at our warehouse. Update address & pay 9 MAD: aramex-ma.top/track"),
(S, "telecom_prize", "fr", "", "Félicitations ! inwi vous offre 30 Go pour l'anniversaire de la marque. Activez votre bonus avant minuit : inwi-30go.vip"),
(S, "telecom_prize", "dar_lat", "", "Maroc Telecom: 3ndek 25000 points ghadi ymchiw lyoum. Bddelhom b telephone Samsung: iam-cadeaux.shop"),
(S, "gov_aid", "msa", "", "وزارة الاقتصاد والمالية: تم قبول طلبكم للاستفادة من الدعم الاستثنائي. المرجو إدخال معلومات بطاقتكم البنكية لتحويل المبلغ: dae-maroc.site"),
(S, "gov_aid", "fr", "", "AMO Tadamon : votre droit à la couverture va expirer. Renouvelez gratuitement en confirmant vos données ici : amo-tadamon.online"),
(S, "gov_aid", "dar_ar", "", "تم تسجيلك فالدعم المباشر 500 درهم فالشهر، باقي غير تأكد رقم الحساب ديالك هنا قبل نهار الجمعة asd-ma.info"),
(S, "family", "dar_lat", "", "salam a mama hada ana Ilyas, tilifoun tkhser lia w hadi nmra dyal sa7bi, 3afak sifti liya 700dh f cash plus rani mzrob"),
(S, "family", "dar_ar", "", "بابا أنا هشام، الهاتف ديالي طاح ليا وتهرس، هادي نمرة جديدة. خاصني نخلص الكرا اليوم 1500 درهم، صيفطهم ليا فوفاكاش"),
(S, "family", "fr", "", "Maman c'est Sara, mon téléphone est tombé dans l'eau, je t'écris d'un autre numéro. J'ai besoin de 2000 DH pour payer le loyer aujourd'hui, tu peux faire un virement ?"),
(S, "whatsapp_hijack", "fr", "", "Salut c'est moi, je change de téléphone et j'ai mis ton numéro par erreur, tu vas recevoir un code par SMS, tu peux me l'envoyer stp ?"),
(S, "whatsapp_hijack", "dar_lat", "", "slm khoya, ghadi ywslek wa7d sms fih code, sifto liya 3afak ghalt w 7titt numero dyalk"),
(S, "job", "fr", "", "Bonjour ! Cherchons 50 personnes pour travail saisonnier en Italie. Salaire 1400€, billet et visa pris en charge. Envoyez 2000 DH de frais d'inscription via Western Union pour réserver."),
(S, "job", "dar_ar", "", "شركة كتقلب على ناس يخدمو من الدار، غير كتدير لايك للفيديوهات وكتربح 300 درهم فالنهار. صيفط لينا ميساج فالواتساب +44 7451 112233"),
(S, "job", "en", "", "Part-time job: earn 500-2000 MAD daily by rating hotels online. No experience needed. Contact HR on Telegram: t.me/hr_rating_ma"),
(S, "investment", "fr", "", "Rejoignez notre programme Bitcoin : +25% de rendement par semaine, capital garanti. Commencez avec 1 000 DH : wa.me/33612345678"),
(S, "investment", "dar_lat", "", "ana kan investi f wa7d plateforme w rbe7t 20000dh f chhar, bghiti nwrik? dakhal ghir b 500dh w rbe7 mdmon"),
(S, "lottery", "msa", "", "تهانينا! تم اختيار رقمكم للفوز بسيارة داسيا لوغان في سحب مرجان. لاستلام الجائزة يرجى أداء رسوم التسجيل 300 درهم."),
(S, "lottery", "dar_lat", "", "3ndi tickets dyal match lmaghrib w brazil b taman mzyan, sift lflous f wafacash w nsiftlek ticket f whatsapp"),
(S, "lottery", "fr", "", "Ministère des Habous : vous avez été tiré au sort pour le Hajj 2027. Confirmez votre place en réglant les frais de 5 000 DH ici : hajj-maroc.online"),
(S, "marketplace", "fr", "", "Bonjour, j'achète votre frigo sur Avito. Mon transporteur passera le récupérer. J'ai déjà payé, cliquez pour recevoir les fonds : avito-transfert.com/recevoir"),
(S, "marketplace", "dar_lat", "", "salam, l moto ba9a? ana f Tanger, sift lia 500dh avance f cashplus w nji nakhodha ghda"),
(S, "utility", "msa", "", "ريضال: لديكم فاتورة ماء غير مؤداة. سيتم قطع الماء خلال 24 ساعة. ادفع الآن عبر redal-paiement.com"),
(S, "account", "fr", "", "Instagram : votre compte a été signalé pour violation des droits d'auteur. Faites appel sous 24h sinon il sera supprimé : instagram-appeal-center.com"),
(S, "account", "dar_ar", "", "الواتساب ديالك غادي يتوقف إلا ما حدثتيش التطبيق، حدث من هنا: whatsapp-update.sbs"),
(S, "lure_link", "dar_lat", "", "Chouf chno katbe3 3lik f had video 😳 tinyurl.com/9x7kd2"),
(S, "account", "en", "", "Your Google account password was changed. If this wasn't you, recover it here: google-account-recovery.net"),
(S, "investment", "dar_ar", "", "ضاعف فلوسك فسيمانة! استثمر فالكريبتو مع خبراء مغاربة، الربح مضمون. تواصل معانا فتيليغرام"),
(S, "bank_phishing", "fr", "+234 803 555 0101", "Banque Populaire: votre compte présente une anomalie. Veuillez rappeler notre service client au plus vite."),
(S, "traffic_fine", "msa", "+63 912 345 6789", "المديرية العامة للأمن الوطني: تم تحرير محضر مخالفة في حقكم. المرجو التواصل معنا في أقرب الآجال."),
(S, "lottery", "dar_lat", "", "mbrok 3lik rb7ti iphone 16 f l concours dyal jumia, sift lina smiytek w adresse w 50dh dyal livraison"),
(S, "bank_otp", "fr", "", "Bonjour, c'est le service fraude de CIH. Nous allons vous envoyer un code pour sécuriser votre compte, merci de nous le lire dès réception."),
# ------------------------------------------------------------------ legit
(L, "otp", "fr", "CIH BANK", "CIH Bank : votre code d'accès à CIH Mobile est 551203. CIH ne vous demandera jamais ce code."),
(L, "bank_notice", "msa", "", "البنك الشعبي: تمت عملية سحب بقيمة 500 درهم من الشباك الأوتوماتيكي بتاريخ 09/10."),
(L, "delivery", "fr", "Jumia", "Votre colis Jumia n°552318 a été expédié. Suivez-le dans l'application Jumia."),
(L, "chat", "dar_lat", "", "salam, ana moul taxi li jabek lbare7, nsiti lk sac f tomobil, fin nji nrje3ho lik?"),
(L, "chat", "dar_ar", "", "ماما راني وصلت لكازا بالسلامة، غادي نعيط ليك فالليل"),
(L, "appointment", "fr", "", "Rappel : la vaccination de votre enfant est prévue le 15/10 au centre de santé de quartier. Pensez au carnet."),
(L, "gov", "msa", "", "وزارة الداخلية: يُخبَر المواطنون أن عملية تجديد البطاقة الوطنية تتم حصريا بمراكز الشرطة أو عبر الموقع الرسمي www.cnie.ma"),
(L, "telecom", "fr", "inwi", "inwi : Bonne nouvelle ! Votre Pass Réseaux Sociaux est activé pour 7 jours. Merci."),
(L, "chat", "dar_lat", "", "a khoya rani 3titek l code dyal la porte dyal l3imara, 1234#"),
(L, "family_money", "fr", "", "Bonjour, je vous confirme l'envoi de 1 500 DH par Wafacash. Code de retrait : 4471. Bonne réception."),
(L, "family_money", "dar_ar", "", "خويا الله يخليك إلا قدرتي سلفني 300 درهم حتى للشهر الجاي، ضاقت بيا شوية"),
(L, "transport", "en", "Careem", "Your Careem ride receipt: 34.50 MAD. Thanks for riding with us!"),
(L, "promo", "fr", "MARJANE", "Marjane : jusqu'à -40% sur les fournitures scolaires. Offre valable en magasin jusqu'au 15/10."),
(L, "chat", "dar_lat", "", "drari match dyal lmontakhab lyoum m3a 20h, ntla9aw f l9ahwa?"),
(L, "school", "msa", "", "تهنئة: يتقدم مدير المؤسسة بأحر التهاني لجميع التلاميذ الناجحين."),
(L, "school", "fr", "", "ENIAD Berkane : le planning des examens du S1 est disponible sur la plateforme. Bonne chance !"),
(L, "chat", "dar_ar", "", "عافاك صيفط ليا الصور ديال العرس فالواتساب"),
(L, "telecom", "fr", "Orange", "Votre facture Orange du mois de septembre (149 DH) est disponible dans votre Espace Client sur orange.ma"),
(L, "appointment", "en", "", "Reminder: your dentist appointment is tomorrow at 9:30. Reply YES to confirm."),
(L, "chat", "dar_lat", "", "rbe7t f l concours dyal l code f ENIAD!! 🎉 l prix 3000dh"),
(L, "gov", "fr", "", "Bonjour Madame, votre dossier CNSS est complet. Le remboursement sera versé sous 10 jours ouvrables."),
(L, "bank_notice", "msa", "CDG", "صندوق الإيداع والتدبير: نشكركم على ثقتكم."),
(L, "warning", "dar_ar", "", "حضيو راسكم، شي واحد كيدير راسو من البنك وكيطلب الكود. حتى بنكة ما كتطلب الكود!"),
(L, "warning", "fr", "", "Attention : ne communiquez jamais votre code secret, même à un employé de la banque. Votre banque."),
(L, "chat", "dar_lat", "", "salam, chno rayk nmchiw l Saïdia had weekend? kayn promo f l'hôtel 3la booking.com"),
(L, "marketplace", "en", "", "Hi! I'm interested in your car on Avito. Is the price negotiable? Can I see it on Saturday?"),
(L, "transport", "fr", "ONCF", "Votre réservation ONCF n°AB12CD est confirmée. Présentez votre e-billet à bord. Bon voyage !"),
(L, "chat", "dar_ar", "", "مبروك عليك الطوموبيل الجديدة! الله يجعلها فاتحة خير"),
(L, "bank_notice", "fr", "AWB", "Votre compte a été crédité de 2 300,00 MAD (VIREMENT CNSS). Attijariwafa bank."),
(L, "utility", "msa", "REDAL", "إشعار: سيتم قطع الماء يوم الأحد من الساعة 8 صباحا إلى 2 زوالا بسبب أشغال الصيانة. نعتذر عن الإزعاج. ريضال"),
]

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blind_set.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "campaign", "lang", "sender", "text"])
        for i, (lab, camp, lang, sender, text) in enumerate(ROWS, 1):
            w.writerow([f"B{i:03d}", lab, camp, lang, sender, text])
    n_s = sum(r[0] for r in ROWS)
    print(f"wrote {out}: {len(ROWS)} rows ({n_s} scams, {len(ROWS) - n_s} legit)")
