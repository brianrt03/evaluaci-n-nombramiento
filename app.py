import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Evaluación Nombramiento", layout="wide")
st.title("🎓 Sistema de Evaluación para Nombramiento")
st.markdown("Seleccione un colaborador de la lista para desplegar sus criterios de evaluación.")

# --- TU URL DE CONEXIÓN (YA INTEGRADA) ---
URL_WEBHOOK = "https://script.google.com/macros/s/AKfycbz8OmTf_FryvGNz6mIIBUyVzL8jkXXOBwlWXv4iKsjQji_hZDaUjLKYHQDV5GnA_HgN4g/exec"

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        # dtype=str es crucial para mantener ceros a la izquierda en IDs
        df_n = pd.read_csv('postulantes.csv', dtype=str) 
        df_f = pd.read_csv('funciones.csv', dtype=str)
        return df_n, df_f
    except FileNotFoundError:
        return None, None

df_nombrados, df_funciones = cargar_datos()

if df_nombrados is None:
    st.error("❌ Error Crítico: No se encuentran los archivos 'nombrados.csv' o 'funciones.csv' en el repositorio.")
else:
    # --- BARRA LATERAL (BUSCADOR) ---
    st.sidebar.header("🔍 Buscar Colaborador")
    
    # Creamos una lista amigable para buscar
    if 'Nombre' in df_nombrados.columns and 'ID' in df_nombrados.columns:
        lista_busqueda = df_nombrados['Nombre'] + " - (ID: " + df_nombrados['ID'] + ")"
        seleccion = st.sidebar.selectbox("Escriba o seleccione:", lista_busqueda)
    else:
        st.error("El archivo 'nombrados.csv' no tiene las columnas 'Nombre' o 'ID'.")
        seleccion = None

    # --- LÓGICA PRINCIPAL ---
    if seleccion:
        # 1. Recuperamos los datos de la persona
        nombre_real = seleccion.split(" - (ID:")[0]
        perfil = df_nombrados[df_nombrados['Nombre'] == nombre_real].iloc[0]

        # 2. Tarjeta de Información Visual
        st.info(f"📂 **Evaluando a:** {perfil['Nombre']}")
        
        col1, col2, col3 = st.columns(3)
        col1.write(f"**ID:** {perfil['ID']}")
        col1.write(f"**Categoría:** {perfil['Categoría']}")
        col2.write(f"**Unidad:** {perfil['Unidad']}")
        col2.write(f"**Sub Unidad:** {perfil['Sub Unidad']}")
        col3.write(f"**Tipo Unidad:** {perfil['Tipo de unidad']}") # Asegúrate que tu CSV tenga esta columna exacta
        
        st.divider()

        # 3. Filtramos las funciones que le tocan
        # ATENCIÓN: Verifica que los nombres de columnas coincidan con tu CSV (Mayúsculas/Minúsculas/Tildes)
        funciones_a_evaluar = df_funciones[
            (df_funciones['Categoria'] == perfil['Categoría']) & 
            (df_funciones['Tipo de unidad'] == perfil['Tipo de unidad'])
        ]

        if funciones_a_evaluar.empty:
            st.warning(f"⚠️ No hay funciones configuradas para el perfil: {perfil['Categoría']} - {perfil['Tipo de unidad']}")
        else:
            with st.form("form_evaluacion"):
                st.subheader("📋 Criterios a Evaluar")
                datos_para_enviar = []
                
                # 4. Generamos las preguntas dinámicamente
                for index, fila in funciones_a_evaluar.iterrows():
                    pregunta_texto = fila['Funcion_Descripcion']
                    st.write(f"🔹 **{pregunta_texto}**")
                    
                    # Detectamos qué tipo de respuesta pide el Excel (si_no, texto, numero)
                    # Usamos .get() por si la columna no existe o está vacía
                    tipo_input = str(fila.get('Tipo_Input', 'texto')).strip().lower()
                    
                    key_unico = f"resp_{perfil['ID']}_{index}"

                    if tipo_input == 'si_no':
                        respuesta = st.radio("Seleccione:", ["Sí", "No", "No Aplica"], key=key_unico, horizontal=True)
                    elif tipo_input == 'numero':
                        respuesta = st.number_input("Ingrese cantidad:", min_value=0, step=1, key=key_unico)
                    else:
                        respuesta = st.text_input("Respuesta:", key=key_unico)

                    # Preparamos el paquete de datos para Google Sheets
                    datos_para_enviar.append({
                        "id": str(perfil['ID']),
                        "nombre": str(perfil['Nombre']),
                        "unidad": str(perfil['Unidad']),
                        "pregunta": str(pregunta_texto),
                        "respuesta": str(respuesta)
                    })
                    st.markdown("---")
                
                observaciones = st.text_area("Observaciones Finales:")
                boton_enviar = st.form_submit_button("✅ Guardar Evaluación")

            # 5. Envío de datos a la Nube (Google Apps Script)
            if boton_enviar:
                with st.spinner('Guardando en Google Sheets...'):
                    errores = 0
                    for paquete in datos_para_enviar:
                        # Agregamos la observación general a cada fila
                        paquete['observaciones'] = observaciones
                        
                        try:
                            # Enviamos los datos a tu URL
                            response = requests.post(URL_WEBHOOK, json=paquete)
                            if response.status_code != 200:
                                errores += 1
                        except Exception as e:
                            errores += 1
                            st.error(f"Error de conexión: {e}")
                    
                    if errores == 0:
                        st.success("¡Evaluación guardada exitosamente en Google Sheets! 🎉")
                        st.balloons()
                    else:
                        st.error(f"⚠️ Se guardaron parcialmente los datos. Hubo {errores} errores de conexión.")
