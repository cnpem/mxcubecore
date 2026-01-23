import os
import threading
import queue
import logging
import msgpack_numpy
from kafka import KafkaConsumer


class KafkaLogger():

    _data_buffer = queue.Queue()
    start_buffer = {}
    stop_buffer = {}

    def monitor(self, consumer):
        for message in consumer:
            kafka_msg = msgpack_numpy.unpackb(message.value)
            msg_id = kafka_msg[0]
            
            if msg_id == "event":
                self._data_buffer.put(kafka_msg[1])
            elif msg_id == "start":
                self.start_buffer = kafka_msg[1]
            elif msg_id == 'stop':
                self.stop_buffer = kafka_msg[1]
                break
        consumer.close()

    def read_data_buffer(self):
        step_values = []
        while not self._data_buffer.empty():
            step_values = self._data_buffer.get()
        return step_values

    def connect(self):
        consumer = KafkaConsumer(
            os.environ['KAFKA_TOPIC'], 
            bootstrap_servers=[os.environ['KAFKA_BOOTSTRAP']])
        if consumer.bootstrap_connected():
            logging.getLogger("HWR").info("Connected to Kafka server")
            kafka_thread = threading.Thread(target=self.monitor, args=(consumer, ))
            kafka_thread.start()
