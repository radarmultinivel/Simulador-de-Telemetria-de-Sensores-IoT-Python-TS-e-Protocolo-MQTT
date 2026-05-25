# Desenvolvido por L. A. Leandro Sao Jose dos Campos- SP
# Data: 25/05/2026

import asyncio
import json
import logging

import paho.mqtt.client as mqtt

from src.telemetry.generators import EstadoSensor, gerar_payload, step

logger = logging.getLogger(__name__)

TOPIC_TEMPLATE = "fabrica/sao_jose_dos_campos/maquina_{maquina:02d}/sensor_{sensor_id}/metrics"


class SensorNode:
    def __init__(
        self,
        sensor_id: str,
        client: mqtt.Client,
        intervalo: float = 2.0,
        qos: int = 1,
        tokenizar: bool = True,
    ):
        self.sensor_id = sensor_id
        self.client = client
        self.intervalo = intervalo
        self.qos = qos
        self.tokenizar = tokenizar
        self._estado = EstadoSensor.inicial()

    def _topico(self) -> str:
        maquina_num = int(self.sensor_id.split("-")[-1]) % 10 + 1
        return TOPIC_TEMPLATE.format(maquina=maquina_num, sensor_id=self.sensor_id)

    async def run(self) -> None:
        logger.info(f"Sensor {self.sensor_id} iniciado no tópico {self._topico()}")
        while True:
            self._estado = step(self._estado)
            payload = gerar_payload(self.sensor_id, self._estado, tokenizar=self.tokenizar)
            payload_json = json.dumps(payload, ensure_ascii=False)

            self.client.publish(
                topic=self._topico(),
                payload=payload_json,
                qos=self.qos,
            )

            logger.debug(f"[{self.sensor_id}] {payload['status']} — T={payload['metrics']['temperature_celsius']}°C | V={payload['metrics']['vibration_g']}g")

            await asyncio.sleep(self.intervalo)
