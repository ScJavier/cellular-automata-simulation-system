# api_service.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import numpy as np
import datetime
import time
import json
import asyncio

import os

from typing import List

# --- Configuración de la BD (Ajusta a tus valores) ---
DB_HOST = os.environ.get("DB_HOST", None)
DB_PORT = os.environ.get("DB_PORT", None)
DB_NAME = os.environ.get("DB_NAME", None)
DB_USER = os.environ.get("DB_USER", None)
DB_PASSWORD = os.environ.get("DB_PASSWORD", None)

app = FastAPI(title="Conway Data Generator API")

# --- Esquemas de Datos para la API (Pydantic) ---

class ExperimentConfig(BaseModel):
    name: str = "Juego de la Vida (B3/S23)"
    board_size: int = 20
    num_steps: int = 50
    initial_density: float = 0.5 # 0.0 a 1.0
    survival_rules: List[int] = [2, 3]
    birth_rules: List[int] = [3]
    rules_notation: str = "B3/S23"

# --- Lógica de la Simulación ---
def next_generation(board: np.ndarray, survival_rules: List[int], birth_rules: List[int]) -> np.ndarray:
    """Calcula la próxima generación del AC basándose en las reglas S/B."""
    size = board.shape[0]
    new_board = np.zeros(board.shape, dtype=int)
    
    for i in range(size):
        for j in range(size):
            # Contar vecinos vivos (usando toroidales para bordes) - La lógica de conteo es la misma
            # NOTA: Mejorar a conteo toroidal si quieres reglas que manejen los bordes de manera especial.
            total_live = np.sum(board[max(0, i-1):i+2, max(0, j-1):j+2]) - board[i, j]
            
            # Aplicar las reglas S/B
            if board[i, j] == 1:
                # REGLA DE SUPERVIVENCIA: Si está viva, debe cumplir las reglas de supervivencia para seguir viva
                if total_live in survival_rules:
                    new_board[i, j] = 1 # Sobrevive
                else:
                    new_board[i, j] = 0 # Muere
            else:
                # REGLA DE NACIMIENTO: Si está muerta, debe cumplir las reglas de nacimiento para nacer
                if total_live in birth_rules:
                    new_board[i, j] = 1 # Nace
                else:
                    new_board[i, j] = 0 # Permanece muerta
                    
    return new_board

def get_db_connection():
    """Retorna una nueva conexión a la BD."""
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

# --- Endpoints de la API ---

@app.get("/")
def read_root():
    return {"status": "Service Running", "project": "Conway Data Generator"}

@app.post("/run_experiment")
async def run_experiment(config: ExperimentConfig):
    """
    Endpoint para iniciar una simulación y guardarla en la BD.
    Se ejecuta en segundo plano para no bloquear la API.
    """
    
    # 1. Crear el registro del experimento (INSERT en raw_data.experiments)
    conn = None
    experiment_id = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        start_time = datetime.datetime.now(datetime.timezone.utc)
        
        # Inicializar tablero aleatorio basado en la densidad
        initial_board = np.random.choice(
            a=[0, 1], 
            size=(config.board_size, config.board_size), 
            p=[1-config.initial_density, config.initial_density]
        )
        
        # Insertar experimento inicial
        cur.execute(
            """INSERT INTO raw_data.experiments 
               (name, board_size, num_steps, initial_config, start_time, rules_notation, survival_rules, birth_rules) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING experiment_id;""",
            (config.name, config.board_size, config.num_steps, str(initial_board.tolist()), start_time, 
             config.rules_notation, str(config.survival_rules).strip('[]'), str(config.birth_rules).strip('[]'))
        )
        experiment_id = cur.fetchone()[0]
        conn.commit()
        
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error during setup: {e}")
    finally:
        if conn: conn.close()

    # 2. Ejecutar la simulación en un proceso que no bloquee la API (Future/Task)
    asyncio.create_task(
        simulate_and_insert(
            experiment_id, 
            config.num_steps, 
            initial_board, 
            config.survival_rules,
            config.birth_rules
        )
    )
    
    return {"message": "Experiment started in background", "experiment_id": experiment_id}


@app.get("/status/{experiment_id}")
def get_experiment_status(experiment_id: int):
    """Consulta el estado, la duración y los metadatos de un experimento."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """SELECT status, duration_seconds, num_steps, start_time, end_time
               FROM raw_data.experiments 
               WHERE experiment_id = %s;""",
            (experiment_id,)
        )
        result = cur.fetchone()
        
        if result is None:
            raise HTTPException(status_code=404, detail=f"Experiment ID {experiment_id} not found.")

        # Devuelve el estado y las métricas clave
        status, duration, steps, start_time, end_time = result
        
        return {
            "experiment_id": experiment_id,
            "status": status,
            "total_steps": steps,
            "duration_seconds": round(float(duration), 2) if duration else None,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        if conn: conn.close()


async def simulate_and_insert(
    experiment_id: int,
    num_steps: int,
    initial_board: np.ndarray,
    survival_rules: List[int],
    birth_rules: List[int]
    ):
    """Lógica de simulación asíncrona e ingesta."""
    conn = None
    board = initial_board
    step_delay = 0.5 # Retraso de 0.5 segundos por paso
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # --- SOLUCIÓN: Recuperar el start_time de la BD ---
        cur.execute("SELECT start_time FROM raw_data.experiments WHERE experiment_id = %s;", (experiment_id,))
        experiment_data = cur.fetchone()
        if not experiment_data:
            raise Exception(f"Experiment ID {experiment_id} not found.")
        start_time = experiment_data[0]
        # ----------------------------------------------------

        for step in range(num_steps):
            
            # 1. Simular y calcular métricas RAW
            current_time = datetime.datetime.now(datetime.timezone.utc)
            live_cells_count = int(np.sum(board))
            
            # 2. Ingesta de la Traza (raw_data.generation_trace)
            cur.execute(
                """INSERT INTO raw_data.generation_trace 
                   (experiment_id, generation_num, capture_time, board_state, live_cells_count)
                   VALUES (%s, %s, %s, %s, %s);""",
                (experiment_id, step, current_time, str(board.tolist()), live_cells_count)
            )
            conn.commit()
            
            # 3. Calcular la próxima generación y esperar
            board = next_generation(board, survival_rules, birth_rules)
            await asyncio.sleep(step_delay) # Espera asíncrona

        # 4. Actualizar el estado final del experimento
        end_time = datetime.datetime.now(datetime.timezone.utc)
        # --- SOLUCIÓN: start_time ya está definido aquí ---
        duration = (end_time - start_time).total_seconds() 
        # --------------------------------------------------
        
        cur.execute(
            """UPDATE raw_data.experiments 
               SET end_time = %s, duration_seconds = %s, status = 'COMPLETED'
               WHERE experiment_id = %s;""",
            (end_time, duration, experiment_id)
        )
        conn.commit()
        
        print(f"INFO: Experimento {experiment_id} finalizado y actualizado.")

    except Exception as e:
        # En caso de fallo, registrar y actualizar el estado
        print(f"FATAL ERROR en Experimento {experiment_id}: {e}")
        if conn:
            cur = conn.cursor()
            cur.execute("UPDATE raw_data.experiments SET status = 'FAILED' WHERE experiment_id = %s;", (experiment_id,))
            conn.commit()
            
    finally:
        if conn: conn.close()