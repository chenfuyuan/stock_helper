# Stock Helper

Enterprise-grade Python DDD Project Skeleton.

## Project Structure

The project follows Domain-Driven Design (DDD) principles with a layered architecture:

```
stock_helper/
├── app/
│   ├── application/        # Application Layer (Use Cases, DTOs)
│   ├── core/               # Core Config & Utilities
│   ├── domain/             # Domain Layer (Entities, Interfaces)
│   ├── infrastructure/     # Infrastructure Layer (DB, Repositories Impl)
│   └── presentation/       # Presentation Layer (API, Middlewares)
├── alembic/                # Database Migrations
├── tests/                  # Test Suite
├── deploy/                 # Deployment Configurations
└── scripts/                # Utility Scripts
```

## Tech Stack

- **Web Framework**: FastAPI (ASGI)
- **Database**: PostgreSQL + SQLAlchemy (Async)
- **Migrations**: Alembic
- **Dependency Management**: Conda + Pip
- **Containerization**: Docker + Docker Compose
- **Logging**: Loguru
- **Testing**: Pytest

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Conda (Optional)

### Installation

1. Create environment:
   ```bash
   make install
   ```

2. Activate environment:
   ```bash
   conda activate stock_helper
   ```

3. Run locally:
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

### Development

- **Linting**: `make lint`
- **Formatting**: `make format`

## API Documentation

Once running, access:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## License

MIT
