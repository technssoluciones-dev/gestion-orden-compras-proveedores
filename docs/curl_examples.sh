#!/usr/bin/env bash
# ProcureFlow AI — Ejemplos curl
# Uso: bash docs/curl_examples.sh

BASE=http://localhost:8000/api/v1

echo "=== 1. Login ==="
RESP=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@procureflow.com","password":"Admin1234!"}')
TOKEN=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token obtenido: ${TOKEN:0:30}..."

echo ""
echo "=== 2. Health ==="
curl -s $BASE/health | python3 -m json.tool

echo ""
echo "=== 3. Crear Proveedor ==="
VENDOR=$(curl -s -X POST $BASE/vendors \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Corp","vendor_code":"ACME-001","email":"info@acme.com","payment_terms":30}')
echo $VENDOR | python3 -m json.tool
VENDOR_ID=$(echo $VENDOR | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo ""
echo "=== 4. Crear Orden de Compra ==="
PO=$(curl -s -X POST $BASE/purchase-orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Laptops Q2\",
    \"priority\": \"high\",
    \"currency\": \"USD\",
    \"vendor_id\": \"$VENDOR_ID\",
    \"line_items\": [
      {\"line_number\": 1, \"description\": \"MacBook Pro\", \"quantity\": \"2\", \"unit_price\": \"2499.00\"}
    ]
  }")
echo $PO | python3 -m json.tool
PO_ID=$(echo $PO | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo ""
echo "=== 5. Enviar a Aprobación ==="
curl -s -X POST $BASE/approvals/$PO_ID/submit \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== 6. Aprobar OC ==="
curl -s -X POST $BASE/approvals/$PO_ID/approve \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "Done."
