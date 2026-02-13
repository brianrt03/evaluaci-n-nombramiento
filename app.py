import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Evaluación Nombramiento", layout="wide")
st.title("🎓 Sistema de Evaluación para Nombramiento")
st.markdown("Seleccione un colaborador de la lista para desplegar sus criterios de evaluación.")

# --- TU URL DE CONEXIÓN (La misma que configuramos antes) ---
URL_WEBHOOK = "https://script.google.com/macros/s/AKfycbz8OmTf_FryvGNz6mIIBUyVzL8jkXXOBwlWXv4iKsjQji_hZDaUjLKYHQDV5GnA_HgN4g/exec"

# --- CARGA Y LIMPIEZA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        # 1. Cargar Postulantes (separado por comas)
        df_n = pd.read_csv('postulantes.csv', dtype=str)
        
        # 2. Cargar Funciones (separado por punto y coma ';')
        df_f = pd.read_csv('funciones.csv', sep=';', dtype=str)
        
        # --- LIMPIEZA AUTOMÁTICA DE DATOS ---
        
        # A. Estandarizar nombres de columnas (quitar espacios extra)
        df_n.columns = df_n.columns.str.strip()
        df_f.columns = df_f.columns.str.strip()
        
        # B. Renombrar columnas para que coincidan
        # Si la columna se llama "Categoria laboral", la renombramos a "Categoría"
        if 'Categoria laboral' in df_f.columns:
            df_f.rename(columns={'Categoria laboral': 'Categoría'}, inplace=True)
            
        # C. Estandarizar valores dentro de las tablas para que hagan "match"
        
        # Limpieza de textos (quitar espacios al inicio/final)
        df_n['Categoría'] = df_n['Categoría'].str.strip()
        df_f['Categoría'] = df_f['Categoría'].str.strip()
        
        df_n['Tipo de unidad'] = df_n['Tipo de unidad'].str.strip()
        df_f['Tipo de unidad'] = df_f['Tipo de unidad'].str.strip()

        # Corrección de "Técnico" vs "Tecnico"
        df_f['Categoría'] = df_f['Categoría'].replace({'Tecnico': 'Técnico'})
        
        # Corrección de "UNIDADES SUBVENCIONADAS" vs "Subvencionada"
        # Mapeamos lo que dice en funciones para que coincida con postulantes
        mapeo_unidades = {
            'UNIDADES SUBVENCIONADAS': 'Subvencionada',
            'UNIDADES AUTOFINANCIADAS': 'Autofinanciada',
            'FACULTADES Y DEPARTAMENTOS': 'Facultad' 
        }
        df_f['Tipo de unidad'] = df_f['Tipo de unidad'].replace(mapeo_unidades)

        return df_n, df_f

    except FileNotFoundError as e:
        st.error(f"Error: No se encuentra el archivo. {e}")
        return None, None
    except Exception as e:
        st.error(f"Error al cargar archivos: {e}")
        return None, None

df_nombrados, df_funciones = cargar_datos()

if df_nombrados is not None:
    # --- BARRA LATERAL (BUSCADOR) ---
    st.sidebar.header("🔍 Buscar Colaborador")
    
    # Creamos una lista amigable para buscar
    if 'Nombre' in df_nombrados.columns and 'ID' in df_nombrados.columns:
        lista_busqueda = df_nombrados['Nombre'] + " - (ID: " + df_nombrados['ID'] + ")"
        seleccion = st.sidebar.selectbox("Escriba o seleccione:", lista_busqueda)
    else:
        st.error("El archivo 'postulantes.csv' no tiene las columnas 'Nombre' o 'ID'.")
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
        col3.write(f"**Tipo Unidad:** {perfil['Tipo de unidad']}")
        
        st.divider()

        # 3. Filtramos las funciones que le tocan
        funciones_a_evaluar = df_funciones[
            (df_funciones['Categoría'] == perfil['Categoría']) & 
            (df_funciones['Tipo de unidad'] == perfil['Tipo de unidad'])
        ]

        if funciones_a_evaluar.empty:
            st.warning(f"⚠️ No se encontraron criterios para: {perfil['Categoría']} - {perfil['Tipo de unidad']}. (Verifica que estén escritos igual en ambos Excel)")
        else:
            with st.form("form_evaluacion"):
                st.subheader("📋 Criterios a Evaluar")
                datos_para_enviar = []
                
                # 4. Generamos las preguntas dinámicamente
                for index, fila in funciones_a_evaluar.iterrows():
                    # Aquí usamos 'Criterios' porque así se llama en tu archivo nuevo
                    pregunta_texto = fila['Criterios']
                    st.write(f"🔹 **{pregunta_texto}**")
                    
                    tipo_input = str(fila.get('Tipo_Input', 'texto')).strip().lower()
                    key_unico = f"resp_{perfil['ID']}_{index}"

                    if tipo_input == 'si_no':
                        respuesta = st.radio("Seleccione:", ["Sí", "No", "No Aplica"], key=key_unico, horizontal=True)
                    elif tipo_input == 'numero':
                        respuesta = st.number_input("Ingrese cantidad:", min_value=0, step=1, key=key_unico)
                    else:
                        respuesta = st.text_input("Respuesta:", key=key_unico)

                    # Preparamos el paquete de datos
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

            # 5. Envío de datos
            if boton_enviar:
                with st.spinner('Guardando en Google Sheets...'):
                    errores = 0
                    for paquete in datos_para_enviar:
                        paquete['observaciones'] = observaciones
                        try:
                            response = requests.post(URL_WEBHOOK, json=paquete)
                            if response.status_code != 200:
                                errores += 1
                        except Exception as e:
                            errores += 1
                            st.error(f"Error de conexión: {e}")
                    
                    if errores == 0:
                        st.success("¡Evaluación guardada exitosamente! 🎉")
                        st.balloons()
                    else:
                        st.error(f"⚠️ Se guardaron parcialmente los datos. Hubo {errores} errores.")
