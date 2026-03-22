# FiatDex Backend — Injective Africa Buildathon 2026

FiatDex is a mobile-first DEX explorer and fiat onramp built natively on the Injective blockchain, specifically designed for the African market (Nigeria, Ghana, Kenya, South Africa).

## Features

- **Token Discovery**: Live feed of Injective ecosystem tokens with 24h market data.
- **Fiat Onramp**: Native integration with Transak and Kado for NGN, GHS, KES, and ZAR.
- **Automated Swaps**: Instant INJ → Target Token execution after fiat purchase.
- **Non-Custodial Auth**: Secure login via Keplr or MetaMask signatures.
- **Portfolio Tracking**: Real-time balance and transaction history.
- **Price Alerts**: Personalized push notifications via Expo.

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy (Async)
- **Cache**: Redis for price data and rate limiting
- **Tasks**: Celery with Redis broker for background swaps and alerts
- **Blockchain**: Injective SDK (`pyinjective`)

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Redis (local or via Docker)
- PostgreSQL (local or via Docker)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Ealfred1/FiatDex.git
   cd FiatDex
   ```

2. **Set up environment variables**:
   Copy `.env.example` to `.env` and fill in your keys.
   ```bash
   cp .env.example .env
   ```

3. **Spin up infrastructure**:
   ```bash
   docker-compose up -d
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the API**:
   ```bash
   uvicorn app.main:app --reload
   ```

7. **Start Celery Worker**:
   ```bash
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Testing

Run the test suite using `pytest`:
```bash
python -m pytest
```

## License

MIT
