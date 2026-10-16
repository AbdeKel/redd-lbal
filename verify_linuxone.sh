#!/usr/bin/env bash
# ==============================================================================
# Script de vérification automatisée pour ScamShield / Redd Lbal sur LinuxONE
# ==============================================================================

set -o pipefail

# Couleurs ANSI pour l'affichage dans le terminal
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}======================================================================${NC}"
echo -e "${CYAN}${BOLD}     Vérification du déploiement ScamShield sur IBM LinuxONE / s390x    ${NC}"
echo -e "${CYAN}${BOLD}======================================================================${NC}\n"

# ------------------------------------------------------------------------------
# 1. Vérification des dépendances (Docker et Docker Compose)
# ------------------------------------------------------------------------------
echo -e "${BLUE}[1/4] Vérification des dépendances système...${NC}"

# Vérifier la présence de Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Échec : Docker n'est pas installé sur ce serveur.${NC}"
    exit 1
fi

# Vérifier que le démon Docker est bien actif
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Échec : Le service Docker est inactif ou vos permissions sont insuffisantes (sudo/groupe docker).${NC}"
    exit 1
fi
echo -e "  ${GREEN}✔ Docker est installé et actif ($(docker --version | cut -d',' -f1)).${NC}"

# Vérifier Docker Compose (Supporte v2 'docker compose' et v1 'docker-compose')
COMPOSE_CMD=""
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    echo -e "  ${GREEN}✔ Docker Compose (Plugin v2) est disponible.${NC}"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    echo -e "  ${GREEN}✔ Docker Compose (Standalone v1) est disponible.${NC}"
else
    echo -e "${RED}❌ Échec : Docker Compose n'est pas installé sur cette machine.${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Vérification du conteneur et de l'écoute sur le port 8000
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[2/4] Vérification du conteneur de l'API (Port 8000)...${NC}"

# Boucle d'attente active (jusqu'à 15 secondes max) au cas où le conteneur démarre tout juste
PORT_READY=0
for i in {1..15}; do
    if command -v nc &> /dev/null && nc -z 127.0.0.1 8000 2>/dev/null; then
        PORT_READY=1
        break
    elif (echo > /dev/tcp/127.0.0.1/8000) 2>/dev/null; then
        PORT_READY=1
        break
    elif curl -s -m 1 http://localhost:8000/ &> /dev/null; then
        PORT_READY=1
        break
    fi
    sleep 1
done

if [ $PORT_READY -ne 1 ]; then
    echo -e "${RED}❌ Échec : Aucun service n'écoute sur le port 8000.${NC}"
    echo -e "${YELLOW}Conseil : Vérifiez les conteneurs avec 'docker ps' ou les journaux avec '${COMPOSE_CMD} logs'.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✔ Le conteneur de l'API tourne et écoute correctement sur le port 8000.${NC}"

# ------------------------------------------------------------------------------
# 3. Test de l'API (Santé du serveur web Uvicorn)
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[3/4] Test de l'API web (GET http://localhost:8000/)...${NC}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 10 http://localhost:8000/ || echo "000")

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 400 ]; then
    echo -e "  ${GREEN}✔ Le serveur web Uvicorn répond bien (Code HTTP : ${HTTP_CODE}).${NC}"
else
    echo -e "${RED}❌ Échec : La route racine a retourné le code HTTP ${HTTP_CODE}.${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 4. Test du Machine Learning (POST http://localhost:8000/analyze)
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[4/4] Test du Machine Learning Scikit-Learn (POST http://localhost:8000/analyze)...${NC}"

PAYLOAD='{"message": "test", "lien": "http://www.exemple.com"}'

RESPONSE=$(curl -s -m 15 -X POST http://localhost:8000/analyze \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" 2>/dev/null || echo "")

if [ -z "$RESPONSE" ]; then
    echo -e "${RED}❌ Échec : Aucune réponse reçue depuis l'endpoint /analyze.${NC}"
    exit 1
fi

# Validation du format JSON de la réponse
IS_VALID_JSON=0
if command -v jq &> /dev/null; then
    if echo "$RESPONSE" | jq . > /dev/null 2>&1; then
        IS_VALID_JSON=1
    fi
elif [[ "$RESPONSE" =~ ^\{.*\}$ ]]; then
    IS_VALID_JSON=1
fi

if [ $IS_VALID_JSON -eq 1 ]; then
    echo -e "  ${GREEN}✔ Réponse JSON valide reçue avec succès du modèle.${NC}"
    echo -e "\n${GREEN}${BOLD}✅ Succès : Le projet ScamShield est 100% opérationnel sur LinuxONE !${NC}\n"
    exit 0
else
    echo -e "${RED}❌ Échec : La réponse retournée n'est pas un JSON valide :${NC}"
    echo "$RESPONSE"
    exit 1
fi
