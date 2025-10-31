# analyze_experiment.py
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import sys
from typing import Optional
import os

try:
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = os.environ["DB_NAME"]
    DB_USER = os.environ["DB_USER"]
    DB_PASSWORD = os.environ["DB_PASSWORD"]

except KeyError as e:
    print("------------------------------------------------------------------")
    print(f"ERROR FATAL: La variable de entorno {e} no está definida.")
    print("Asegúrate de configurar tu archivo .env o el docker-compose.yaml.")
    print("------------------------------------------------------------------")
    sys.exit(1)


# Crear la URI con las variables leídas
DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_experiment_data(experiment_id: int) -> Optional[pd.DataFrame]:
    """
    Conecta a PostgreSQL usando SQLAlchemy y extrae la traza completa de un experimento.
    """
    engine = None
    try:
        # 1. Crear el Engine de SQLAlchemy
        engine = create_engine(DB_URI)
        print(f"✅ Conexión a la BD (SQLAlchemy) exitosa para Experimento ID: {experiment_id}")
        
        # 2. Consulta SQL para unir metadatos y traza
        query = f"""
        SELECT 
            t.generation_num,
            t.capture_time,
            t.live_cells_count,
            e.name AS experiment_name,
            e.board_size,
            e.duration_seconds
        FROM raw_data.generation_trace t
        JOIN raw_data.experiments e ON t.experiment_id = e.experiment_id
        WHERE t.experiment_id = {experiment_id}
        ORDER BY t.generation_num ASC;
        """
        
        # 3. Leer datos usando el Engine. Pandas ahora usará la conexión recomendada.
        # Aquí ya no pasamos la conexión de psycopg2 (conn), sino el engine de SQLAlchemy
        df = pd.read_sql_query(query, engine) 
        
        if df.empty:
            print(f"⚠️ No se encontraron datos para el Experimento ID {experiment_id}.")
            return None

        return df

    except Exception as e:
        # El manejo de errores de SQLAlchemy es más genérico
        print(f"❌ Error al conectar o ejecutar SQL: {e}")
        return None
    finally:
        # El engine se encarga de cerrar las conexiones automáticamente
        if engine:
             # Opcional: Dispose the engine if it won't be reused for a while
             engine.dispose()
             pass

def basic_eda(df: pd.DataFrame, experiment_id: int):
    """
    Realiza un análisis descriptivo básico y genera un gráfico.
    """
    print("\n--- Análisis Descriptivo ---")
    print(f"Experimento: {df['experiment_name'].iloc[0]}")
    print(f"Tamaño del Tablero: {df['board_size'].iloc[0]}x{df['board_size'].iloc[0]}")
    print(f"Generaciones registradas: {len(df)}")
    print(f"Duración de la simulación: {df['duration_seconds'].iloc[0]} segundos")
    
    print("\nEstadísticas de Células Vivas:")
    print(df['live_cells_count'].describe())
    
    # --- Visualización ---
    
    plt.figure(figsize=(10, 6))
    plt.plot(df['generation_num'], df['live_cells_count'], marker='o', linestyle='-', markersize=2)
    plt.title(f"Evolución de Células Vivas - Experimento ID {experiment_id}")
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
        print("Ejemplo: python analyze_experiment.py 5")
        print("------------------------------------------------------------------")
        sys.exit(1) # Salir con código de error
    
    try:
        # 2. Leer y convertir el primer argumento (sys.argv[1]) a entero
        # sys.argv[0] es el nombre del script (analyze_experiment.py)
        TARGET_EXPERIMENT_ID = int(sys.argv[1])
        
    except ValueError:
        print(f"ERROR: El argumento '{sys.argv[1]}' no es un número entero válido.")
        sys.exit(1)

    print(f"\n🚀 Iniciando análisis del Experimento ID: {TARGET_EXPERIMENT_ID}")
    
    # 3. Ejecutar el análisis con el ID proporcionado
    df_experiment = get_experiment_data(TARGET_EXPERIMENT_ID)
    
    if df_experiment is not None:
        basic_eda(df_experiment, TARGET_EXPERIMENT_ID)
    else:
        print("Finalizando análisis.")