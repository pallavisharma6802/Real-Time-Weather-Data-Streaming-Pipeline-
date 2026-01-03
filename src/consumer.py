import os
import sys
import json
import pandas as pd
import report_pb2
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.fs as fs
from kafka import KafkaConsumer, TopicPartition
from subprocess import check_output

os.environ["CLASSPATH"] = str(check_output([os.environ["HADOOP_HOME"]+"/bin/hdfs", "classpath", "--glob"]), "utf-8")

broker     = 'localhost:9092'
topic_name = 'temperatures'

def main():
    if len(sys.argv) != 2:
        print("Usage: python consumer.py <partition_number>")
        sys.exit(1)
    partition_id = int(sys.argv[1])

    # TODO: Create KafkaConsumer using manual partition assignment
    consumer = KafkaConsumer(bootstrap_servers=[broker])
    consumer.assign([TopicPartition(topic_name, partition_id)])
    hdfs = fs.HadoopFileSystem('boss', 9000)

    file = f"/partition-{partition_id}.json"
    if os.path.exists(file):
        with open(file, "r") as f:
            checkpoint = json.load(f)
        batch_id = checkpoint["batch_id"] + 1
        offset = checkpoint["offset"]
        consumer.seek(TopicPartition(topic_name, partition_id), offset)
    else:
        batch_id = 0
        consumer.seek(TopicPartition(topic_name, partition_id), 0)

    while True:
        batch = consumer.poll(1000)
        weather_list = []
        for topic_partition, msgs in batch.items():
            for msg in msgs:
                report = report_pb2.Report.FromString(msg.value)
                weather_list.append({
                    'station_id': report.station_id,
                    'date': report.date,
                    'degrees': report.degrees
                })

        if weather_list:
            df = pd.DataFrame(weather_list)
            filename = f"data/partition-{partition_id}-batch-{batch_id}.parquet"
            path = f"hdfs://boss:9000/{filename}"
            path_tmp = path + ".tmp"

            with hdfs.open_output_stream(path_tmp) as f:
                table = pa.Table.from_pandas(df)
                pq.write_table(table, f)
            hdfs.move(path_tmp, path)

            position = consumer.position(TopicPartition(topic_name, partition_id))
            data = {
                "batch_id": batch_id,
                "offset": position
            }
            with open(file + ".tmp", "w") as f:
                json.dump(data, f)
            os.replace(file + ".tmp", file)

            batch_id += 1

if __name__ == '__main__':
    main()

