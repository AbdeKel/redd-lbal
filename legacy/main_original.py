import os
import sys
from typing import Optional, Tuple
from contextlib import asynccontextmanager
from urllib.parse import urlparse

# Assure l'encodage UTF-8 sur Windows pour les print()
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import joblib
import Levenshtein
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Chemins des modèles et répertoires
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, "webapp")
TEXT_MODEL_PATH = os.path.join(BASE_DIR, "text_model.joblib")
TEXT_VEC_PATH = os.path.join(BASE_DIR, "text_vectorizer.joblib")
URL_MODEL_PATH = os.path.join(BASE_DIR, "url_model.joblib")
URL_VEC_PATH = os.path.join(BASE_DIR, "url_vectorizer.joblib")

# Dictionnaire global pour stocker les modèles en mémoire
models = {}

# Liste Blanche prioritaire (Whitelist) de sites officiels vérifiés
WHITELIST = [
    'instagram.com',
    'www.instagram.com',
    'google.com',
    'www.google.com',
    'facebook.com',
    'wikipedia.org',
    'github.com',
    'ump.ma',
    'www.ump.ma',
]

# Liste Python de domaines de confiance très ciblés par les arnaques et le phishing
TRUSTED_DOMAINS = [
    "paypal.com",
    "microsoft.com",
    "netflix.com",
    "amazon.com",
    "apple.com",
    "facebook.com",
    "google.com",
    "instagram.com",
    "github.com",
    "ump.ma",
    "ameli.fr",
    "impots.gouv.fr",
    "labanquepostale.fr",
    "credit-agricole.fr",
    "bnpparibas.com",
    "societegenerale.com",
    "orange.fr",
    "sfr.fr",
    "laposte.fr",
    "wikipedia.org",
]


def extract_strict_domain(url: str) -> str:
    """
    Extrait uniquement le nom de domaine strict (ex: 'google.com')
    en utilisant urllib.parse.urlparse et en retirant les protocoles et 'www.'
    """
    url_clean = url.strip().lower()
    
    # S'assurer d'avoir un schéma pour que urlparse peuple correctement netloc
    if not url_clean.startswith(("http://", "https://")):
        url_clean = "https://" + url_clean

    parsed = urlparse(url_clean)
    domain = parsed.netloc or parsed.path.split("/")[0]

    # Supprime les identifiants éventuels (ex: user:pass@domain.com)
    if "@" in domain:
        domain = domain.split("@")[-1]

    # Supprime le port éventuel (ex: domain.com:8080)
    domain = domain.split(":")[0]

    # Retire 'www.' si présent
    if domain.startswith("www."):
        domain = domain[4:]

    return domain.strip()


def check_heuristic_protection(domain: str) -> Tuple[bool, bool, Optional[str], Optional[str]]:
    """
    Fonction de protection heuristique sur le domaine strict :
    1. Vérification si domaine de confiance certifié (exact match)
    2. Règle 1 (Homoglyphe) : Si le domaine contient 'xn--'
    3. Règle 2 (Typosquatting) : Distance de Levenshtein de 1 ou 2 avec un domaine de confiance (non exacte)

    Retourne: (is_danger, is_trusted_exact, motif, trusted_domain)
    """
    if not domain:
        return False, False, None, None

    # Vérification 1 : Correspondance exacte avec un domaine de confiance
    for trusted in TRUSTED_DOMAINS:
        if domain == trusted or domain.endswith("." + trusted):
            return False, True, "Correspondance exacte avec domaine officiel de confiance", trusted

    # Règle 1 : Détection d'homoglyphes (Punycode 'xn--')
    if "xn--" in domain:
        return True, False, "Attaque par homoglyphe détectée (présence de 'xn--')", None

    # Règle 2 : Détection de typosquatting (Distance Levenshtein de 1 ou 2)
    for trusted in TRUSTED_DOMAINS:
        dist = Levenshtein.distance(domain, trusted)
        if dist in (1, 2):
            return True, False, f"Typosquatting détecté : imite '{trusted}' (distance: {dist})", trusted

    return False, False, None, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge les modèles et vectoriseurs en mémoire au démarrage de l'application."""
    print("[-] Chargement des modèles et vectoriseurs en mémoire...")
    try:
        models["text_model"] = joblib.load(TEXT_MODEL_PATH)
        models["text_vectorizer"] = joblib.load(TEXT_VEC_PATH)
        models["url_model"] = joblib.load(URL_MODEL_PATH)
        models["url_vectorizer"] = joblib.load(URL_VEC_PATH)
        print("[OK] Tous les modèles sont chargés avec succès.")
    except Exception as e:
        print(f"[ERREUR] Échec du chargement des modèles : {e}")
        raise e
    yield
    models.clear()


# Initialisation de l'application FastAPI
app = FastAPI(
    title="API de Détection de Fraude et Phishing",
    description="API permettant d'analyser les messages suspects et les URLs avec protection heuristique et Machine Learning.",
    version="1.2.0",
    lifespan=lifespan,
)

# Configuration du middleware CORS pour autoriser toutes les origines
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modèle Pydantic pour la requête
class AnalyzeRequest(BaseModel):
    message: Optional[str] = Field(
        None,
        description="Le texte du message (SMS ou e-mail) à analyser",
        example="Félicitations, vous avez gagné un chèque de 1000€ ! Cliquez ici pour réclamer.",
    )
    lien: Optional[str] = Field(
        None,
        description="L'URL à analyser",
        example="http://secure-login-banque-update.com/verify",
    )


# Modèle Pydantic pour la réponse
class AnalyzeResponse(BaseModel):
    statut: str = Field(..., description="'Sécurisé' ou 'Danger'")
    probabilite: float = Field(..., description="Probabilité d'arnaque (entre 0.0 et 1.0)")
    message_alerte: Optional[str] = Field(
        None,
        description="Message d'alerte spécifique pour personne âgée",
    )
    details: Optional[dict] = Field(None, description="Détails de l'analyse")


def analyze_link(lien: str) -> Tuple[str, float, Optional[str], dict]:
    """
    Fonction d'analyse des liens :
    1. Règle prioritaire Liste Blanche (WHITELIST)
    2. Règles heuristiques (Homoglyphe & Typosquatting Levenshtein)
    3. Modèle Machine Learning URL
    """
    domain = extract_strict_domain(lien)

    # 1. Règle prioritaire : Liste Blanche (WHITELIST)
    # Si le domaine extrait correspond exactement à un élément de la WHITELIST,
    # retourne immédiatement le statut 'Sécurisé' (probabilité 0.0) avec le message 'Site officiel vérifié'.
    # Si le domaine est dans la Whitelist, il ne doit PAS passer par le calcul de Levenshtein ni par le modèle ML.
    if domain in WHITELIST or f"www.{domain}" in WHITELIST:
        details_lien = {
            "url": lien,
            "domaine": domain,
            "statut": "Sécurisé",
            "probabilite_arnaque": 0.0,
            "message": "Site officiel vérifié",
            "source": "Liste Blanche prioritaire (WHITELIST)",
        }
        return "Sécurisé", 0.0, "Site officiel vérifié", details_lien

    # 2. Vérification des règles heuristiques (Homoglyphe & Typosquatting Levenshtein)
    is_danger, is_trusted_exact, motif, trusted_ref = check_heuristic_protection(domain)

    if is_trusted_exact:
        details_lien = {
            "url": lien,
            "domaine": domain,
            "statut": "Sécurisé",
            "probabilite_arnaque": 0.0,
            "source": f"Site officiel certifié ({trusted_ref})",
        }
        return "Sécurisé", 0.0, None, details_lien

    elif is_danger:
        alert_msg = "Attention, ce lien imite un site officiel pour vous tromper"
        details_lien = {
            "url": lien,
            "domaine": domain,
            "regle_heuristique": motif,
            "message": alert_msg,
            "probabilite_arnaque": 1.0,
            "statut": "Danger",
            "bloque_par": "Heuristique",
        }
        return "Danger", 1.0, alert_msg, details_lien

    else:
        # 3. Modèle Machine Learning URL
        url_vec = models.get("url_vectorizer")
        url_model = models.get("url_model")
        if not url_vec or not url_model:
            raise HTTPException(status_code=500, detail="Modèle d'URL non chargé.")

        url_clean_for_ml = lien.replace("https://", "").replace("http://", "").replace("www.", "")
        X_url = url_vec.transform([url_clean_for_ml])
        prob_lien = float(url_model.predict_proba(X_url)[0][1])
        statut_ml = "Danger" if prob_lien >= 0.5 else "Sécurisé"
        details_lien = {
            "url": lien,
            "domaine": domain,
            "probabilite_arnaque": round(prob_lien, 4),
            "statut": statut_ml,
            "bloque_par": "Modèle ML" if statut_ml == "Danger" else None,
            "source": "Modèle Machine Learning",
        }
        return statut_ml, prob_lien, None, details_lien


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "models_loaded": len(models) == 4,
        "trusted_domains_count": len(TRUSTED_DOMAINS),
        "whitelist_count": len(WHITELIST),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest):
    message = payload.message.strip() if payload.message else None
    lien = payload.lien.strip() if payload.lien else None

    # Vérification qu'au moins un des deux champs est renseigné
    if not message and not lien:
        raise HTTPException(
            status_code=400,
            detail="Veuillez fournir au moins un champ : 'message' ou 'lien'.",
        )

    prob_message = None
    prob_lien = None
    heuristic_alert_message = None
    details = {}

    # Analyse du message texte avec le modèle Machine Learning
    if message:
        print("\n" + "-" * 55)
        print(f"[ANALYSE TEXTE] Début analyse du message...")
        text_vec = models.get("text_vectorizer")
        text_model = models.get("text_model")
        if not text_vec or not text_model:
            raise HTTPException(status_code=500, detail="Modèle de texte non chargé.")

        X_text = text_vec.transform([message])
        prob_message = float(text_model.predict_proba(X_text)[0][1])
        statut_text = "Danger" if prob_message >= 0.5 else "Sécurisé"
        print(f"[RÉSULTAT TEXTE ML] Probabilité d'arnaque : {prob_message:.4f} ({prob_message * 100:.2f}%) -> {statut_text}")
        print("-" * 55)

        details["message"] = {
            "texte": message,
            "probabilite_arnaque": round(prob_message, 4),
            "statut": statut_text,
        }

    # Analyse du lien : protection heuristique prioritaire puis modèle ML
    if lien:
        print("\n" + "=" * 60)
        print(f"[ANALYSE LIEN] URL reçue : '{lien}'")
        
        # Extraction stricte du nom de domaine via urllib.parse.urlparse
        domain = extract_strict_domain(lien)
        print(f"[EXTRACTION NOM DE DOMAINE] Domaine strict extrait : '{domain}'")

        # RÈGLE 1 PRIORITAIRE : VÉRIFICATION LISTE BLANCHE (WHITELIST)
        # Si le domaine extrait correspond exactement à un élément de la WHITELIST,
        # retourne immédiatement le statut 'Sécurisé' (probabilité 0.0) avec le message 'Site officiel vérifié'.
        # Si le domaine est dans la Whitelist, il ne doit PAS passer par le calcul de Levenshtein ni par le modèle ML.
        if domain in WHITELIST or f"www.{domain}" in WHITELIST:
            print(f"[LISTE BLANCHE PRIORITAIRE] Le domaine '{domain}' correspond exactement à un élément de la WHITELIST.")
            print(f" -> BYPASS : Ni calcul de Levenshtein ni modèle ML ne sont exécutés.")
            print(f" -> RETOUR IMMÉDIAT : Statut 'Sécurisé' (Probabilité : 0.0), Message : 'Site officiel vérifié'")
            print("=" * 60)
            details["lien"] = {
                "url": lien,
                "domaine": domain,
                "statut": "Sécurisé",
                "probabilite_arnaque": 0.0,
                "message": "Site officiel vérifié",
                "source": "Liste Blanche prioritaire (WHITELIST)",
            }
            return AnalyzeResponse(
                statut="Sécurisé",
                probabilite=0.0,
                message_alerte="Site officiel vérifié",
                details=details,
            )

        # 1. Vérification des règles heuristiques
        is_danger, is_trusted_exact, motif, trusted_ref = check_heuristic_protection(domain)

        if is_trusted_exact:
            # Correspondance exacte avec un domaine de confiance (ex: google.com, paypal.com)
            print(f"[SITE OFFICIEL CERTIFIÉ] Le domaine '{domain}' est une correspondance exacte avec '{trusted_ref}'")
            print(f" -> BLOCAGE : AUCUN (Site officiel reconnu)")
            print(f" -> RÉSULTAT : SÉCURISÉ (Probabilité : 0.0)")
            prob_lien = 0.0
            details["lien"] = {
                "url": lien,
                "domaine": domain,
                "statut": "Sécurisé",
                "probabilite_arnaque": 0.0,
                "source": f"Site officiel certifié ({trusted_ref})",
            }

        elif is_danger:
            # Échec à l'une des règles heuristiques (Homoglyphe ou Typosquatting)
            heuristic_alert_message = "Attention, ce lien imite un site officiel pour vous tromper"
            prob_lien = 1.0
            print(f"[BLOCAGE PAR HEURISTIQUE] [!] {motif}")
            print(f" -> RESULTAT : DANGER IMMEDIAT (Probabilite: 100%)")
            print(f" -> ALERTE SENIORS : '{heuristic_alert_message}'")
            print("=" * 60)

            details["lien"] = {
                "url": lien,
                "domaine": domain,
                "regle_heuristique": motif,
                "message": heuristic_alert_message,
                "probabilite_arnaque": 1.0,
                "statut": "Danger",
                "bloque_par": "Heuristique",
            }

        else:
            # Le lien passe les règles heuristiques avec succès -> Analyse par le modèle ML
            print(f"[REGLES HEURISTIQUES VALIDEES] Le domaine '{domain}' n'est ni homoglyphe ni typosquatting.")
            print(f"[ANALYSE PAR MODELE ML] Envoi au classifieur url_model.joblib...")

            url_vec = models.get("url_vectorizer")
            url_model = models.get("url_model")
            if not url_vec or not url_model:
                raise HTTPException(status_code=500, detail="Modèle d'URL non chargé.")

            # Pour une prédiction équitable du modèle entraîné sans le biais des préfixes de protocoles
            url_clean_for_ml = lien.replace("https://", "").replace("http://", "").replace("www.", "")
            X_url = url_vec.transform([url_clean_for_ml])
            prob_lien = float(url_model.predict_proba(X_url)[0][1])
            statut_ml = "Danger" if prob_lien >= 0.5 else "Sécurisé"

            if statut_ml == "Danger":
                print(f"[BLOCAGE PAR MODELE ML] [!] Detecte comme malveillant par url_model.joblib")
            else:
                print(f"[VALIDATION PAR MODELE ML] [OK] Declare legitime par url_model.joblib")

            print(f" -> Probabilite d'arnaque ML : {prob_lien:.4f} ({prob_lien * 100:.2f}%) -> Statut : {statut_ml}")
            print("=" * 60)

            details["lien"] = {
                "url": lien,
                "domaine": domain,
                "probabilite_arnaque": round(prob_lien, 4),
                "statut": statut_ml,
                "bloque_par": "Modèle ML" if statut_ml == "Danger" else None,
                "source": "Modèle Machine Learning",
            }

    # Détermination du statut global et de la probabilité finale
    if prob_message is not None and prob_lien is not None:
        final_prob = max(prob_message, prob_lien)
    elif prob_message is not None:
        final_prob = prob_message
    else:
        final_prob = prob_lien

    statut_global = "Danger" if final_prob >= 0.5 else "Sécurisé"

    return AnalyzeResponse(
        statut=statut_global,
        probabilite=round(final_prob, 4),
        message_alerte=heuristic_alert_message,
        details=details,
    )


# Montage des fichiers statiques de la webapp (index.html, style.css, app.js)
if os.path.exists(WEBAPP_DIR):
    app.mount("/", StaticFiles(directory=WEBAPP_DIR, html=True), name="webapp")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
