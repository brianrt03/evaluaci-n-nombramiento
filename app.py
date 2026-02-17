import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión de Nombramientos", layout="wide")

# --- TU URL (MANTENEMOS LA MISMA) ---
URL_WEBHOOK = "https://script.google.com/macros/s/AKfycbxQupYHGTRkYEQzxO3bsgMOGRxaHLyEFs_gRmlBzNet2O7ilB33v1ndKmJRQC9DcJNo0Q/exec"

# --- FUNCIONES DE CARGA Y CONEXIÓN ---
@st.cache_data
def cargar_datos_maestros():
    """Carga y limpia los archivos CSV locales"""
    try:
        # 1. Cargar CSVs
        df_n = pd.read_csv('postulantes.csv', dtype=str)
        df_f = pd.read_csv('funciones.csv', sep=';', dtype=str)
        
        # --- LIMPIEZA DE COLUMNAS ---
        df_n.columns = df_n.columns.str.strip()
        df_f.columns = df_f.columns.str.strip()
        
        if 'Categoria laboral' in df_f.columns:
            df_f.rename(columns={'Categoria laboral': 'Categoría'}, inplace=True)
            
        # --- LIMPIEZA DE VALORES ---
        for col in ['Categoría', 'Tipo de unidad', 'Unidad', 'Nombre', 'ID', 'Posición']:
            if col in df_n.columns: 
                df_n[col] = df_n[col].astype(str).str.strip()
                df_n[col] = df_n[col].replace('nan', 'SIN DATOS')
            if col in df_f.columns: 
                df_f[col] = df_f[col].astype(str).str.strip()

        # --- ESTANDARIZACIÓN (MAPEO ROBUSTO) ---
        df_f['Categoría'] = df_f['Categoría'].replace({'Tecnico': 'Técnico'})
        
        # CAMBIO 1: MAPEO AMPLIADO PARA QUE APAREZCAN LAS FACULTADES
        # Agregamos todas las variantes posibles que puedan venir en el Excel
        mapeo_largo = {
            'Subvencionada': 'UNIDADES SUBVENCIONADAS',
            'Autofinanciada': 'UNIDADES AUTOFINANCIADAS',
            'Facultades y departamentos': 'FACULTADES Y DEPARTAMENTOS',

        }
        
        # Aplicamos el mapeo (si no encuentra la clave, deja el valor original)
        df_n['Tipo de unidad'] = df_n['Tipo de unidad'].replace(mapeo_largo)
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
    
    # Filtro 1: Tipo de Unidad
    tipos_unicos = sorted(list(set(df_nombrados['Tipo de unidad'].dropna().astype(str).tolist())))
    lista_tipos = ["Todos"] + tipos_unicos
    filtro_tipo = st.sidebar.selectbox("1. Tipo de Unidad:", lista_tipos)

    # Lógica de cascada para Filtro 2
    df_para_unidades = df_nombrados.copy()
    if filtro_tipo != "Todos":
        df_para_unidades = df_para_unidades[df_para_unidades['Tipo de unidad'] == filtro_tipo]
    
    # Filtro 2: Unidad
    unidades_disponibles = sorted(list(set(df_para_unidades['Unidad'].dropna().astype(str).tolist())))
    lista_unidades = ["Todas"] + unidades_disponibles
    filtro_unidad = st.sidebar.selectbox("2. Unidad:", lista_unidades)

    # Aplicar filtros
    df_filtrado = df_nombrados.copy()
    if filtro_tipo != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Tipo de unidad'] == filtro_tipo]
    if filtro_unidad != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Unidad'] == filtro_unidad]

    # ==========================================
    # 2. ESTADO Y KPIs
    # ==========================================
    df_filtrado['Estado'] = df_filtrado['ID'].apply(lambda x: '✅ Listo' if str(x) in ids_ya_evaluados else '⏳ Pendiente')
    
    df_pendientes = df_filtrado[df_filtrado['Estado'] == '⏳ Pendiente']
    df_listos = df_filtrado[df_filtrado['Estado'] == '✅ Listo']

    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Filtrados", len(df_filtrado))
    col2.metric("📝 Pendientes", len(df_pendientes))
    col3.metric("✅ Evaluados", len(df_listos))
    
    if len(df_filtrado) > 0:
        progreso = len(df_listos) / len(df_filtrado)
        st.progress(progreso, text=f"Avance: {int(progreso*100)}%")
    
    st.divider()

    # ==========================================
    # 3. ZONA DE TRABAJO
    # ==========================================
    tab_pendientes, tab_historial = st.tabs(["⏳ Evaluar Pendientes", "📂 Historial Evaluados"])

    with tab_pendientes:
        if df_pendientes.empty:
            st.success("🎉 ¡No hay personas pendientes con los filtros seleccionados!")
        else:
            # Filtro 3: Nombre
            st.markdown("##### 3. Seleccione al Colaborador:")
            lista_nombres = df_pendientes['Nombre'] + " - (ID: " + df_pendientes['ID'] + ")"
            seleccion = st.selectbox("Buscar por nombre:", lista_nombres, label_visibility="collapsed")
            
            if seleccion:
                id_seleccionado = seleccion.split(" - (ID: ")[1][:-1]
                perfil = df_nombrados[df_nombrados['ID'] == id_seleccionado].iloc[0]

                st.info(f"**{perfil['Nombre']}** | {perfil['Categoría']} | {perfil['Posición']} | {perfil['Unidad']}")

                funciones_persona = df_funciones[
                    (df_funciones['Categoría'] == perfil['Categoría']) & 
                    (df_funciones['Tipo de unidad'] == perfil['Tipo de unidad'])
                ]

                if funciones_persona.empty:
                    st.warning(f"⚠️ No hay funciones para: {perfil['Categoría']} - {perfil['Tipo de unidad']}")
                else:
                    with st.form("form_eval"):
                        detalles_respuestas = [] 
                        
                        for idx, fila in funciones_persona.iterrows():
                            criterio = fila['Criterios']
                            tipo_input = str(fila.get('Tipo_Input', 'texto')).strip().lower()
                            
                            st.write(f"🔹 {criterio}")
                            key_widget = f"preg_{perfil['ID']}_{idx}"

                            # CAMBIO 2: PREDETERMINADO EN "NO"
                            # index=0 es "Sí", index=1 es "No"
                            if tipo_input == 'si_no':
                                resp = st.radio("Cumple:", ["Sí", "No"], index=1, horizontal=True, key=key_widget)
                            elif tipo_input == 'numero':
                                resp = st.number_input("Cantidad:", min_value=0, key=key_widget)
                            else:
                                resp = st.text_input("Respuesta:", key=key_widget)
                            
                            detalles_respuestas.append({
                                "pregunta": str(criterio),
                                "respuesta": str(resp)
                            })
                            st.markdown("---")
                        
                        # CAMBIO 3: OBSERVACIONES QUE SE LIMPIAN
                        # Al incluir el ID en la "key", Streamlit crea una caja nueva para cada persona
                        obs = st.text_area("Observaciones Finales:", key=f"obs_{perfil['ID']}")
                        
                        if st.form_submit_button("💾 Guardar Evaluación Completa"):
                            payload_completo = {
                                "id": str(perfil['ID']),
                                "nombre": str(perfil['Nombre']),
                                "unidad": str(perfil['Unidad']),
                                "categoria": str(perfil['Categoría']),
                                "tipo_unidad": str(perfil['Tipo de unidad']),
                                "observaciones": obs,
                                "detalles": detalles_respuestas 
                            }
                            
                            with st.spinner("Guardando..."):
                                try:
                                    res = requests.post(URL_WEBHOOK, json=payload_completo)
                                    if res.status_code == 200:
                                        st.success("✅ ¡Registro guardado!")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(f"Error servidor: {res.status_code}")
                                except Exception as e:
                                    st.error(f"Error conexión: {e}")

    with tab_historial:
        if df_listos.empty:
            st.info("Sin evaluaciones completadas.")
        else:
            st.dataframe(df_listos[['ID', 'Nombre', 'Unidad', 'Categoría', 'Tipo de unidad']], use_container_width=True, hide_index=True)
