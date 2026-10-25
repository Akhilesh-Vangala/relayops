# workers

- [worker.py](worker.py): claims queued runs, drives the investigator, simulates and publishes reports
- [worker_health.py](worker_health.py): heartbeat-based liveness probe
- [wait_for_database.py](wait_for_database.py): blocks startup until the migrated schema exists

[Deployment](../../../../docs/operations/DEPLOYMENT.md#durable-runtime)
