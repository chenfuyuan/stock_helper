# API Guide

This guide focuses on the key APIs available in the system, particularly the **Scheduler API** for managing background tasks.

## Base URL

By default: `http://localhost:8000/api/v1`

## Scheduler API

The Scheduler API allows you to control data synchronization jobs dynamically.

### 1. Get Scheduler Status

Check if the scheduler is running and list all active jobs.

- **Endpoint**: `GET /scheduler/status`
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "is_running": true,
      "jobs": [
        {
          "id": "sync_daily_by_date",
          "name": "sync_daily_by_date_job",
          "next_run_time": "2023-10-27T18:00:00+08:00",
          "trigger": "cron[hour='18', minute='0']",
          "kwargs": {}
        }
      ],
      "available_jobs": ["sync_daily_history", "sync_daily_by_date", "sync_history_finance"]
    }
  }
  ```

### 2. Trigger a Job Immediately

Run a job once immediately (asynchronously).

- **Endpoint**: `POST /scheduler/jobs/{job_id}/trigger`
- **Example**: Trigger daily sync for a specific date.
  ```json
  {
    "params": {
      "trade_date": "2023-10-26"
    }
  }
  ```

### 3. Schedule a Cron Job

Set up a recurring job at a specific time daily.

- **Endpoint**: `POST /scheduler/jobs/{job_id}/schedule`
- **Body**:
  ```json
  {
    "hour": 18,
    "minute": 0
  }
  ```
- **Example**: Schedule `sync_daily_by_date` to run every day at 18:00.

### 4. Start an Interval Job

Set up a job that runs repeatedly with a time interval.

- **Endpoint**: `POST /scheduler/jobs/{job_id}/start`
- **Body**:
  ```json
  {
    "interval_minutes": 60
  }
  ```

### 5. Stop a Job

Remove a scheduled job (does not stop a currently executing job instance, but prevents future runs).

- **Endpoint**: `POST /scheduler/jobs/{job_id}/stop`

## Stock Data API

Standard CRUD operations for stock data.

- `GET /stocks/`: List stocks with pagination and filtering.
- `GET /stocks/{code}`: Get details of a specific stock.
- `POST /stocks/sync`: Manually trigger a full stock list sync.

## Swagger UI

For a complete interactive reference, visit the Swagger UI at `http://localhost:8000/api/v1/docs`.
