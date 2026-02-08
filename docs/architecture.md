# Architecture Documentation

## Overview

Stock Helper follows the **Domain-Driven Design (DDD)** principles, structured to ensure separation of concerns, scalability, and maintainability. The application is divided into distinct layers: Presentation, Application, Domain, and Infrastructure.

## Directory Structure

```
src/
├── api/                # API Routes & Middlewares (Global Presentation)
├── modules/            # Business Modules
│   └── market_data/    # Market Data Bounded Context
│       ├── application/    # Application Layer
│       ├── domain/         # Domain Layer
│       ├── infrastructure/ # Infrastructure Layer
│       └── presentation/   # Presentation Layer (Module specific)
├── shared/             # Shared Kernel
└── main.py             # Application Entrypoint
```

## Layers

### 1. Domain Layer (`domain/`)

The heart of the business logic. It contains entities, value objects, domain events, and repository interfaces.

- **Entities**: Objects with identity and lifecycle (e.g., `StockInfo`, `StockDaily`).
- **Repositories (Interfaces)**: Abstractions for data access (e.g., `StockRepository`).
- **Services**: Domain services for logic that doesn't fit into a single entity.
- **Exceptions**: Domain-specific errors.

**Dependencies**: This layer has **no dependencies** on other layers or external frameworks.

### 2. Application Layer (`application/`)

Orchestrates the domain logic to fulfill user use cases.

- **Use Cases**: Specific business actions (e.g., `SyncStocksUseCase`, `GetStockBasicInfo`).
- **DTOs**: Data Transfer Objects to decouple domain entities from external interfaces.
- **Interfaces**: Definitions for services required by the application (e.g., `StockDataProvider`).

**Dependencies**: Depends only on the **Domain Layer**.

### 3. Infrastructure Layer (`infrastructure/`)

Implements the interfaces defined in Domain and Application layers.

- **Persistence**: Database models (SQLAlchemy), repository implementations.
- **Data Sources**: External API clients (e.g., Tushare API integration).
- **Jobs**: Background jobs and workers.

**Dependencies**: Depends on **Domain** and **Application** layers, and external libraries (SQLAlchemy, requests, etc.).

### 4. Presentation Layer (`presentation/` & `src/api/`)

Handles external interactions (HTTP requests).

- **API Endpoints**: FastAPI routers and controllers.
- **Schemas**: Request/Response models (Pydantic).

**Dependencies**: Depends on **Application** layer to execute use cases.

## Key Flows

### Data Synchronization Flow

1. **Trigger**: A scheduled job or API request initiates the sync process.
2. **Application**: `SyncStocksUseCase` is invoked.
3. **Infrastructure (Data Source)**: `TushareService` fetches raw data from the external API.
4. **Domain**: Raw data is converted into Domain Entities (`StockInfo`).
5. **Infrastructure (Persistence)**: `StockRepositoryImpl` saves the entities to the database.

## Shared Kernel (`src/shared/`)

Contains components shared across multiple modules, such as:
- Base classes for Entities and Use Cases.
- Configuration (`config.py`).
- Logging setup.
- Common utilities (e.g., SchedulerService).
