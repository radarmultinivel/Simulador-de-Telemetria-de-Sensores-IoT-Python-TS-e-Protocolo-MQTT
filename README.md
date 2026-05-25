# Simulador de Telemetria de Sensores IoT

**Desenvolvido por L. A. Leandro Sao Jose dos Campos- SP**
**Data: 25/05/2026**

---

## 1. Objetivo do Programa

Este software simula o comportamento de 10 sensores industriais fisicos independentes que enviam leituras continuas de telemetria (temperatura e vibracao) para um Broker central utilizando o protocolo MQTT. O sistema e projetado para ambientes de fabrica inteligente (Industria 4.0), permitindo testes de arquiteturas de mensageria, carga em bancos de series temporais e prototipagem de regras de alerta preditivo sem a necessidade de hardware fisico.

---

## 2. Requisitos

### 2.1. Requisitos Funcionais

| Codigo | Descricao |
|--------|-----------|
| RF-01 | O sistema deve simular 10 sensores operando em paralelo |
| RF-02 | Cada sensor deve publicar leituras de temperatura (Celsius) e vibracao (G) |
| RF-03 | Os dados devem ser publicados via protocolo MQTT com QoS 1 |
| RF-04 | Os topicos devem seguir estrutura hierarquica: `fabrica/sao_jose_dos_campos/maquina_XX/sensor_XXXX/metrics` |
| RF-05 | O payload deve ser JSON com timestamp ISO 8601 |
| RF-06 | O sistema deve suportar reconexao automatica ao broker |
| RF-07 | IDs de sensores devem ser tokenizados antes de trafegar na rede |
| RF-08 | Credenciais do broker devem ser lidas de variaveis de ambiente |

### 2.2. Requisitos Nao Funcionais

| Codigo | Descricao |
|--------|-----------|
| RNF-01 | Linguagem: Python 3.11+ |
| RNF-02 | Protocolo: MQTT v3.1.1 |
| RNF-03 | Runtime concorrente: asyncio |
| RNF-04 | Cliente MQTT: biblioteca paho-mqtt |
| RNF-05 | Broker de desenvolvimento: Eclipse Mosquitto (Docker) |
| RNF-06 | Testes: pytest + pytest-asyncio |

---

## 3. Especificacoes Tecnicas

### 3.1. Estrutura do Topico MQTT

```
fabrica/sao_jose_dos_campos/maquina_{maquina:02d}/sensor_{sensor_id}/metrics
```

Exemplo:
```
fabrica/sao_jose_dos_campos/maquina_05/sensor_SNSR-IND-005/metrics
```

### 3.2. Estrutura do Payload JSON

```json
{
  "sensor_id": "TKN-A1B2C3D4E5F6",
  "timestamp": "2026-05-25T23:42:00Z",
  "metrics": {
    "temperature_celsius": 42.58,
    "vibration_g": 0.12
  },
  "status": "OPERATIONAL"
}
```

### 3.3. Algoritmo de Geracao de Dados

O sistema utiliza o modelo de **caminhada aleatoria (random walk)** controlada:

- **Temperatura:** varia gradualmente em torno de 45C com passos de ate 0.8C por ciclo, limitada a faixa 20C-85C
- **Vibracao:** oscila em torno de 0.10G com passos de ate 0.05G
- **Anomalias:** 3% de probabilidade por ciclo de disparar um pico anomalo de vibracao (ate 3.5G) com duracao de 3 a 8 ciclos
- **Status:** OPERATIONAL (< 60C e < 0.4G), WARNING (< 75C e < 1.0G), CRITICAL (> 75C ou > 1.0G)

### 3.4. Mecanismos de Seguranca

1. **Tokenizacao de IDs:** SHA-256 com salt sobre o identificador bruto, gerando token de 12 caracteres (ex: `TKN-A1B2C3D4E5F6`)
2. **Variaveis de ambiente:** Credenciais nunca sao hardcoded, lidas exclusivamente de variaveis de ambiente
3. **Conexao segura:** Suporte a autenticacao usuario/senha no broker Mosquitto

---

## 4. Fluxograma da Arquitetura

```
+============================================================================+
|                        SIMULADOR DE TELEMETRIA IOT                          |
+============================================================================+
|                                                                             |
|  +---------------------------+     +-----------------------------------+   |
|  |       main.py             |     |       config/mqtt_client.py       |   |
|  |  Orquestrador Assincrono  |---->|  Gerenciador de Conexao MQTT     |   |
|  |                           |     |  - Le env vars                   |   |
|  |  Cria 10 SensorNodes      |     |  - Tokenizacao SHA-256           |   |
|  |  Gerencia shutdown        |     |  - Callbacks on_connect          |   |
|  +---------------------------+     |  - on_disconnect / reconexao     |   |
|            |                        +-----------------------------------+   |
|            |                                       |                       |
|            v                                       v                       |
|  +---------------------------+     +-----------------------------------+   |
|  |   telemetry/sensor_node   |     |          Broker MQTT              |   |
|  |   Classe SensorNode       |---->|      Mosquitto :1883             |   |
|  |                           |     |     topicos hierarquicos         |   |
|  |  Loop while True          |     |     QoS 1                        |   |
|  |  await asyncio.sleep()    |     +-----------------------------------+   |
|  +---------------------------+                       |                       |
|            |                                         |                       |
|            v                                         v                       |
|  +---------------------------+     +-----------------------------------+   |
|  | telemetry/generators.py   |     |     Consumidores Externos         |   |
|  |                           |     |                                   |   |
|  |  Random Walk Temperatura  |     |  - mosquitto_sub (CLI)           |   |
|  |  Random Walk Vibracao     |     |  - MQTT Explorer (GUI)           |   |
|  |  Deteccao de Anomalias    |     |  - InfluxDB / TimescaleDB        |   |
|  |  Determinacao de Status   |     |  - Dashboards SRE                |   |
|  +---------------------------+     +-----------------------------------+   |
|                                                                             |
+============================================================================+
```

### Fluxo de Execucao

```
INICIO
  |
  v
main()
  |-- logging.basicConfig()
  |-- build_client()
  |     |-- Le variaveis de ambiente (MQTT_BROKER_URL, MQTT_USER, etc)
  |     |-- Cria cliente paho-mqtt com MQTTv311
  |     |-- Configura callbacks on_connect / on_disconnect
  |     |-- connect_async() + loop_start()
  |     +-- Retorna client
  |
  |-- Cria lista de 10 SensorNodes (SNSR-IND-001 a SNSR-IND-010)
  |
  |-- Cria 10 tarefas asyncio (uma por sensor)
  |     |
  |     +-- SensorNode.run()  (cada sensor em paralelo)
  |           |
  |           +-- while True:
  |                 |-- estado = step(estado)       # caminhada aleatoria
  |                 |-- payload = gerar_payload()    # monta JSON + tokeniza
  |                 |-- client.publish(topic, json, qos=1)
  |                 |-- await asyncio.sleep(2.0)
  |
  |-- Aguarda sinal de desligamento (SIGINT/SIGTERM)
  |
  |-- Cancela todas as tarefas
  |-- client.loop_stop() + client.disconnect()
  +-- FIM
```

---

## 5. Stacks e Tecnologias

| Camada | Tecnologia | Versao |
|--------|-----------|--------|
| Linguagem | Python | 3.11+ |
| Protocolo | MQTT | v3.1.1 |
| Cliente MQTT | paho-mqtt | >=1.6.1 <2.0.0 |
| Runtime | asyncio | (stdlib) |
| Broker (dev) | Eclipse Mosquitto | 2.0 |
| Container | Docker / Compose | 3.8 |
| Testes | pytest | >=7.4 |
| Testes assincronos | pytest-asyncio | >=0.21 |
| SO | Windows / Linux / macOS | - |

### Diagrama de Dependencias

```
requirements.txt
  |
  +-- paho-mqtt>=1.6.1,<2.0.0    (comunicacao MQTT)
  |
  +-- pytest>=7.4.0               (framework de testes)
  |
  +-- pytest-asyncio>=0.21.0      (suporte asyncio nos testes)
```

### Docker Images

```
docker-compose.yml
  |
  +-- eclipse-mosquitto:2.0       (broker MQTT local)
        |
        +-- mosquitto/config/mosquitto.conf  (configuracao)
        +-- /mosquitto/data/                 (persistencia)
        +-- /mosquitto/log/                  (logs)
```

---

## 6. Estrutura do Projeto

```
/
|
+-- docker-compose.yml              # Orquestracao do broker Mosquitto
+-- requirements.txt                # Dependencias Python
+-- .env.example                    # Template de variaveis de ambiente
|
+-- mosquitto/
|   +-- config/
|       +-- mosquitto.conf          # Configuracao do broker MQTT
|
+-- src/
|   +-- __init__.py
|   +-- main.py                     # Orquestrador principal assincrono
|   |
|   +-- config/
|   |   +-- __init__.py
|   |   +-- mqtt_client.py          # Gerenciador de conexao MQTT
|   |
|   +-- telemetry/
|       +-- __init__.py
|       +-- generators.py           # Algoritmos de geracao de dados
|       +-- sensor_node.py          # Classe do no sensor assincrono
|
+-- tests/
|   +-- __init__.py
|   +-- test_simulator.py           # Testes automatizados (19 cenarios)
|
+-- README.md                       # Documentacao
+-- LICENSE
```

---

## 7. Instalacao e Execucao

### 7.1. Pre-requisitos

- Python 3.11 ou superior
- Docker e Docker Compose
- Git (opcional)

### 7.2. Passo a Passo

#### Passo 1: Clone o repositorio

```bash
git clone https://github.com/seu-usuario/Simulador-de-Telemetria-de-Sensores-IoT-Python-TS-e-Protocolo-MQTT.git
cd Simulador-de-Telemetria-de-Sensores-IoT-Python-TS-e-Protocolo-MQTT
```

#### Passo 2: Suba o broker Mosquitto

```bash
docker compose up -d
```

Verifique se o container esta rodando:

```bash
docker ps --filter name=mqtt-broker
```

Para gerar o arquivo de senhas no broker:

```bash
docker exec -it mqtt-broker mosquitto_passwd -c /mosquitto/config/passwd iot_simulator
# Digite a senha quando solicitado
docker restart mqtt-broker
```

#### Passo 3: Crie e ative o ambiente virtual

```bash
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (CMD):
venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate
```

#### Passo 4: Instale as dependencias

```bash
pip install -r requirements.txt
```

#### Passo 5: Configure as variaveis de ambiente

Copie o arquivo de exemplo:

```bash
# Windows:
copy .env.example .env

# Linux / macOS:
cp .env.example .env
```

Edite o arquivo `.env` conforme sua configuracao:

```ini
MQTT_BROKER_URL=localhost
MQTT_BROKER_PORT=1883
MQTT_USER=iot_simulator
MQTT_PASSWORD=sua_senha_aqui
MQTT_CLIENT_ID=simulador_industria_01
```

#### Passo 6: Execute o simulador

```bash
python src/main.py
```

---

## 8. Manual do Usuario

### 8.1. Console de Execucao

Ao iniciar, o simulador exibe:

```
2026-05-25T23:42:00 [INFO] __main__: Inicializando Simulador de Telemetria Industrial IoT
2026-05-25T23:42:00 [INFO] __main__: Registrando 10 sensores: ['SNSR-IND-001', ..., 'SNSR-IND-010']
2026-05-25T23:42:00 [INFO] src.config.mqtt_client: Cliente MQTT inicializado --- localhost:1883
2026-05-25T23:42:00 [INFO] src.config.mqtt_client: Cliente MQTT conectado ao broker localhost:1883
2026-05-25T23:42:00 [INFO] src.telemetry.sensor_node: Sensor SNSR-IND-001 iniciado no topico fabrica/sao_jose_dos_campos/maquina_01/sensor_SNSR-IND-001/metrics
...
```

A cada 2 segundos, cada sensor publica uma leitura. Em modo DEBUG (altere `logging.INFO` para `logging.DEBUG` em `main.py`), e possivel ver cada publicacao individual.

### 8.2. Encerramento

Pressione **Ctrl+C** para encerrar graciosamente:

```
2026-05-25T23:45:00 [INFO] __main__: Sinal de desligamento recebido. Encerrando sensores...
2026-05-25T23:45:00 [INFO] __main__: Simulador encerrado com sucesso.
```

### 8.3. Inspecao com mosquitto_sub

Com o broker rodando, abra um segundo terminal e inscreva-se nos topicos:

```bash
# Todos os sensores
mosquitto_sub -h localhost -p 1883 \
  -u iot_simulator -P sua_senha_aqui \
  -t "fabrica/+/+/+/metrics" -v

# Sensor especifico
mosquitto_sub -h localhost -p 1883 \
  -u iot_simulator -P sua_senha_aqui \
  -t "fabrica/sao_jose_dos_campos/maquina_01/sensor_SNSR-IND-001/metrics" -v

# Todas as temperaturas
mosquitto_sub -h localhost -p 1883 \
  -u iot_simulator -P sua_senha_aqui \
  -t "fabrica/+/+/+/metrics" -v \
  | Select-String "temperature_celsius"
```

Saida esperada:

```
fabrica/sao_jose_dos_campos/maquina_01/sensor_SNSR-IND-001/metrics {"sensor_id": "TKN-A1B2C3D4E5F6", "timestamp": "2026-05-25T23:42:00Z", "metrics": {"temperature_celsius": 42.58, "vibration_g": 0.12}, "status": "OPERATIONAL"}
```

### 8.4. Inspecao com MQTT Explorer (GUI)

Recomenda-se o [MQTT Explorer](http://mqtt-explorer.com/) para inspecao visual:

1. Instale o MQTT Explorer
2. Configure conexao: `localhost:1883`, usuario/senha
3. Navegue pelos topicos na arvore a esquerda
4. Clique em um topico para ver o payload JSON formatado

### 8.5. Configuracao de Parametros

| Parametro | Arquivo | Descricao | Valor Padrao |
|-----------|---------|-----------|--------------|
| `MQTT_BROKER_URL` | `.env` | Host do broker | localhost |
| `MQTT_BROKER_PORT` | `.env` | Porta do broker | 1883 |
| `MQTT_USER` | `.env` | Usuario de autenticacao | iot_simulator |
| `MQTT_PASSWORD` | `.env` | Senha de autenticacao | - |
| `MQTT_CLIENT_ID` | `.env` | ID do cliente MQTT | iot_simulator |
| `QTD_SENSORES` | `src/main.py` | Numero de sensores | 10 |
| `intervalo` | `sensor_node.py` | Intervalo entre leituras (s) | 2.0 |
| `TEMPERATURA_BASE` | `generators.py` | Temperatura central (C) | 45.0 |
| `VIBRACAO_BASE` | `generators.py` | Vibracao central (G) | 0.10 |
| `PROBABILIDADE_ANOMALIA` | `generators.py` | Chance de anomalia por ciclo | 0.03 (3%) |
| `QOS` | `sensor_node.py` | Nivel de Qualidade de Servico | 1 |

---

## 9. Testes

### 9.1. Execucao dos Testes

```bash
pytest tests/ -v --tb=short
```

### 9.2. Cobertura de Testes (19 cenarios)

**TestGeradores (9 testes):**
- `test_estado_inicial_dentro_da_faixa` - Valida limites iniciais
- `test_step_mantem_temperatura_na_faixa` - Temperatura permanece 20C-85C apos 100 passos
- `test_anomalia_vibracao_decai_gradualmente` - Pico anomalo decai suavemente
- `test_anomalia_vibracao_retorna_ao_normal_ao_final` - Retorno ao normal apos ciclo anomalo
- `test_status_operational_por_padrao` - Status padrao OPERATIONAL
- `test_status_critical_com_temperatura_alta` - Temperatura > 75C -> CRITICAL
- `test_status_critical_com_vibracao_alta` - Vibracao > 1.0G -> CRITICAL
- `test_status_warning_com_temperatura_elevada` - Temperatura 60C-75C -> WARNING
- `test_status_warning_com_vibracao_elevada` - Vibracao 0.4G-1.0G -> WARNING

**TestPayload (4 testes):**
- `test_estrutura_do_payload_json` - Payload contem todos os campos obrigatorios
- `test_payload_timestamp_formato_iso` - Timestamp esta em formato ISO 8601 valido
- `test_tokenizacao_mascara_sensor_id` - Tokenizacao altera o ID original
- `test_payload_serializavel_json` - Payload e serializavel/desserializavel

**TestSensorNode (4 testes):**
- `test_topico_segue_padrao_hierarquico` - Topico segue formato especificado
- `test_run_publica_mensagem_valida` - Sensor publica payload valido com QoS 1
- `test_run_respeita_intervalo` - Intervalo entre publicacoes e respeitado
- `test_run_suporta_multiplos_sensores_concorrentes` - 10 sensores rodam em paralelo

**TestReconexaoMQTT (2 testes):**
- `test_on_disconnect_nao_levanta_excecao` - Callback de desconexao e seguro
- `test_client_build_usa_variaveis_de_ambiente` - Variaveis de ambiente sao lidas corretamente

### 9.3. Testes com Mock

Os testes utilizam `unittest.mock.MagicMock` para simular o cliente MQTT, permitindo validacao sem necessidade de broker real ou conexao de rede.

---

## 10. Casos de Uso

### 10.1. Carga em Bancos de Series Temporais

Alimente InfluxDB, TimescaleDB ou Prometheus com dados realistas para:
- Testar capacidade de ingestao antes do deploy de hardware fisico
- Validar politicas de retencao e downsampling
- Dimensionar recursos de armazenamento

### 10.2. Prototipagem de Alertas Preditivos

Simule cenarios de WARNING e CRITICAL para:
- Testar regras de alerta em paineis SRE
- Validar logicas de escalonamento de incidentes
- Treinar modelos de machine learning preditivo

### 10.3. Testes de Arquitetura de Mensageria

Valide:
- Throughput do broker MQTT sob carga
- Comportamento de QoS 1 em cenarios de queda de rede
- Latencia ponta-a-ponta dos pipelines de dados

---

## 11. Seguranca

### 11.1. Protecao de Credenciais

- Credenciais lidas exclusivamente de variaveis de ambiente
- Arquivo `.env` nao versionado (adicionar ao `.gitignore`)
- Uso de arquivo de senhas do Mosquitto (`passwd`)

### 11.2. Tokenizacao de IDs

A funcao `tokenize_sensor_id()` em `src/config/mqtt_client.py`:

```python
def tokenize_sensor_id(raw_id: str, salt: str = "ind4.0") -> str:
    h = sha256(f"{raw_id}{salt}".encode()).hexdigest()[:12].upper()
    return f"TKN-{h}"
```

- Aplica SHA-256 com salt industrial (ind4.0)
- Gera token de 12 caracteres hexadecimais
- Impede exposicao de metadados da planta industrial

### 11.3. Recomendacoes para Producao

1. Configure TLS/SSL no broker Mosquitto para criptografia do trafego
2. Utilize um cofre de segredos (Hashicorp Vault, AWS Secrets Manager)
3. Restrinja o acesso ao broker por firewall de rede
4. Ative autenticacao por certificado X.509 para os clientes MQTT
5. Monitore o broker com ferramentas como Prometheus + Grafana

---

## 12. Troubleshooting

### 12.1. Erro de Conexao ao Broker

```
Falha na conexao MQTT. Codigo RC=5
```

**Causa:** Autenticacao falhou (usuario/senha incorretos).
**Solucao:** Verifique as credenciais no arquivo `.env` e no arquivo de senhas do Mosquitto.

### 12.2. Container Mosquitto nao Inicia

```
Error: Invalid config
```

**Causa:** Arquivo `mosquitto.conf` mal formatado ou `passwd` inexistente.
**Solucao:** Verifique se o arquivo `passwd` existe em `mosquitto/config/`. Se nao, gere-o:

```bash
docker exec -it mqtt-broker mosquitto_passwd -c /mosquitto/config/passwd iot_simulator
docker restart mqtt-broker
```

### 12.3. Porta 1883 ja em Uso

```
Error starting userland proxy: listen tcp4 0.0.0.0:1883: bind: address already in use
```

**Solucao:** Altere a porta no `docker-compose.yml` ou pare o servico conflitante:

```bash
netstat -ano | findstr :1883
taskkill /PID <PID> /F
```

---

## 13. Licenca

Este projeto esta sob a licenca MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.

---

*Documentacao gerada em 25/05/2026 por L. A. Leandro Sao Jose dos Campos- SP*
