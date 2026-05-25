# Desenvolvido por L. A. Leandro Sao Jose dos Campos- SP
# Data: 25/05/2026

import asyncio
import logging
import signal

from src.config.mqtt_client import build_client
from src.telemetry.sensor_node import SensorNode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

QTD_SENSORES = 10
SENSORES_BASE = [f"SNSR-IND-{i:03d}" for i in range(1, QTD_SENSORES + 1)]


async def main() -> None:
    logger.info("Inicializando Simulador de Telemetria Industrial IoT")
    logger.info(f"Registrando {QTD_SENSORES} sensores: {SENSORES_BASE}")

    client = build_client()

    sensores = [
        SensorNode(sensor_id=sid, client=client)
        for sid in SENSORES_BASE
    ]

    tarefas = [asyncio.create_task(sensor.run()) for sensor in sensores]

    shutdown_event = asyncio.Event()

    def _shutdown():
        logger.info("Sinal de desligamento recebido. Encerrando sensores...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass

    await shutdown_event.wait()

    for t in tarefas:
        t.cancel()

    await asyncio.gather(*tarefas, return_exceptions=True)

    client.loop_stop()
    client.disconnect()
    logger.info("Simulador encerrado com sucesso.")


if __name__ == "__main__":
    asyncio.run(main())
