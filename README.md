# Stock Helper

Enterprise-grade Python DDD Project Skeleton for Stock Market Data Analysis.

## Project Structure

The project follows Domain-Driven Design (DDD) principles with a layered architecture:

```
stock_helper/
├── src/
│   ├── api/                # API Routes & Middlewares
│   ├── modules/            # Business Modules
│   │   └── market_data/    # Market Data Module
│   │       ├── application/    # Application Layer (Use Cases, DTOs)
│   │       ├── domain/         # Domain Layer (Entities, Interfaces)
│   │       ├── infrastructure/ # Infrastructure Layer (DB, Repositories Impl, External APIs)
│   │       └── presentation/   # Presentation Layer (API Endpoints)
│   ├── shared/             # Shared Kernel (Config, Base Classes, Utilities)
│   └── main.py             # Application Entrypoint
├── alembic/                # Database Migrations
├── docs/                   # Documentation
├── tests/                  # Test Suite
└── scripts/                # Utility Scripts
```

## Tech Stack

- **Web Framework**: FastAPI (ASGI)
- **Database**: PostgreSQL + SQLAlchemy (Async)
- **Migrations**: Alembic
- **Scheduler**: APScheduler (AsyncIO)
- **Dependency Management**: Conda + Pip
- **Containerization**: Docker + Docker Compose
- **Logging**: Loguru
- **Testing**: Pytest

## Core Features

- **Stock Basic Info**: Sync and manage stock basic information (symbol, name, industry, etc.).
- **Daily Quotations**: Sync historical and daily incremental stock market data.
- **Financial Data**: Sync stock financial indicators and reports.
- **Task Scheduling**: Built-in scheduler for automated data synchronization.

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Conda (Optional)
- Tushare Token (Set in `.env`)

### Installation

1. Create environment:
   ```bash
   make install
   ```

2. Activate environment:
   ```bash
   conda activate stock_helper
   ```

3. Configure Environment Variables:
   Copy `.env.example` to `.env` and fill in your database credentials and Tushare token.

4. Run locally:
   ```bash
   make run
   ```

### Running with Docker

```bash
docker-compose up --build
```

### Testing

```bash
make test
```

## API Documentation

Once running, access:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Task Scheduler Management

The project includes a powerful scheduler API to manage background jobs.

- **Check Status**: `GET /api/v1/scheduler/status`
- **Trigger Job Immediately**: `POST /api/v1/scheduler/jobs/{job_id}/trigger`
- **Start Interval Job**: `POST /api/v1/scheduler/jobs/{job_id}/start`
- **Schedule Cron Job**: `POST /api/v1/scheduler/jobs/{job_id}/schedule`
- **Stop Job**: `POST /api/v1/scheduler/jobs/{job_id}/stop`

Available Jobs:
- `sync_daily_history`: Sync all historical daily data (supports resume from breakpoint).
- `sync_daily_by_date`: Sync daily data for a specific date (default: today).
- `sync_history_finance`: Sync historical financial data.

## License

MIT
