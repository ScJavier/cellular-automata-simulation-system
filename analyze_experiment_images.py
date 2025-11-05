# analyze_experiment.py - Versión con Animación y Reglas

import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import sys
from typing import Optional, List
import os
from dotenv import load_dotenv, find_dotenv
import numpy as np
import ast # Necesario para deserializar la cadena del tablero
import imageio.v2 as imageio # Para crear el GIF

load_dotenv(find_dotenv())

try:
    # Nota: Usaremos 'localhost' aquí porque el script corre en WSL (Host)
    DB_HOST = 'localhost' 
    DB_PORT = 5432
    DB_NAME = os.environ["DB_NAME"]
    DB_USER = os.environ["DB_USER"]
    DB_PASSWORD = os.environ["DB_PASSWORD"]

except KeyError as e:
    print("------------------------------------------------------------------")
    print(f"ERROR FATAL: La variable de entorno {e} no está definida.")
    print("------------------------------------------------------------------")
    sys.exit(1)


# Crear la URI con las variables leídas
DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_experiment_data(experiment_id: int) -> Optional[pd.DataFrame]:
    """
    Conecta a PostgreSQL, extrae la traza completa, las reglas y el estado RAW.
    """
    engine = None
    try:
        engine = create_engine(DB_URI)
        print(f"✅ Conexión a la BD (SQLAlchemy) exitosa para Experimento ID: {experiment_id}")
        
        # 2. Consulta SQL con las nuevas columnas de configuración
        query = f"""
        SELECT 
            t.generation_num,
            t.capture_time,
            t.live_cells_count,
            t.board_state, -- <--- ¡IMPORTANTE: Extrayendo el estado RAW!
            e.name AS experiment_name,
            e.board_size,
            e.duration_seconds,
            e.rules_notation, -- <--- NUEVAS COLUMNAS
            e.survival_rules,
            e.birth_rules
        FROM raw_data.generation_trace t
        JOIN raw_data.experiments e ON t.experiment_id = e.experiment_id
        WHERE t.experiment_id = {experiment_id}
        ORDER BY t.generation_num ASC;
        """
        
        df = pd.read_sql_query(query, engine) 
        
        if df.empty:
            print(f"⚠️ No se encontraron datos para el Experimento ID {experiment_id}.")
            return None

        return df

    except Exception as e:
        print(f"❌ Error al conectar o ejecutar SQL: {e}")
        return None
    finally:
        if engine:
             engine.dispose()
             pass


def create_simulation_gif(df: pd.DataFrame, experiment_id: int):
    """
    Deserializa el estado del tablero en cada generación y crea un GIF animado.
    """
    output_filename = f"simulation_{experiment_id}.gif"
    frames = []
    
    # 1. Configuración de la figura para la animación
    fig, ax = plt.subplots(figsize=(6, 6))
    plt.title(f"ID {experiment_id} - Reglas: {df['rules_notation'].iloc[0]}")
    
    # El tamaño del tablero es constante
    board_size = df['board_size'].iloc[0]
    
    print(f"\n🎬 Generando animación del tablero (Guardando en {output_filename})...")
    
    for index, row in df.iterrows():
        try:
            # Deserializar la cadena del tablero a una lista de listas de Python
            board_list = ast.literal_eval(row['board_state'])
            board_array = np.array(board_list, dtype=int)
            
            # 2. Renderizar el tablero
            ax.clear()
            ax.imshow(board_array, cmap='binary', interpolation='nearest')
            ax.set_title(f"Generación: {row['generation_num']} | Células: {row['live_cells_count']}", fontsize=10)
            ax.set_xticks(np.arange(-0.5, board_size, 1), minor=True)
            ax.set_yticks(np.arange(-0.5, board_size, 1), minor=True)
            ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5)
            ax.tick_params(which='minor', size=0)
            ax.set_yticklabels([])
            ax.set_xticklabels([])
            
            # 3. Capturar el Frame
            fig.canvas.draw()
            image = np.frombuffer(fig.canvas.tostring_rgb(), dtype='uint8')
            image = image.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            frames.append(image)
            
        except Exception as e:
            print(f"Error al procesar la generación {row['generation_num']}: {e}")
            continue

    plt.close(fig) # Cerrar la figura para liberar memoria
    
    # 4. Crear el GIF
    imageio.mimsave(output_filename, frames, fps=5) # 5 frames por segundo (ajústalo a tu gusto)
    print(f"✅ Animación guardada exitosamente en {output_filename}")


def basic_eda(df: pd.DataFrame, experiment_id: int):
    """
    Realiza un análisis descriptivo básico y genera el gráfico de población.
    """
    print("\n--- Análisis Descriptivo ---")
    print(f"Experimento: {df['experiment_name'].iloc[0]}")
    print(f"Reglas: {df['rules_notation'].iloc[0]} (S: {df['survival_rules'].iloc[0]}, B: {df['birth_rules'].iloc[0]})") # <--- LÍNEA MEJORADA
    print(f"Tamaño del Tablero: {df['board_size'].iloc[0]}x{df['board_size'].iloc[0]}")
    print(f"Generaciones registradas: {len(df)}")
    print(f"Duración de la simulación: {df['duration_seconds'].iloc[0]} segundos")
    
    print("\nEstadísticas de Células Vivas:")
    print(df['live_cells_count'].describe())
    
    # --- Visualización de Población (Gráfico estático) ---
    
    plt.figure(figsize=(10, 6))
    plt.plot(df['generation_num'], df['live_cells_count'], marker='o', linestyle='-', markersize=2)
    plt.title(f"Evolución de Células Vivas - Experimento ID {experiment_id} | Reglas: {df['rules_notation'].iloc[0]}")
    plt.xlabel("Número de Generación (Paso)")
    plt.ylabel("Células Vivas (live_cells_count)")
    plt.grid(True)
    plt.show()


# --- Ejecución Principal ---
if __name__ == "__main__":
    
    # 1. Verificar si el ID del experimento fue proporcionado
    if len(sys.argv) < 2:
        print("------------------------------------------------------------------")
        print("ERROR: Debe proporcionar el ID del experimento como argumento.")
        print("Uso: python analyze_experiment.py <experiment_id>")
        print("------------------------------------------------------------------")
        sys.exit(1)
    
    try:
        TARGET_EXPERIMENT_ID = int(sys.argv[1])
        
    except ValueError:
        print(f"ERROR: El argumento '{sys.argv[1]}' no es un número entero válido.")
        sys.exit(1)

    print(f"\n🚀 Iniciando análisis del Experimento ID: {TARGET_EXPERIMENT_ID}")
    
    df_experiment = get_experiment_data(TARGET_EXPERIMENT_ID)
    
    if df_experiment is not None:
        basic_eda(df_experiment, TARGET_EXPERIMENT_ID)
        create_simulation_gif(df_experiment, TARGET_EXPERIMENT_ID) # <--- ¡Nueva función de animación!
    else:
        print("Finalizando análisis.")