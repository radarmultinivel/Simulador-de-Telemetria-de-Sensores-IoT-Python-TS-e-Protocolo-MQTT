# Desenvolvido por L. A. Leandro Sao Jose dos Campos- SP
# Data: 25/05/2026

import random
from dataclasses import dataclass
from typing import Tuple

from src.config.mqtt_client import tokenize_sensor_id

TEMPERATURA_BASE = 45.0
AMPLITUDE_TEMPERATURA = 15.0
PASSO_TEMPERATURA = 0.8

VIBRACAO_BASE = 0.10
VIBRACAO_MAX_NORMAL = 0.50
PASSO_VIBRACAO = 0.05
PROBABILIDADE_ANOMALIA = 0.03
VIBRACAO_PICO_ANOMALO = 2.5


@dataclass
class EstadoSensor:
    temperatura: float
    vibracao: float
    ciclos_anomalia: int

    @classmethod
    def inicial(cls) -> "EstadoSensor":
        return cls(
            temperatura=TEMPERATURA_BASE + random.uniform(-5.0, 5.0),
            vibracao=VIBRACAO_BASE + random.uniform(-0.02, 0.02),
            ciclos_anomalia=0,
        )


def _caminhada_temperatura(temp_atual: float) -> float:
    passo = random.uniform(-PASSO_TEMPERATURA, PASSO_TEMPERATURA)
    nova = temp_atual + passo
    return max(20.0, min(85.0, nova))


def _caminhada_vibracao(vib_atual: float, anomalia: bool) -> Tuple[float, int]:
    if anomalia:
        pico = VIBRACAO_PICO_ANOMALO * random.uniform(0.6, 1.4)
        ciclos = random.randint(3, 8)
        return pico, ciclos

    passo = random.uniform(-PASSO_VIBRACAO, PASSO_VIBRACAO)
    nova = vib_atual + passo
    return max(0.0, min(VIBRACAO_MAX_NORMAL, nova)), 0


def step(estado: EstadoSensor) -> EstadoSensor:
    if estado.ciclos_anomalia > 0:
        ciclos_restantes = estado.ciclos_anomalia - 1
        vib = estado.vibracao * random.uniform(0.85, 1.0)
        if ciclos_restantes == 0:
            vib = VIBRACAO_BASE + random.uniform(-0.02, 0.02)
        return EstadoSensor(
            temperatura=_caminhada_temperatura(estado.temperatura),
            vibracao=vib,
            ciclos_anomalia=ciclos_restantes,
        )

    ocorreu_anomalia = random.random() < PROBABILIDADE_ANOMALIA
    vib, ciclos = _caminhada_vibracao(estado.vibracao, ocorreu_anomalia)
    return EstadoSensor(
        temperatura=_caminhada_temperatura(estado.temperatura),
        vibracao=vib,
        ciclos_anomalia=ciclos,
    )


def determinar_status(temp: float, vib: float) -> str:
    if temp > 75.0 or vib > 1.0:
        return "CRITICAL"
    if temp > 60.0 or vib > 0.4:
        return "WARNING"
    return "OPERATIONAL"


def gerar_payload(sensor_id: str, estado: EstadoSensor, tokenizar: bool = True) -> dict:
    from datetime import datetime, timezone

    saida_id = tokenize_sensor_id(sensor_id) if tokenizar else sensor_id

    return {
        "sensor_id": saida_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": {
            "temperature_celsius": round(estado.temperatura, 2),
            "vibration_g": round(estado.vibracao, 4),
        },
        "status": determinar_status(estado.temperatura, estado.vibracao),
    }
