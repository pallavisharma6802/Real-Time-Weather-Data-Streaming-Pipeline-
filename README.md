# Real-Time Weather Data Streaming Pipeline

A distributed data streaming pipeline that simulates real-time weather data ingestion, processing, and storage using Apache Kafka, MySQL, and Hadoop HDFS. This project demonstrates stream processing with exactly-once semantics, atomic writes, and crash recovery mechanisms.

## Overview

This system implements a scalable pipeline where weather data from multiple stations is streamed through Kafka and stored in Parquet format on HDFS for downstream analytics. The architecture includes:

- **Weather Generator**: Simulates daily weather observations from 10 stations
- **MySQL Database**: Stores incoming weather records
- **Kafka Producer**: Reads from MySQL and publishes to Kafka topic with Protobuf serialization
- **Kafka Consumer**: Processes partitioned streams and writes Parquet files to HDFS
- **Crash Recovery**: Checkpoint-based recovery with atomic writes

## Architecture

```
Weather Generator → MySQL → Kafka Producer → Kafka Topic (4 partitions) → Kafka Consumer → HDFS (Parquet)
```

The pipeline uses Protobuf for efficient message serialization, implements exactly-once delivery semantics, and ensures data consistency through atomic file writes and checkpointing.

## Technologies

- **Python 3**: Core application logic
- **Apache Kafka**: Distributed message streaming
- **MySQL**: Relational database for weather records
- **Hadoop HDFS**: Distributed file storage
- **Protocol Buffers (Protobuf)**: Message serialization
- **PyArrow**: Parquet file generation
- **Docker Compose**: Container orchestration
- **SQLAlchemy**: Database ORM

## Project Structure

```
.
├── docker-compose.yml          # Container orchestration configuration
├── Dockerfile.kafka            # Kafka broker container
├── Dockerfile.mysql            # MySQL database container
├── Dockerfile.hdfs             # HDFS base container
├── Dockerfile.namenode         # HDFS NameNode container
├── Dockerfile.datanode         # HDFS DataNode container
├── requirements.txt            # Project dependencies
└── src/
    ├── weather_generator.py    # Simulates weather data generation
    ├── producer.py             # Kafka producer (MySQL → Kafka)
    ├── consumer.py             # Kafka consumer (Kafka → HDFS)
    ├── debug.py                # Debug consumer for monitoring
    ├── report.proto            # Protobuf message schema
    └── requirements.txt        # Python package dependencies
```

## Prerequisites

- Docker and Docker Compose
- Python 3.x
- Protocol Buffer Compiler (protoc)

## Setup and Installation

### 1. Build Docker Images

```bash
docker build . -f Dockerfile.hdfs     -t p7-hdfs
docker build . -f Dockerfile.kafka    -t p7-kafka
docker build . -f Dockerfile.namenode -t p7-nn
docker build . -f Dockerfile.datanode -t p7-dn
docker build . -f Dockerfile.mysql    -t p7-mysql
```

### 2. Start Services

```bash
export PROJECT=p7
docker compose up -d
```

This will start:

- Kafka broker
- MySQL database
- HDFS NameNode
- HDFS DataNodes (3 replicas)

### 3. Generate Protobuf Code

```bash
python3 -m grpc_tools.protoc -I=src/ --python_out=src/ src/report.proto
```

## Usage

### Start Weather Data Generator

```bash
docker exec -d -w /src p7-kafka python3 weather_generator.py
```

This generates simulated weather data for 10 stations starting from 2000-01-01, inserting records into MySQL at an accelerated rate (1 day per 0.1 seconds).

### Start Kafka Producer

```bash
docker exec -d -w /src p7-kafka python3 producer.py
```

The producer:

- Creates a Kafka topic `temperatures` with 4 partitions
- Reads weather records from MySQL
- Serializes data using Protobuf
- Publishes to Kafka with exactly-once semantics (acks=all, retries=10)

### Monitor with Debug Consumer

```bash
docker exec -it -w /src p7-kafka python3 debug.py
```

Prints incoming messages from all partitions for verification.

### Start Kafka Consumers

Launch separate consumers for each partition:

```bash
docker exec -it -w /src p7-kafka python3 consumer.py 0
docker exec -it -w /src p7-kafka python3 consumer.py 1
docker exec -it -w /src p7-kafka python3 consumer.py 2
docker exec -it -w /src p7-kafka python3 consumer.py 3
```

Each consumer:

- Manually assigns a specific partition
- Processes batches of messages
- Writes Parquet files to HDFS atomically
- Maintains checkpoints for crash recovery

## Key Features

### Exactly-Once Semantics

- Producer configured with `acks=all` and `retries=10`
- Consumer checkpoints store offsets alongside batch references
- Atomic writes prevent partial data visibility

### Crash Recovery

- Consumers write checkpoint files (`partition-N.json`) containing:
  - Current batch ID
  - Kafka partition offset
- On restart, consumers seek to last committed offset
- Ensures no data loss or duplication

### Atomic Writes to HDFS

- Files written to temporary location (`.tmp` suffix)
- Atomic move operation after complete write
- Prevents readers from seeing partial data

### Partitioned Processing

- Topic partitioned by station ID
- Supports parallel processing across multiple consumers
- Scalable architecture for high-throughput scenarios

## Data Flow

1. **Weather Generator** inserts records into MySQL `temperatures` table
2. **Producer** queries MySQL for new records (by ID) and publishes to Kafka
3. **Kafka** distributes messages across 4 partitions based on station ID key
4. **Consumers** read assigned partitions and write batches to HDFS as Parquet files
5. **Checkpoints** track processing progress for each partition

## Output Format

Parquet files stored in HDFS under `/data/`:

```
hdfs://boss:9000/data/partition-0-batch-0.parquet
hdfs://boss:9000/data/partition-0-batch-1.parquet
hdfs://boss:9000/data/partition-1-batch-0.parquet
...
```

Each file contains three columns:

- `station_id`: Weather station identifier
- `date`: Observation date (YYYY-MM-DD)
- `degrees`: Temperature in degrees

## Verification

### Check MySQL Data

```bash
docker exec -it p7-mysql mysql -u root -pabc CS544 -e "SELECT * FROM temperatures LIMIT 10;"
```

### List HDFS Files

```bash
docker exec -it p7-kafka hdfs dfs -ls hdfs://boss:9000/data/
```

### Read Parquet File

```python
import pyarrow.parquet as pq
import pyarrow.fs as fs

hdfs = fs.HadoopFileSystem('boss', 9000)
table = pq.read_table('hdfs://boss:9000/data/partition-0-batch-0.parquet', filesystem=hdfs)
print(table.to_pandas())
```

## Configuration

Key configurations in the pipeline:

- **Kafka Topic**: 4 partitions, replication factor 1
- **Producer**: Max 10 retries, all replicas must acknowledge
- **Consumer**: Manual partition assignment, batch processing
- **Data Rate**: 1 day per 0.1 seconds (configurable via `AUTOGRADER_DELAY_OVERRIDE_VAL`)

## Limitations and Future Work

- Single Kafka broker (not a cluster) for simplicity
- Small batch sizes result in many small Parquet files (not optimal for HDFS)
- Hardcoded connection parameters (suitable for local development only)
- No authentication or encryption (academic prototype)

Future enhancements could include:

- Multi-broker Kafka cluster for fault tolerance
- Larger batch sizes for improved HDFS efficiency
- Real-time dashboard for data visualization
- Stream processing with aggregations and windowing
- Integration with Apache Spark or Flink for analytics

## Acknowledgments

Developed as part of CS544: Big Data Systems course project. This implementation demonstrates fundamental concepts in distributed systems, stream processing, and big data storage architectures.
