import report_pb2
from kafka import KafkaConsumer

broker = "localhost:9092"
topic_name = "temperatures"

consumer = KafkaConsumer(
    bootstrap_servers=[broker],
    group_id="debug",    
)

consumer.subscribe([topic_name])

for msg in consumer:
    report = report_pb2.Report.FromString(msg.value)
    result = {
        'station_id': report.station_id,
        'date': report.date,
        'degrees': report.degrees,
        'partition': msg.partition,
    }
    print(result)