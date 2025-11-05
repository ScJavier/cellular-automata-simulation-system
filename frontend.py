import streamlit as st
import requests
import json
import datetime # Importación necesaria para datetime.now()
import time      # Importación necesaria para time.sleep()
import os
import re
from typing import Optional, List

# --- Configuración (LEER DE VARIABLES DE ENTORNO) ---
try:
    API_HOST = os.environ["API_HOST"]
except KeyError:
    st.error("🚨 ERROR FATAL: La variable de entorno 'API_HOST' no está definida.")
    st.stop()


# --- Funciones de Utilidad ---

def parse_rules(rules_str: str) -> Optional[List[int]]:
    """Convierte una cadena de reglas (ej: '2,3') a una lista de enteros."""
    if not rules_str:
        return []
    
    # Limpia la cadena y acepta solo dígitos y comas
    cleaned_str = re.sub(r'[^\d,]', '', rules_str)
    
    try:
        # Convierte cada número a entero y filtra los vacíos
        return [int(n.strip()) for n in cleaned_str.split(',') if n.strip()]
    except ValueError:
        return None # Indica un fallo en el parsing


# --- Estructura de la Interfaz ---

st.set_page_config(page_title="Conway Data Generator", layout="centered")
st.title("🔬 Plataforma de Generación de Datos RAW")
st.subheader("Simulación y Registro de Experimentos de Autómatas Celulares")

# Definimos el nombre por defecto aquí
default_name = "Corrida_Automatica_" + datetime.datetime.now().strftime("%Y%m%d_%H%M")


# --- Formulario de Configuración de Experimento ---

with st.form("experiment_form"):
    st.markdown("### 1. Parámetros de la Simulación")
    
    experiment_name = st.text_input("Nombre del Experimento", value=default_name)
    
    col_size, col_steps, col_density = st.columns(3)
    
    with col_size:
        board_size = st.slider("Tamaño del Tablero", min_value=10, max_value=100, value=25, step=5)
    with col_steps:
        num_steps = st.slider("Número de Pasos/Generaciones", min_value=10, max_value=200, value=50, step=10)
    with col_density:
        initial_density = st.slider("Densidad Inicial", min_value=0.1, max_value=0.9, value=0.4, step=0.05)
    
    st.markdown("---")
    st.markdown("### 2. Reglas del Autómata Celular (Notación S/B)")
    
    col_survival, col_birth = st.columns(2)
    
    with col_survival:
        survival_rules_str = st.text_input(
            "Reglas de Supervivencia (S)", 
            value="2,3", 
            help="Números de vecinos para que una célula VIVA sobreviva. Ej: '2,3' (Conway)."
        )
    
    with col_birth:
        birth_rules_str = st.text_input(
            "Reglas de Nacimiento (B)", 
            value="3", 
            help="Números de vecinos para que una célula MUERTA nazca. Ej: '3' (Conway)."
        )
    
    st.markdown("---")
    submitted = st.form_submit_button("🚀 Iniciar Experimento Configurable")


# --- Lógica de Envío ---

if submitted:
    
    # Validar y parsear las reglas
    survival_rules = parse_rules(survival_rules_str)
    birth_rules = parse_rules(birth_rules_str)
    
    if survival_rules is None or birth_rules is None:
        st.error("❌ Error: Las reglas de Supervivencia o Nacimiento contienen caracteres no válidos (solo se permiten números y comas).")
        st.stop()

    # Construir la notación S/B para la auditoría en la BD
    rules_notation = f"B{','.join(map(str, birth_rules))}/S{','.join(map(str, survival_rules))}"
    
    # 1. Preparar la carga útil (Payload)
    payload = {
        "name": experiment_name,
        "board_size": board_size,
        "num_steps": num_steps,
        "initial_density": initial_density,
        "survival_rules": survival_rules,    # Pasa la lista[int]
        "birth_rules": birth_rules,          # Pasa la lista[int]
        "rules_notation": rules_notation     # Pasa la notación para la BD
    }
    
    # Placeholder para mostrar el estado en tiempo real
    status_placeholder = st.empty() 
    
    try:
        # 2. Llamada a la API para iniciar (POST /run_experiment)
        status_placeholder.info(f"Enviando solicitud para iniciar: {API_HOST}/run_experiment con reglas: {rules_notation}")
        response = requests.post(f"{API_HOST}/run_experiment", json=payload)
        
        # ... (El resto de la lógica de polling y manejo de errores permanece igual) ...
        # (Espera que hayas pegado la lógica de polling corregida de un paso anterior)
        
        if response.status_code != 200:
            status_placeholder.error(f"❌ Error al iniciar (Código {response.status_code}): {response.json().get('detail', 'Error desconocido')}")
        else:
            result = response.json()
            exp_id = result.get("experiment_id")
            
            # --- INICIO DEL POLLING ---
            
            status_placeholder.warning(f"⏳ Experimento **#{exp_id}** iniciado ({rules_notation}). Monitoreando estado...")
            
            status_loop = True
            
            while status_loop:
                time.sleep(1) 
                
                status_response = requests.get(f"{API_HOST}/status/{exp_id}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data['status']
                    
                    if current_status == 'COMPLETED':
                        duration = status_data.get('duration_seconds')
                        st.balloons() 
                        status_placeholder.success(f"🎉 **Experimento #{exp_id} COMPLETADO** ({rules_notation}) en {duration} segundos.")
                        
                        st.markdown("---")
                        st.subheader(f"Metadatos Registrados")
                        st.json(status_data)
                        status_loop = False
                    
                    elif current_status == 'FAILED':
                        status_placeholder.error(f"❌ Experimento #{exp_id} FALLÓ. Revisa los logs de la API.")
                        st.json(status_data)
                        status_loop = False
                    
                    else: # RUNNING
                        status_placeholder.warning(f"⏳ Experimento #{exp_id} en curso (Status: {current_status})...")
                        
                else:
                    status_placeholder.error("Error al consultar el estado de la API.")
                    status_loop = False
                    
    except requests.exceptions.ConnectionError:
        status_placeholder.error(f"🚨 **¡Error de Conexión!** Asegúrate de que tu API (uvicorn) esté corriendo en {API_HOST}.")
    except Exception as e:
        status_placeholder.error(f"Ocurrió un error inesperado en el frontend: {e}")

# --- Información Adicional ---

st.markdown("---")
st.caption(f"API Host: {API_HOST}. Nota: La API ejecuta la simulación de forma asíncrona.")