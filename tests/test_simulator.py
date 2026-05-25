# Desenvolvido por L. A. Leandro Sao Jose dos Campos- SP
# Data: 25/05/2026

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from src.telemetry.generators import (
    EstadoSensor,
    gerar_payload,
    step,
    TEMPERATURA_BASE,
    VIBRACAO_BASE,
)
from src.telemetry.sensor_node import SensorNode, TOPIC_TEMPLATE


class TestGeradores:
    def test_estado_inicial_dentro_da_faixa(self):
        estado = EstadoSensor.inicial()
        assert 20.0 <= estado.temperatura <= 85.0
        assert 0.0 <= estado.vibracao <= 0.5
        assert estado.ciclos_anomalia == 0

    def test_step_mantem_temperatura_na_faixa(self):
        estado = EstadoSensor(temperatura=50.0, vibracao=0.1, ciclos_anomalia=0)
        for _ in range(100):
            estado = step(estado)
            assert 20.0 <= estado.temperatura <= 85.0
            assert estado.vibracao >= 0.0

    def test_anomalia_vibracao_decai_gradualmente(self):
        estado = EstadoSensor(temperatura=50.0, vibracao=2.0, ciclos_anomalia=5)
        estado = step(estado)
        assert estado.ciclos_anomalia == 4
        assert estado.vibracao > 1.5
        assert estado.vibracao <= 2.0

    def test_anomalia_vibracao_retorna_ao_normal_ao_final(self):
        estado = EstadoSensor(temperatura=50.0, vibracao=2.5, ciclos_anomalia=1)
        estado = step(estado)
        assert estado.ciclos_anomalia == 0
        assert estado.vibracao < 0.5

    def test_status_operational_por_padrao(self):
        estado = EstadoSensor(temperatura=45.0, vibracao=0.1, ciclos_anomalia=0)
        from src.telemetry.generators import determinar_status

        assert determinar_status(estado.temperatura, estado.vibracao) == "OPERATIONAL"

    def test_status_critical_com_temperatura_alta(self):
        from src.telemetry.generators import determinar_status

        assert determinar_status(80.0, 0.1) == "CRITICAL"

    def test_status_critical_com_vibracao_alta(self):
        from src.telemetry.generators import determinar_status

        assert determinar_status(50.0, 1.5) == "CRITICAL"

    def test_status_warning_com_temperatura_elevada(self):
        from src.telemetry.generators import determinar_status

        assert determinar_status(62.0, 0.1) == "WARNING"

    def test_status_warning_com_vibracao_elevada(self):
        from src.telemetry.generators import determinar_status

        assert determinar_status(50.0, 0.45) == "WARNING"


class TestPayload:
    def test_estrutura_do_payload_json(self):
        estado = EstadoSensor(temperatura=42.58, vibracao=0.12, ciclos_anomalia=0)
        payload = gerar_payload("SNSR-IND-010", estado, tokenizar=False)

        assert "sensor_id" in payload
        assert "timestamp" in payload
        assert "metrics" in payload
        assert "status" in payload

        assert payload["sensor_id"] == "SNSR-IND-010"
        assert payload["metrics"]["temperature_celsius"] == 42.58
        assert payload["metrics"]["vibration_g"] == 0.12
        assert payload["status"] == "OPERATIONAL"

    def test_payload_timestamp_formato_iso(self):
        estado = EstadoSensor(temperatura=50.0, vibracao=0.1, ciclos_anomalia=0)
        payload = gerar_payload("SNSR-IND-001", estado, tokenizar=False)
        ts = payload["timestamp"]
        datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_tokenizacao_mascara_sensor_id(self):
        estado = EstadoSensor(temperatura=50.0, vibracao=0.1, ciclos_anomalia=0)
        payload_tokenizado = gerar_payload("SNSR-IND-999", estado, tokenizar=True)
        assert payload_tokenizado["sensor_id"] != "SNSR-IND-999"
        assert payload_tokenizado["sensor_id"].startswith("TKN-")

    def test_payload_serializavel_json(self):
        estado = EstadoSensor(temperatura=42.58, vibracao=0.12, ciclos_anomalia=0)
        payload = gerar_payload("SNSR-IND-010", estado, tokenizar=False)
        json_str = json.dumps(payload, ensure_ascii=False)
        reconstruido = json.loads(json_str)
        assert reconstruido == payload


class TestSensorNode:
    def test_topico_segue_padrao_hierarquico(self):
        sensor = SensorNode(
            sensor_id="SNSR-IND-005",
            client=MagicMock(),
            intervalo=0.01,
        )
        topico = sensor._topico()
        assert topico.startswith("fabrica/sao_jose_dos_campos/maquina_")
        assert topico.endswith("/metrics")
        assert "sensor_SNSR-IND-005" in topico

    @pytest.mark.asyncio
    async def test_run_publica_mensagem_valida(self):
        mock_client = MagicMock()
        sensor = SensorNode(
            sensor_id="SNSR-IND-001",
            client=mock_client,
            intervalo=0.01,
            qos=1,
        )

        tarefa = asyncio.create_task(sensor.run())
        await asyncio.sleep(0.02)
        tarefa.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarefa

        assert mock_client.publish.called
        args, kwargs = mock_client.publish.call_args
        assert kwargs["qos"] == 1
        topico = kwargs["topic"]
        assert topico.startswith("fabrica/sao_jose_dos_campos/")

        payload_dict = json.loads(kwargs["payload"])
        assert "sensor_id" in payload_dict
        assert "timestamp" in payload_dict
        assert "metrics" in payload_dict
        assert "temperature_celsius" in payload_dict["metrics"]
        assert "vibration_g" in payload_dict["metrics"]

    @pytest.mark.asyncio
    async def test_run_respeita_intervalo(self):
        mock_client = MagicMock()
        sensor = SensorNode(
            sensor_id="SNSR-IND-001",
            client=mock_client,
            intervalo=0.05,
        )

        tarefa = asyncio.create_task(sensor.run())
        await asyncio.sleep(0.12)
        tarefa.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarefa

        chamadas = mock_client.publish.call_count
        assert chamadas >= 1
        assert chamadas <= 4

    @pytest.mark.asyncio
    async def test_run_suporta_multiplos_sensores_concorrentes(self):
        mock_client = MagicMock()
        sensores = [
            SensorNode(
                sensor_id=f"SNSR-IND-{i:03d}",
                client=mock_client,
                intervalo=0.01,
            )
            for i in range(1, 11)
        ]

        tarefas = [asyncio.create_task(s.run()) for s in sensores]
        await asyncio.sleep(0.03)
        for t in tarefas:
            t.cancel()
        await asyncio.gather(*tarefas, return_exceptions=True)

        assert mock_client.publish.call_count >= 10


class TestReconexaoMQTT:
    def test_on_disconnect_nao_levanta_excecao(self):
        from src.config.mqtt_client import on_disconnect

        mock_client = MagicMock()
        on_disconnect(mock_client, None, 0)
        on_disconnect(mock_client, None, 1)

    def test_client_build_usa_variaveis_de_ambiente(self):
        with patch.dict("os.environ", {
            "MQTT_BROKER_URL": "test.mosquitto.org",
            "MQTT_BROKER_PORT": "1883",
            "MQTT_USER": "test_user",
            "MQTT_PASSWORD": "test_pass",
        }, clear=True):
            from importlib import reload
            import src.config.mqtt_client as mqtt_mod
            reload(mqtt_mod)
            assert mqtt_mod.MQTT_BROKER_URL == "test.mosquitto.org"
            assert mqtt_mod.MQTT_BROKER_PORT == 1883
            assert mqtt_mod.MQTT_USER == "test_user"
            assert mqtt_mod.MQTT_PASSWORD == "test_pass"
