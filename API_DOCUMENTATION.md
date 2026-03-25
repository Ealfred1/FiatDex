# FiatDex API Documentation

**Base URL:** `http://localhost:8000`  
**API Version:** v1 (`/api/v1`)  
**Content-Type:** `application/json`

---

## Authentication Flow

### 1. Sign Up (Email Registration)

**URL:** `POST /api/v1/auth/signup`

**Request Payload:**
```json
{
  "email": "testuser@fiatdex.app",
  "password": "TestPass1",
  "full_name": "Test User",
  "country": "NG"
}
```

**Success Response (200):**
```json
{
  "message": "OTP sent to your email",
  "email": "testuser@fiatdex.app"
}
```

**Validation Error (422):**
```json
{
  "detail": "Input should be a valid email address"
}
```

---

### 2. Verify OTP

**URL:** `POST /api/v1/auth/verify-otp`

**Request Payload:**
```json
{
  "email": "testuser@fiatdex.app",
  "otp_code": "709459"
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "303c28c8-847a-4ff8-8d0e-baa3cb08fe4e",
    "email": "testuser@fiatdex.app",
    "full_name": "Test User",
    "country": "NG",
    "wallet_address": null,
    "auth_method": "email",
    "email_verified": true,
    "preferred_currency": "USD",
    "account_balance": "0E-8",
    "created_at": "2026-03-25T20:34:29.553540Z"
  }
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid or expired OTP"
}
```

---

### 3. Login (Email)

**URL:** `POST /api/v1/auth/login`

**Request Payload:**
```json
{
  "email": "testuser@fiatdex.app",
  "password": "TestPass1"
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "303c28c8-847a-4ff8-8d0e-baa3cb08fe4e",
    "email": "testuser@fiatdex.app",
    "full_name": "Test User",
    "country": "NG",
    "wallet_address": null,
    "auth_method": "email",
    "email_verified": true,
    "preferred_currency": "NGN",
    "account_balance": "0E-8",
    "created_at": "2026-03-25T20:34:29.553540Z"
  }
}
```

**Error Response (401):**
```json
{
  "detail": "Invalid credentials"
}
```

---

### 4. Resend OTP

**URL:** `POST /api/v1/auth/resend-otp`

**Request Payload:**
```json
{
  "email": "testuser@fiatdex.app"
}
```

**Success Response (200):**
```json
{
  "message": "Verification code resent"
}
```

---

### 5. Forgot Password

**URL:** `POST /api/v1/auth/forgot-password`

**Request Payload:**
```json
{
  "email": "testuser@fiatdex.app"
}
```

**Response (200):** (Always returns success to prevent email enumeration)
```json
{
  "message": "If the email exists, a reset link has been sent"
}
```

---

### 6. Get Current User Profile

**URL:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "id": "303c28c8-847a-4ff8-8d0e-baa3cb08fe4e",
  "email": "testuser@fiatdex.app",
  "full_name": "Test User",
  "country": "NG",
  "wallet_address": null,
  "auth_method": "email",
  "email_verified": true,
  "preferred_currency": "USD",
  "account_balance": "0E-8",
  "created_at": "2026-03-25T20:34:29.553540Z"
}
```

**Error Response (401):**
```json
{
  "detail": "Could not validate credentials"
}
```

---

## Wallet Endpoints

### 7. Request Wallet Authentication Nonce

**URL:** `POST /api/v1/wallet/auth/nonce`

**Request Payload:**
```json
{
  "wallet_address": "inj1test123456789abcdefghijklmnopqrstuvwxyz",
  "wallet_type": "keplr"
}
```

**Success Response (200):**
```json
{
  "nonce": "9f08332d-2868-4de7-b9ed-5defdc618fcb",
  "message": "FiatDex Authentication\nAddress: inj1test123456789abcdefghijklmnopqrstuvwxyz\nNonce: 9f08332d-2868-4de7-b9ed-5defdc618fcb\nTimestamp: 2026-03-25T20:34:59.943162+00:00",
  "expires_in": 300
}
```

---

### 8. Get Wallet Balance

**URL:** `GET /api/v1/wallet/balance`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "total_value_usd": "0",
  "total_value_local": "0",
  "local_currency": "USD",
  "tokens": []
}
```

---

### 9. Update User Preferences

**URL:** `PUT /api/v1/wallet/preferences`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `currency` (optional): NGN, GHS, KES, ZAR, USD

**Request Example:**
```
PUT /api/v1/wallet/preferences?currency=NGN
```

**Success Response (200):**
```json
{
  "wallet_address": null,
  "wallet_type": null,
  "preferred_currency": "NGN",
  "is_active": true
}
```

---

## Portfolio Endpoints

### 10. Get Portfolio Overview

**URL:** `GET /api/v1/portfolio`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "total_portfolio_value_usd": "0E-8",
  "account_balance_usd": "0E-8",
  "holdings": [],
  "on_chain_balances": [],
  "local_currency": "USD"
}
```

---

### 11. Get Transaction History

**URL:** `GET /api/v1/portfolio/transactions`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
[]
```

---

## Funding Endpoints

### 12. Get Account Balance

**URL:** `GET /api/v1/funding/balance`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "account_balance": "0E-8",
  "currency": "USD"
}
```

---

### 13. Get Funding History

**URL:** `GET /api/v1/funding/history`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
[]
```

---

### 14. Initiate Funding

**URL:** `POST /api/v1/funding/initiate`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Payload:**
```json
{
  "amount": 5000,
  "currency": "NGN"
}
```

**Success Response (200):**
```json
{
  "authorization_url": "https://checkout.paystack.com/...",
  "access_code": "...",
  "reference": "..."
}
```

**Error Response (500):**
```json
{
  "detail": "Failed to initialize Paystack transaction"
}
```

---

## Alert Endpoints

### 15. Create Price Alert

**URL:** `POST /api/v1/alerts`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Payload:**
```json
{
  "token_denom": "inj",
  "token_symbol": "INJ",
  "target_price_usd": 50.0,
  "condition": "above"
}
```

**Success Response (200):**
```json
{
  "id": "4076661c-e25c-41b5-a149-8bf0a1b02b92",
  "token_denom": "inj",
  "token_symbol": "INJ",
  "target_price_usd": 50.0,
  "condition": "above",
  "is_active": true,
  "created_at": "2026-03-25T20:35:09.661681Z"
}
```

---

### 16. Get Watchlist

**URL:** `GET /api/v1/alerts/watchlist`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
[]
```

---

### 17. Add to Watchlist

**URL:** `POST /api/v1/alerts/watchlist`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Payload:**
```json
{
  "token_denom": "inj",
  "token_symbol": "INJ"
}
```

**Success Response (200):**
```json
{
  "token_denom": "inj",
  "token_symbol": "INJ",
  "added_at": "2026-03-25T20:35:09.810535Z"
}
```

---

### 18. Remove from Watchlist

**URL:** `DELETE /api/v1/alerts/watchlist/{token_denom}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Example:** `DELETE /api/v1/alerts/watchlist/inj`

**Success Response (200):**
```json
{
  "status": "ok"
}
```

---

## Onramp Endpoints

### 19. Get Onramp Quote

**URL:** `POST /api/v1/onramp/quote`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Payload:**
```json
{
  "fiat_amount": 5000,
  "fiat_currency": "NGN",
  "target_market_id": "inj",
  "payment_method": "card"
}
```

**Success Response (200):**
```json
{
  "provider": "transak",
  "fiat_amount": 5000,
  "fiat_currency": "NGN",
  "estimated_inj_amount": "...",
  "estimated_target_amount": "...",
  "fees": "...",
  "expires_at": "..."
}
```

**Error Response (503):**
```json
{
  "detail": "Onramp providers currently unavailable"
}
```

---

## Sell Endpoints

### 20. Get Sell Quote

**URL:** `POST /api/v1/sell/quote`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Payload:**
```json
{
  "token_denom": "inj",
  "amount": 10
}
```

**Success Response (200):**
```json
{
  "token_denom": "inj",
  "token_symbol": "INJ",
  "amount_to_sell": "10.00000000",
  "estimated_usd_received": "98.00000000",
  "exchange_rate": "10.000000",
  "fee_usd": "2.00000000",
  "expires_at": "2026-03-25T20:36:00.000000+00:00"
}
```

**Error Response (400):**
```json
{
  "detail": "Insufficient holdings"
}
```

---

## Token Endpoints

### 21. Get Token Feed

**URL:** `GET /api/v1/tokens`

**Query Parameters:**
- `limit` (optional): 1-100, default 20
- `offset` (optional): default 0
- `sort_by` (optional): volume, gainers, losers, newest
- `search` (optional): search by token name/symbol
- `currency` (optional): NGN, GHS, KES, ZAR, USD

**Example:** `GET /api/v1/tokens?limit=5&sort_by=gainers`

**Success Response (200):**
```json
{
  "tokens": [],
  "total": 0,
  "has_more": false
}
```

**Note:** Returns empty when Injective network is not connected.

---

## Health Endpoints

### 22. Health Check

**URL:** `GET /health`

**Success Response (200):**
```json
{
  "status": "ok",
  "environment": "development"
}
```

---

### 23. Root Endpoint

**URL:** `GET /`

**Success Response (200):**
```json
{
  "message": "Welcome to FiatDex API — Injective Africa Buildathon 2026"
}
```

---

## Summary Table

| # | Endpoint | Method | Auth Required | Status |
|---|----------|--------|---------------|--------|
| 1 | `/api/v1/auth/signup` | POST | No | ✅ |
| 2 | `/api/v1/auth/verify-otp` | POST | No | ✅ |
| 3 | `/api/v1/auth/login` | POST | No | ✅ |
| 4 | `/api/v1/auth/resend-otp` | POST | No | ✅ |
| 5 | `/api/v1/auth/forgot-password` | POST | No | ✅ |
| 6 | `/api/v1/auth/me` | GET | Yes | ✅ |
| 7 | `/api/v1/wallet/auth/nonce` | POST | No | ✅ |
| 8 | `/api/v1/wallet/balance` | GET | Yes | ✅ |
| 9 | `/api/v1/wallet/preferences` | PUT | Yes | ✅ |
| 10 | `/api/v1/portfolio` | GET | Yes | ✅ |
| 11 | `/api/v1/portfolio/transactions` | GET | Yes | ✅ |
| 12 | `/api/v1/funding/balance` | GET | Yes | ✅ |
| 13 | `/api/v1/funding/history` | GET | Yes | ✅ |
| 14 | `/api/v1/funding/initiate` | POST | Yes | ⚠️ |
| 15 | `/api/v1/alerts` | POST | Yes | ✅ |
| 16 | `/api/v1/alerts/watchlist` | GET | Yes | ✅ |
| 17 | `/api/v1/alerts/watchlist` | POST | Yes | ✅ |
| 18 | `/api/v1/alerts/watchlist/{token}` | DELETE | Yes | ✅ |
| 19 | `/api/v1/onramp/quote` | POST | Yes | ⚠️ |
| 20 | `/api/v1/sell/quote` | POST | Yes | ✅ |
| 21 | `/api/v1/tokens` | GET | No | ⚠️ |
| 22 | `/health` | GET | No | ✅ |
| 23 | `/` | GET | No | ✅ |

**Legend:**
- ✅ = Working
- ⚠️ = Needs external API keys (Paystack, Transak, Kado, Injective)
