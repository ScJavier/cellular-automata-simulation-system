import streamlit as st
import requests
import json
import datetime # Importación necesaria para datetime.now()
import time      # Importación necesaria para time.sleep()
import os

# --- Configuración ---
API_HOST = os.environ.get("API_HOST", None)

# --- Estructura de la Interfaz ---

st.set_page_config(page_title="Conway Data Generator", layout="centered")
st.title("🔬 Plataforma de Generación de Datos RAW")
st.subheader("Simulación y Registro de Experimentos de Autómatas Celulares")

# Definimos el nombre por defecto aquí
default_name = "Corrida_Automatica_" + datetime.datetime.now().strftime("%Y%m%d_%H%M")

# --- Formulario de Configuración de Experimento ---

with st.form("experiment_form"):
    st.markdown("### Configuración del Experimento")
    
    # Parámetros de la API
    experiment_name = st.text_input(
        "Nombre del Experimento", 
        value=default_name,
        help="Nombre descriptivo para la BD."
    )
    board_size = st.slider(
        "Tamaño del Tablero (N x N)", 
        min_value=10, max_value=100, value=25, step=5,
        help="Dimensión del tablero (ej: 25x25)."
    )
    num_steps = st.slider(
        "Número de Pasos/Generaciones", 
        min_value=10, max_value=200, value=50, step=10,
        help="Total de iteraciones de la simulación a registrar."
    )
    initial_density = st.slider(
        "Densidad Inicial de Población", 
        min_value=0.1, max_value=0.9, value=0.4, step=0.05,
        help="Porcentaje de celdas vivas al inicio (0.1 a 0.9)."
    )
    
    # Botón de envío
    submitted = st.form_submit_button("🚀 Iniciar Experimento y Guardar RAW")

# --- Lógica de Envío ---

if submitted:
    # 1. Preparar la carga útil (Payload)
    payload = {
        "name": experiment_name,
        "board_size": board_size,
        "num_steps": num_steps,
        "initial_density": initial_density
    }
    
    # Placeholder para mostrar el estado en tiempo real
    status_placeholder = st.empty() 
    
    try:
        # 2. Llamada a la API para iniciar (POST /run_experiment)
        status_placeholder.info(f"Enviando solicitud para iniciar: {API_HOST}/run_experiment")
        response = requests.post(f"{API_HOST}/run_experiment", json=payload)
        
        # --- Solución Robusta: Verificar respuesta de la API ---
        if response.status_code != 200:
            # Si falla, muestra el error de la API y no continúa con el polling
            status_placeholder.error(f"❌ Error al iniciar (Código {response.status_code}): {response.json().get('detail', 'Error desconocido')}")
        else:
            # Si es exitoso, inicia el Polling
            result = response.json()
            exp_id = result.get("experiment_id")
            
            # --- INICIO DEL POLLING ---
            
            status_placeholder.warning(f"⏳ Experimento **#{exp_id}** iniciado. Monitoreando estado...")
            
            status_loop = True
            # progress_bar = st.progress(0) # Desactivado temporalmente ya que la API no reporta pasos completados
            
            while status_loop:
                time.sleep(1) # Espera 1 segundo entre consultas (Polling Interval)
                
                # Consultar el estado
                status_response = requests.get(f"{API_HOST}/status/{exp_id}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data['status']
                    
                    if current_status == 'COMPLETED':
                        # progress_bar.progress(100)
                        duration = status_data.get('duration_seconds')
                        st.balloons() # Celebración visual
                        status_placeholder.success(f"🎉 **Experimento #{exp_id} COMPLETADO** en {duration} segundos.")
                        
                        st.markdown("---")
                        st.subheader(f"Resultados del Experimento #{exp_id}")
                        st.json(status_data)
                        status_loop = False
                    
                    elif current_status == 'FAILED':
                        # progress_bar.progress(100)
                        status_placeholder.error(f"❌ Experimento #{exp_id} FALLÓ. Revisa los logs de la API y la BD.")
                        st.json(status_data)
                        status_loop = False
                    
                    else: # RUNNING
                        # Muestra el estado actual mientras corre
                        status_placeholder.warning(f"⏳ Experimento #{exp_id} en curso (Status: {current_status})... Pasos: {status_data['total_steps']}")
                        
                else:
                    status_placeholder.error("Error al consultar el estado de la API.")
                    status_loop = False
                    
    except requests.exceptions.ConnectionError:
        status_placeholder.error(f"🚨 **¡Error de Conexión!** Asegúrate de que tu API (uvicorn) esté corriendo en {API_HOST}.")
    except Exception as e:
        status_placeholder.error(f"Ocurrió un error inesperado en el frontend: {e}")

# --- Información Adicional ---

st.markdown("---")
st.caption("Nota: La API ejecuta la simulación de forma asíncrona, el frontend monitorea el estado a través del endpoint `/status/{id}`.")