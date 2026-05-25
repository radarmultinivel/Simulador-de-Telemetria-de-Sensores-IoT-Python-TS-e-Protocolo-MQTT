# Desenvolvido por L. A. Leandro Sao Jose dos Campos- SP
# Data: 25/05/2026

import os
import logging
from hashlib import sha256

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

MQTT_BROKER_URL = os.environ.get("MQTT_BROKER_URL", "localhost")
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
MQTT_USER = os.environ.get("MQTT_USER", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
MQTT_CLIENT_ID = os.environ.get("MQTT_CLIENT_ID", "iot_simulator")


def tokenize_sensor_id(raw_id: str, salt: str = "ind4.0") -> str:
    h = sha256(f"{raw_id}{salt}".encode()).hexdigest()[:12].upper()
    return f"TKN-{h}"


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Cliente MQTT conectado ao broker {MQTT_BROKER_URL}:{MQTT_BROKER_PORT}")
    else:
        logger.error(f"Falha na conexão MQTT. Código RC={rc}")


def on_disconnect(client, userdata, rc, properties=None):
    if rc != 0:
        logger.warning(f"Desconexão inesperada do broker (RC={rc}). Tentando reconectar...")


def build_client() -> mqtt.Client:
    client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        protocol=mqtt.MQTTv311,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    client.connect_async(MQTT_BROKER_URL, MQTT_BROKER_PORT, keepalive=60)
    client.loop_start()

    logger.info(f"Cliente MQTT inicializado — {MQTT_BROKER_URL}:{MQTT_BROKER_PORT}")
    return client
