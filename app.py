import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión de Nombramientos", layout="wide")

# --- TU URL DEL SCRIPT DE GOOGLE ---
URL_WEBHOOK = "https://script.google.com/macros/s/AKfycby9NHgo7U4IUEyAjK0uD9KIAOdnQ0jUXLyi6ksYFul76CZFI7Yt7_lJlrFaLezTAvH1Tg/exec"

# --- FUNCIONES DE CARGA Y CONEXIÓN ---
@st.cache_data
def cargar_datos_maestros():
    """Carga y limpia los archivos CSV locales"""
    try:
        # 1. Cargar Postulantes
        df_n = pd.read_csv('postulantes.csv', dtype=str)
        # 2. Cargar Funciones
        df_f = pd.read_csv('funciones.csv', sep=';', dtype=str)
        
        # --- LIMPIEZA DE COLUMNAS ---
        df_n.columns = df_n.columns.str.strip()
        df_f.columns = df_f.columns.str.strip()
        
        if 'Categoria laboral' in df_f.columns:
            df_f.rename(columns={'Categoria laboral': 'Categoría'}, inplace=True)
            
        # --- LIMPIEZA DE VALORES ---
        for col in ['Categoría', 'Tipo de unidad', 'Unidad', 'Nombre', 'ID']:
            if col in df_n.columns: 
                df_n[col] = df_n[col].astype(str).str.strip()
                df_n[col] = df_n[col].replace('nan', 'SIN DATOS')
            if col in df_f.columns: 
                df_f[col] = df_f[col].astype(str).str.strip()

        # --- ESTANDARIZACIÓN ---
        df_f['Categoría'] = df_f['Categoría'].replace({'Tecnico': 'Técnico'})
        
        # AQUI ESTA EL CAMBIO DEL FILTRO:
        # Mapeamos los nombres cortos del Excel de personas a los nombres LARGOS de funciones
        # Así aparecerá "FACULTADES Y DEPARTAMENTOS" en el filtro
        mapeo_largo = {
            'Subvencionada': 'UNIDADES SUBVENCIONADAS',
            'Autofinanciada': 'UNIDADES AUTOFINANCIADAS',
            'Facultad': 'FACULTADES Y DEPARTAMENTOS',
            'FACULTAD': 'FACULTADES Y DEPARTAMENTOS'
        }
        # Aplicamos el cambio al archivo de PERSONAS (df_n)
        df_n['Tipo de unidad'] = df_n['Tipo de unidad'].replace(mapeo_largo)
        
        # Aseguramos que el archivo de FUNCIONES (df_f) también use los nombres largos
        # (Por si acaso ya venían cortos)
        df_f['Tipo de unidad'] = df_f['Tipo de unidad'].replace(mapeo_largo)
        
        return df_n, df_f
    except Exception as e:
        st.error(f"❌ Error crítico cargando archivos: {e}")
        return None, None

def obtener_ids_evaluados():
    try:
        response = requests.get(URL_WEBHOOK)
        if response.status_code == 200:
            return [str(x) for x in response.json()]
        return []
    except:
        return []

# --- INICIO DE LA APLICACIÓN ---
df_nombrados, df_funciones = cargar_datos_maestros()
ids_ya_evaluados = obtener_ids_evaluados()

if df_nombrados is not None:
    st.title("📊 Dashboard de Evaluación de Nombramiento")

    # ==========================================
    # 1. BARRA LATERAL (FILTROS)
    # ==========================================
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    try:
        # Filtro Unidad
        unidades_unicas = sorted(list(set(df_nombrados['Unidad'].dropna().astype(str).tolist())))
        lista_unidades = ["Todas"] + unidades_unicas
        filtro_unidad = st.sidebar.selectbox("Filtrar por Unidad:", lista_unidades)
        
        # Filtro Tipo de Unidad
        tipos_unicos = sorted(list(set(df_nombrados['Tipo de unidad'].dropna().astype(str).tolist())))
        lista_tipos = ["Todos"] + tipos_unicos
        filtro_tipo = st.sidebar.selectbox("Filtrar por Tipo de Unidad:", lista_tipos)
    except Exception as e:
        st.error(f"Error filtros: {e}")
        filtro_unidad = "Todas"
        filtro_tipo = "Todos"

    # Aplicar filtros
    df_filtrado = df_nombrados.copy()
    if filtro_unidad != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Unidad'] == filtro_unidad]
    if filtro_tipo != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Tipo de unidad'] == filtro_tipo]

    # ==========================================
    # 2. LÓGICA DE ESTADO
    # ==========================================
    df_filtrado['Estado'] = df_filtrado['ID'].apply(lambda x: '✅ Listo' if str(x) in ids_ya_evaluados else '⏳ Pendiente')
    
    df_pendientes = df_filtrado[df_filtrado['Estado'] == '⏳ Pendiente']
    df_listos = df_filtrado[df_filtrado['Estado'] == '✅ Listo']

    # ==========================================
    # 3. KPIs
    # ==========================================
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total Filtrado", len(df_filtrado))
    col2.metric("📝 Pendientes", len(df_pendientes))
    col3.metric("✅ Evaluados", len(df_listos))
    
    if len(df_filtrado) > 0:
        progreso = len(df_listos) / len(df_filtrado)
        st.progress(progreso, text=f"Avance: {int(progreso*100)}%")
    
    st.divider()

    # ==========================================
    # 4. PESTAÑAS
    # ==========================================
    tab_pendientes, tab_historial = st.tabs(["⏳ Lista de Pendientes", "📂 Historial"])

    # --- PESTAÑA A: PENDIENTES ---
    with tab_pendientes:
        if df_pendientes.empty:
            st.success("🎉 ¡No hay pendientes con estos filtros!")
        else:
            lista_para_selector = df_pendientes['Nombre'] + " - (ID: " + df_pendientes['ID'] + ")"
            seleccion = st.selectbox("Seleccione colaborador:", lista_para_selector)
            
            if seleccion:
                id_seleccionado = seleccion.split(" - (ID: ")[1][:-1]
                perfil = df_nombrados[df_nombrados['ID'] == id_seleccionado].iloc[0]

                st.markdown(f"**Evaluando a:** {perfil['Nombre']} | **Unidad:** {perfil['Unidad']}")

                # Buscar funciones (Usando el nombre largo normalizado)
                funciones_persona = df_funciones[
                    (df_funciones['Categoría'] == perfil['Categoría']) & 
                    (df_funciones['Tipo de unidad'] == perfil['Tipo de unidad'])
                ]

                if funciones_persona.empty:
                    st.warning(f"⚠️ No hay funciones para: {perfil['Categoría']} - {perfil['Tipo de unidad']}. (Revisa que coincidan los nombres)")
                else:
                    with st.form("form_eval"):
                        datos_para_enviar = []
                        for idx, fila in funciones_persona.iterrows():
                            criterio = fila['Criterios']
                            tipo_input = str(fila.get('Tipo_Input', 'texto')).strip().lower()
                            
                            st.write(f"🔹 {criterio}")
                            key_widget = f"preg_{perfil['ID']}_{idx}"

                            # CAMBIO REALIZADO: Solo Sí y No
                            if tipo_input == 'si_no':
                                resp = st.radio("Cumple:", ["Sí", "No"], horizontal=True, key=key_widget)
                            elif tipo_input == 'numero':
                                resp = st.number_input("Cantidad:", min_value=0, key=key_widget)
                            else:
                                resp = st.text_input("Respuesta:", key=key_widget)
                            
                            datos_para_enviar.append({
                                "id": str(perfil['ID']), "nombre": str(perfil['Nombre']),
                                "unidad": str(perfil['Unidad']), "pregunta": str(criterio),
                                "respuesta": str(resp)
                            })
                            st.markdown("---")
                        
                        obs = st.text_area("Observaciones:")
                        
                        if st.form_submit_button("💾 Guardar"):
                            with st.spinner("Enviando..."):
                                errores = 0
                                for paquete in datos_para_enviar:
                                    paquete['observaciones'] = obs
                                    try:
                                        res = requests.post(URL_WEBHOOK, json=paquete)
                                        if res.status_code != 200: errores += 1
                                    except: errores += 1
                                
                                if errores == 0:
                                    st.success("✅ ¡Guardado!")
                                    st.cache_data.clear()
                                    st.rerun() # Recarga automática
                                else:
                                    st.error("⚠️ Error de conexión.")

    # --- PESTAÑA B: HISTORIAL ---
    with tab_historial:
        if df_listos.empty:
            st.info("Sin evaluaciones completadas.")
        else:
            st.dataframe(df_listos[['ID', 'Nombre', 'Unidad', 'Categoría', 'Tipo de unidad']], use_container_width=True, hide_index=True)
