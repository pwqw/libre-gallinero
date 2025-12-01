#!/data/data/com.termux/files/usr/bin/bash
# Script optimizado para Termux que usa nmap para encontrar ESP8266/ESP32
# Busca dispositivos con puerto 8266 abierto (WebREPL) y actualiza .env

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐔 Buscador ESP8266 con nmap${NC}\n"

# Verificar que nmap esté instalado
if ! command -v nmap &> /dev/null; then
    echo -e "${RED}❌ nmap no está instalado${NC}\n"
    echo -e "${YELLOW}Instalando nmap...${NC}"
    pkg install nmap -y
    echo
fi

# Detectar IP local
LOCAL_IP=$(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)

if [ -z "$LOCAL_IP" ]; then
    echo -e "${RED}❌ No se pudo detectar IP local en wlan0${NC}"
    echo -e "${YELLOW}¿Especificar rango manualmente? (ej: 192.168.1.0/24)${NC}"
    exit 1
fi

# Calcular rango de red (asumir /24)
NETWORK=$(echo "$LOCAL_IP" | cut -d. -f1-3).0/24

echo -e "${BLUE}📡 IP local: ${LOCAL_IP}${NC}"
echo -e "${BLUE}📡 Rango: ${NETWORK}${NC}\n"

echo -e "${BLUE}🔍 Escaneando puerto 8266 (WebREPL)...${NC}"
echo -e "${YELLOW}(Esto puede tardar 30-60 segundos)${NC}\n"

# Escaneo optimizado para Termux:
# -p8266: solo puerto WebREPL
# --open: solo puertos abiertos
# -T4: timing agresivo
# -n: sin resolución DNS (más rápido)
# --host-timeout: timeout por host
NMAP_OUTPUT=$(nmap -p8266 --open -T4 -n --host-timeout 5s "$NETWORK" 2>/dev/null)

# Extraer IPs con puerto abierto
ESP_IPS=$(echo "$NMAP_OUTPUT" | grep "Nmap scan report for" | awk '{print $5}')

if [ -z "$ESP_IPS" ]; then
    echo -e "${RED}❌ No se encontraron dispositivos con puerto 8266 abierto${NC}\n"
    echo -e "${YELLOW}🔧 Verifica:${NC}"
    echo -e "   • ESP8266 está encendido"
    echo -e "   • ESP8266 está en la misma red WiFi"
    echo -e "   • WebREPL está habilitado\n"
    exit 1
fi

# Contar dispositivos encontrados
NUM_ESP=$(echo "$ESP_IPS" | wc -l)

# Mostrar resultados
echo -e "${GREEN}✅ Dispositivos con puerto 8266 abierto (${NUM_ESP}):${NC}\n"
echo "$ESP_IPS" | while read -r ip; do
    echo -e "   • ${GREEN}${ip}${NC}"
done
echo

# Guardar IPs en archivo temporal
ESP_LIST_FILE="/tmp/esp8266_ips.txt"
echo "$ESP_IPS" > "$ESP_LIST_FILE"
echo -e "${BLUE}📄 IPs guardadas en: ${ESP_LIST_FILE}${NC}\n"

# Actualizar .env si hay exactamente 1 dispositivo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

if [ "$NUM_ESP" -eq 1 ]; then
    FIRST_IP=$(echo "$ESP_IPS" | head -1)

    echo -e "${BLUE}📝 Actualizando .env con IP: ${FIRST_IP}${NC}"

    if [ -f "$ENV_FILE" ]; then
        # Actualizar WEBREPL_IP en .env existente
        if grep -q "^WEBREPL_IP=" "$ENV_FILE"; then
            # Reemplazar valor existente
            sed -i "s/^WEBREPL_IP=.*/WEBREPL_IP=$FIRST_IP/" "$ENV_FILE"
            echo -e "${GREEN}✅ .env actualizado: WEBREPL_IP=$FIRST_IP${NC}\n"
        else
            # Agregar línea nueva
            echo "WEBREPL_IP=$FIRST_IP" >> "$ENV_FILE"
            echo -e "${GREEN}✅ .env actualizado: WEBREPL_IP=$FIRST_IP${NC}\n"
        fi
    else
        # Crear .env desde .env.example y actualizar IP
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
            sed -i "s/^WEBREPL_IP=.*/WEBREPL_IP=$FIRST_IP/" "$ENV_FILE"
            echo -e "${GREEN}✅ .env creado y actualizado: WEBREPL_IP=$FIRST_IP${NC}\n"
        else
            echo -e "${YELLOW}⚠️  No se encontró .env.example, creando .env básico${NC}"
            echo "WEBREPL_IP=$FIRST_IP" > "$ENV_FILE"
            echo -e "${GREEN}✅ .env creado: WEBREPL_IP=$FIRST_IP${NC}\n"
        fi
    fi

    echo -e "${BLUE}💡 Para deployar:${NC}"
    echo "   python3 tools/deploy_wifi.py gallinero"
    echo
elif [ "$NUM_ESP" -gt 1 ]; then
    echo -e "${YELLOW}⚠️  Se encontraron múltiples dispositivos${NC}"
    echo -e "${YELLOW}   No se actualizó .env automáticamente${NC}\n"

    echo -e "${BLUE}💡 Para actualizar .env manualmente:${NC}"
    FIRST_IP=$(echo "$ESP_IPS" | head -1)
    echo "   Edita .env y cambia WEBREPL_IP a la IP correcta"
    echo

    echo -e "${BLUE}💡 Para probar WebREPL en cada IP:${NC}"
    echo "$ESP_IPS" | while read -r ip; do
        echo "   python3 tools/find_esp8266.py --test-only $ip"
    done
    echo

    echo -e "${BLUE}💡 Para deployar con IP específica:${NC}"
    echo "   python3 tools/deploy_wifi.py gallinero $FIRST_IP"
    echo
fi
