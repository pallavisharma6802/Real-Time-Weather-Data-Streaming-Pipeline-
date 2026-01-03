import os
import time
import report_pb2
from kafka import KafkaAdminClient, KafkaProducer, KafkaConsumer
from kafka.admin import NewTopic
from kafka.errors import UnknownTopicOrPartitionError, TopicAlreadyExistsError
from sqlalchemy import create_engine, text

broker = "localhost:9092"
admin = KafkaAdminClient(bootstrap_servers=[broker])
topic_name = "temperatures"

try:
    admin.delete_topics([topic_name])
    time.sleep(3)
except UnknownTopicOrPartitionError:
    pass

try:
    admin.create_topics([NewTopic(name = topic_name, num_partitions=4, replication_factor=1)])
except TopicAlreadyExistsError:
    pass

project = os.environ.get("PROJECT", "p7")
sqlhost = f"{project}-mysql-1"

#ref1 - https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html
#ref2 - https://kafka.apache.org/27/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html#:~:text=valueSerializer)-,A%20producer%20is%20instantiated%20by%20providing%20a%20set%20of%20key,it%20to%20avoid%20resource%20leaks.
producer = KafkaProducer(
    bootstrap_servers=broker,
    key_serializer=lambda k: k.encode('utf-8'), 
    value_serializer=lambda v: v.SerializeToString(),
    retries=10,
    acks='all'
)

#ref3 - https://stackoverflow.com/questions/74495598/sqlalchemy-attributeerror-connection-object-has-no-attribute-commit
engine = create_engine(f"mysql+mysqlconnector://root:abc@{sqlhost}/CS544", future=True)

curr = 0
while True:
    with engine.begin() as conn:
        query = conn.execute(text("""SELECT * 
                                     FROM temperatures 
                                     WHERE id > :id 
                                     ORDER BY id"""),
                              {"id": curr})
        rows = list(query)
        for row in rows:
            curr = row[0]
            report = report_pb2.Report()
            report.date = str(row[2])
            report.degrees = float(row[3])
            report.station_id = row[1]

            result = producer.send(topic_name, key=row[1], value=report)
            result.get()

        conn.commit()
    time.sleep(1)




