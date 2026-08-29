#!/usr/bin/env bash
set -euo pipefail

# Xray config and Reality parameters.
CONFIG="/etc/xray/config.json"
XRAY_SERVICE="xray"

# CHANGE THESE VALUES TO MATCH YOUR SERVER.
DOMAIN="YOUR_DOMAIN"
PORT="443"
SNI="www.cloudflare.com"
PUBLIC_KEY="YOUR_REALITY_PUBLIC_KEY"
SHORT_ID="YOUR_SHORT_ID"

UUID="${1:?UUID required}"
EMAIL="${2:?EMAIL required}"

command -v jq >/dev/null 2>&1 || {
  echo "jq is required" >&2
  exit 1
}

test -f "$CONFIG" || {
  echo "Xray config not found: $CONFIG" >&2
  exit 1
}

BACKUP="${CONFIG}.bak.$(date +%s)"
cp "$CONFIG" "$BACKUP"

# Add client to inbound with tag vless-reality.
TMP="$(mktemp)"

jq --arg id "$UUID" --arg email "$EMAIL" '
  .inbounds |= map(
    if .tag == "vless-reality" and .protocol == "vless"
    then
      .settings.clients = ((.settings.clients // []) + [{
        "id": $id,
        "email": $email,
        "flow": "xtls-rprx-vision"
      }])
    else .
    end
  )
' "$CONFIG" > "$TMP"

mv "$TMP" "$CONFIG"

# Validate before restart.
xray run -test -config "$CONFIG"

systemctl restart "$XRAY_SERVICE"

# The Telegram bot receives this JSON.
jq -n \
  --arg uuid "$UUID" \
  --arg email "$EMAIL" \
  --arg domain "$DOMAIN" \
  --arg port "$PORT" \
  --arg sni "$SNI" \
  --arg pbk "$PUBLIC_KEY" \
  --arg sid "$SHORT_ID" \
  '{
    vless_url:
      ("vless://" + $uuid + "@" + $domain + ":" + $port
       + "?type=tcp"
       + "&security=reality"
       + "&pbk=" + $pbk
       + "&fp=chrome"
       + "&sni=" + $sni
       + "&sid=" + $sid
       + "&flow=xtls-rprx-vision"
       + "&encryption=none"
       + "#"+$email)
  }'
