# Domain Model Documentation

This document describes the core entities and their relationships within the **Market Data** module.

## Entities

### 1. StockInfo

Represents the basic information of a stock.

- **Source**: `src/modules/market_data/domain/entities/stock_info.py`
- **Key Attributes**:
    - `symbol`: Stock symbol (e.g., "000001").
    - `third_code`: Code used by third-party providers (e.g., "000001.SZ").
    - `name`: Stock name.
    - `area`: Region/Area.
    - `industry`: Industry sector.
    - `market`: Market type (Main Board, GEM, etc.).
    - `list_status`: Listing status (Listed, Delisted, Paused).
    - `list_date`: Date of listing.
    - `is_hs`: Whether it belongs to Northbound/Southbound trading.

### 2. StockDaily

Represents daily market quotation data (OHLCV).

- **Source**: `src/modules/market_data/domain/entities/stock_daily.py`
- **Key Attributes**:
    - `stock_code`: Foreign key to `StockInfo`.
    - `trade_date`: Trading date.
    - `open`, `high`, `low`, `close`: Price data.
    - `pre_close`: Previous closing price.
    - `change`, `pct_chg`: Price change and percentage change.
    - `vol`: Trading volume.
    - `amount`: Trading amount.

### 3. StockFinance

Represents financial indicators and reports.

- **Source**: `src/modules/market_data/domain/entities/stock_finance.py`
- **Key Attributes**:
    - `stock_code`: Foreign key to `StockInfo`.
    - `ann_date`: Announcement date.
    - `end_date`: Reporting period end date.
    - `eps`: Earnings Per Share.
    - `dt_eps`: Diluted EPS.
    - `total_revenue_ps`: Revenue per share.
    - `revenue_ps`: Revenue per share (main business).
    - `capital_rese_ps`: Capital reserve per share.
    - `surplus_rese_ps`: Surplus reserve per share.
    - `undist_profit_ps`: Undistributed profit per share.

## Relationships

- **StockInfo (1) -> (N) StockDaily**: One stock has many daily records.
- **StockInfo (1) -> (N) StockFinance**: One stock has many financial records.

## Data Flow

Data is typically fetched from external providers (like Tushare), converted into these Domain Entities, and then persisted into the database using Repositories.
