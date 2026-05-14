# ProcureFlow AI — API Reference

## Autenticación

Todos los endpoints (excepto `/health` y `/auth/login`) requieren header:

```
Authorization: Bearer <access_token>
```

## Auth

### POST /api/v1/auth/login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@procureflow.com", "password": "Admin1234!"}'
```

Response:
```json
{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}
```

### POST /api/v1/auth/refresh

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

## Purchase Orders

### POST /api/v1/purchase-orders

```bash
curl -X POST http://localhost:8000/api/v1/purchase-orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Laptops Q2",
    "description": "MacBook Pro M3",
    "priority": "high",
    "currency": "USD",
    "line_items": [
      {"line_number": 1, "description": "MacBook Pro 14\"", "quantity": "2", "unit_price": "2499.00"}
    ]
  }'
```

### POST /api/v1/approvals/{po_id}/submit

```bash
curl -X POST http://localhost:8000/api/v1/approvals/$PO_ID/submit \
  -H "Authorization: Bearer $TOKEN"
```

### POST /api/v1/approvals/{po_id}/approve

```bash
curl -X POST http://localhost:8000/api/v1/approvals/$PO_ID/approve \
  -H "Authorization: Bearer $APPROVER_TOKEN"
```

### POST /api/v1/approvals/{po_id}/reject

```bash
curl -X POST http://localhost:8000/api/v1/approvals/$PO_ID/reject \
  -H "Authorization: Bearer $APPROVER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Presupuesto insuficiente para Q2"}'
```

## Vendors

### POST /api/v1/vendors (ADMIN/MANAGER)

```bash
curl -X POST http://localhost:8000/api/v1/vendors \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Supplies SA",
    "vendor_code": "TS-001",
    "email": "sales@techsupplies.com",
    "payment_terms": 30,
    "currency": "USD"
  }'
```

## Códigos de Error

| Código | Significado |
|--------|-------------|
| 400 | Bad Request — parámetros inválidos |
| 401 | Unauthorized — token inválido o expirado |
| 403 | Forbidden — sin permisos para esta acción |
| 404 | Not Found — entidad no encontrada |
| 409 | Conflict — recurso ya existe |
| 422 | Unprocessable Entity — violación de regla de negocio |
| 429 | Too Many Requests — rate limit excedido |
| 503 | Service Unavailable — componente crítico caído |
