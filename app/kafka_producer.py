import json
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer


class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str, topic: str = "notifications"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        if self._producer:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def publish(self, event: Dict[str, Any]) -> None:
        """
        Fire-and-forget semantics are handled by caller (BackgroundTasks).
        This method still awaits Kafka send to ensure delivery to broker.
        """
        if not self._producer:
            raise RuntimeError("Kafka producer not started")
        await self._producer.send_and_wait(self.topic, event)
