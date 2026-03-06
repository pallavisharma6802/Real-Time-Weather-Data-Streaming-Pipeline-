# Real-Time Weather Streaming Pipeline

A distributed streaming pipeline that moves simulated weather data from ingestion to HDFS storage with exactly-once semantics, atomic writes, and checkpoint-based crash recovery.

## Tech Stack

| Layer | Tools |
|---|---|
| Streaming | Apache Kafka (4 partitions, Protobuf serialization) |
| Storage | Hadoop HDFS (Parquet via PyArrow) |
| Database | MySQL + SQLAlchemy |
| Infrastructure | Docker, Docker Compose |
| Language | Python 3 |

## Pipeline
```
Weather Generator → MySQL → Kafka Producer → Kafka (4 partitions) → Consumers → HDFS (Parquet)
```

- 10 simulated stations, partitioned by station ID for parallel processing
- Each consumer owns one partition and writes independently

## Key Engineering Decisions

**Exactly-once semantics**
- Producer: `acks=all`, `retries=10`
- Consumer: checkpoints store Kafka offset + batch ID before acknowledging

**Atomic HDFS writes**
- Files written to `.tmp` path first, then renamed on completion
- Readers never see partial data

**Crash recovery**
- On restart, consumers read `partition-N.json` checkpoint and seek to last committed offset
- Guarantees no data loss or duplication across restarts

## Output

Parquet files in HDFS under `/data/`:
```
/data/partition-0-batch-0.parquet
/data/partition-0-batch-1.parquet
/data/partition-1-batch-0.parquet
...
```

Each file: `station_id`, `date`, `degrees`

## Quick Start
```bash
# Build images
docker build . -f Dockerfile.hdfs -t p7-hdfs
docker build . -f Dockerfile.kafka -t p7-kafka
docker build . -f Dockerfile.namenode -t p7-nn
docker build . -f Dockerfile.datanode -t p7-dn
docker build . -f Dockerfile.mysql -t p7-mysql

# Start cluster
export PROJECT=p7 && docker compose up -d

# Generate Protobuf stubs
python3 -m grpc_tools.protoc -I=src/ --python_out=src/ src/report.proto

# Run the pipeline
docker exec -d -w /src p7-kafka python3 weather_generator.py
docker exec -d -w /src p7-kafka python3 producer.py
docker exec -it -w /src p7-kafka python3 consumer.py 0  # repeat for partitions 1-3
```

**Requirements:** Docker, Docker Compose, Python 3

## Project Structure
```
├── docker-compose.yml
├── Dockerfile.*             # Per-service images (kafka, mysql, hdfs, namenode, datanode)
└── src/
    ├── weather_generator.py # Simulates station data → MySQL
    ├── producer.py          # MySQL → Kafka (Protobuf)
    ├── consumer.py          # Kafka → HDFS (partitioned, checkpointed)
    ├── debug.py             # Stream monitor
    └── report.proto         # Message schema
```
