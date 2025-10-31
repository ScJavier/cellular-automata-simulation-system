# 🔬 CASS: Cellular Automata Simulation System

**Estado del Proyecto: En Desarrollo (Data Ingestion Layer)**

Este proyecto implementa el **CASS**, un sistema de microservicios robusto para la **generación, ingesta, y análisis inicial de datos RAW** provenientes de simulaciones de Autómatas Celulares (actualmente, el Juego de la Vida de Conway).

El objetivo es simular un sistema de eventos de alto volumen, donde la data RAW es almacenada de manera auditable antes de cualquier proceso de transformación.

---

## 🏗️ Arquitectura del Stack (Docker Compose)

El CASS está implementado como un conjunto de servicios desacoplados y levantados mediante Docker Compose, lo que garantiza la portabilidad y la reproducibilidad.

| Servicio | Rol Principal | Tecnología | Puerto (Host) |
| :--- | :--- | :--- | :--- |
| **`postgres`** | **Almacenamiento RAW** | PostgreSQL 16 (Alpine) | `5432` |
| **`api`** | **Ingesta y Simulación** | FastAPI / Python 3.8 | `8000` |
| **`frontend`** | **UI de Control y Ejecución** | Streamlit / Python 3.8 | `8501` |

### 📁 Estructura del Repositorio

```bash
/cellular-automata-simulation-system/
├── .env                       # Credenciales de BD y configuración
├── docker-compose.yaml        # Define y conecta los 3 servicios
├── Dockerfile                 # Imagen base para los servicios Python
├── requirements.txt           # Dependencias exactas (FastAPI, Streamlit, etc.)
├── schema_setup.sql           # Script de inicialización de la BD (RAW data model)
├── api_service.py             # Microservicio de ingesta (FastAPI)
├── frontend.py                # UI de control para iniciar experimentos (Streamlit)
├── analyze_experiment.py      # Script de análisis manual (EDA)
└── README.md
```

---

## 🚀 Inicio Rápido (Quick Start)

### 1. Requerimientos

* Docker Desktop (con WSL 2 activado)
* Python 3.8+ (para entorno local)
* Git

### 2. Configuración del Entorno Local

Antes de levantar Docker, asegúrate de que tu archivo `.env` contenga las credenciales que usa la BD:

```bash
# .env (Ejemplo de contenido, usar tus valores reales)
DB_NAME=dev_pipeline_db
DB_USER=de_user
DB_PASSWORD=mi_contrasena_segura_123
```

### 3. Levantamiento del Stack

Este comando construye las imágenes de Python, levanta los 3 servicios y usa el *host* `postgres` para la conexión interna.

```bash
docker compose up --build -d
```

### 4. Acceso al Sistema

Una vez que los servicios estén activos (`docker ps` debe mostrar los 3 contenedores `Up`):

| Componente | URL de Acceso |
| :--- | :--- |
| **UI de Control (Frontend)** | `http://localhost:8501` |
| **API Docs (Swagger)** | `http://localhost:8000/docs` |
| **BD (DBeaver)** | `Host: localhost`, `Port: 5432` |

---

## 📊 Flujo de Trabajo (Uso del Sistema)

1.  **Ingesta de Datos:** Utiliza el **Frontend (puerto 8501)** para definir los parámetros del experimento (tamaño del tablero, pasos) y enviarlo a la API. El Frontend usará el patrón de *polling* para monitorear el estado hasta que el experimento marque `COMPLETED`.
2.  **Auditoría de Datos:** Los datos se almacenan en el esquema `raw_data` de PostgreSQL:
    * `raw_data.experiments`: Metadatos del experimento (ID, duración, nombre).
    * `raw_data.generation_trace`: Traza completa de la simulación (estado RAW del tablero por paso).
3.  **Análisis Manual (EDA):** Puedes analizar la calidad de la ingesta directamente desde tu terminal de WSL.

### Análisis Manual (WSL)

##### Configuración del Entorno Virtual (Local Development)

Antes de trabajar con scripts como `analyze_experiment.py` o correr Streamlit fuera de Docker, configura el entorno virtual:

```bash
# 1. Crear el entorno virtual
python3 -m venv .venv 

# 2. Activar el entorno virtual
source .venv/bin/activate

# 3. Instalar dependencias locales (basadas en requirements.txt)
pip install -r requirements.txt
```

Para correr el script de análisis local, debes cargar las variables de entorno:

```bash
set -a; source ./.env; set +a
```

```bash
python analyze_experiment.py 5
```

---

## 🧹 Limpieza del Entorno

Para detener el stack y eliminar los contenedores y la red:

```bash
docker compose down
```

Para forzar un inicio limpio de la BD (eliminando toda la data persistente):

```bash
docker compose down
```

```bash
docker volume rm [nombre_carpeta_proyecto]_postgres_data
```

```bash
docker compose up --build -d
```