import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión de Nombramientos", layout="wide")

# --- TU NUEVA URL ---
URL_WEBHOOK = "https://script.google.com/macros/s/AKfycby9NHgo7U4IUEyAjK0uD9KIAOdnQ0jUXLyi6ksYFul76CZFI7Yt7_lJlrFaLezTAvH1Tg/exec"

# --- FUNCIONES DE CARGA Y CONEXIÓN ---
@st.cache_data
def cargar_datos_maestros():
    """Carga y limpia los archivos CSV locales"""
    try:
        # 1. Cargar Postulantes (separado por comas)
        df_n = pd.read_csv('postulantes.csv', dtype=str)
        # 2. Cargar Funciones (separado por punto y coma)
        df_f = pd.read_csv('funciones.csv', sep=';', dtype=str)
        
        # --- LIMPIEZA DE COLUMNAS ---
        df_n.columns = df_n.columns.str.strip()
        df_f.columns = df_f.columns.str.strip()
        
        # Renombrar columna de funciones si es necesario
        if 'Categoria laboral' in df_f.columns:
            df_f.rename(columns={'Categoria laboral': 'Categoría'}, inplace=True)
            
        # --- LIMPIEZA DE VALORES (TRIM) ---
        for col in ['Categoría', 'Tipo de unidad']:
            if col in df_n.columns: df_n[col] = df_n[col].str.strip()
            if col in df_f.columns: df_f[col] = df_f[col].str.strip()

        # --- ESTANDARIZACIÓN DE TEXTOS ---
        # Corrección Técnico vs Tecnico
        df_f['Categoría'] = df_f['Categoría'].replace({'Tecnico': 'Técnico'})
        
        # Corrección Unidades
        mapeo_unidades = {
            'UNIDADES SUBVENCIONADAS': 'Subvencionada',
            'UNIDADES AUTOFINANCIADAS': 'Autofinanciada',
            'FACULTADES Y DEPARTAMENTOS': 'Facultad'
        }
        df_f['Tipo de unidad'] = df_f['Tipo de unidad'].replace(mapeo_unidades)
        
        return df_n, df_f
    except Exception as e:
        st.error(f"❌ Error crítico cargando archivos: {e}")
        return None, None

def obtener_ids_evaluados():
    """Pregunta a Google Sheets qué IDs ya están listos"""
    try:
        response = requests.get(URL_WEBHOOK)
        if response.status_code == 200:
            # Esperamos recibir una lista de IDs ["001", "20038222", etc]
            return [str(x) for x in response.json()]
        return []
    except Exception as e:
        # Si falla la conexión, asumimos lista vacía para no romper la app
        print(f"Error conectando: {e}") 
        return []

# --- INICIO DE LA APLICACIÓN ---
df_nombrados, df_funciones = cargar_datos_maestros()
ids_ya_evaluados = obtener_ids_evaluados()

if df_nombrados is not None:
    st.title("📊 Dashboard de Evaluación de Nombramiento")

    # ==========================================
    # 1. BARRA LATERAL (FILTROS INTELIGENTES)
    # ==========================================
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    # Filtro Unidad
    lista_unidades = ["Todas"] + sorted(df_nombrados['Unidad'].unique().tolist())
    filtro_unidad = st.sidebar.selectbox("Filtrar por Unidad:", lista_unidades)
    
    # Filtro Tipo de Unidad
    lista_tipos = ["Todos"] + sorted(df_nombrados['Tipo de unidad'].unique().tolist())
    filtro_tipo = st.sidebar.selectbox("Filtrar por Tipo de Unidad:", lista_tipos)

    # Aplicamos filtros
    df_filtrado = df_nombrados.copy()
    if filtro_unidad != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Unidad'] == filtro_unidad]
    if filtro_tipo != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Tipo de unidad'] == filtro_tipo]

    # ==========================================
    # 2. LÓGICA DE ESTADO (PENDIENTE vs EVALUADO)
    # ==========================================
    # Marcamos quiénes ya están listos comparando su ID con la lista de la nube
    df_filtrado['Estado'] = df_filtrado['ID'].apply(lambda x: '✅ Listo' if str(x) in ids_ya_evaluados else '⏳ Pendiente')
    
    df_pendientes = df_filtrado[df_filtrado['Estado'] == '⏳ Pendiente']
    df_listos = df_filtrado[df_filtrado['Estado'] == '✅ Listo']

    # ==========================================
    # 3. INDICADORES SUPERIORES (KPIs)
    # ==========================================
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total en Selección", len(df_filtrado))
    col2.metric("📝 Pendientes", len(df_pendientes))
    col3.metric("✅ Evaluados", len(df_listos))
    
    # Barra de progreso
    if len(df_filtrado) > 0:
        progreso = len(df_listos) / len(df_filtrado)
        st.progress(progreso, text=f"Avance del grupo filtrado: {int(progreso*100)}%")
    
    st.divider()

    # ==========================================
    # 4. PESTAÑAS (LISTAS SEPARADAS)
    # ==========================================
    tab_pendientes, tab_historial = st.tabs(["⏳ Lista de Pendientes", "📂 Historial de Evaluados"])

    # --- PESTAÑA A: PENDIENTES ---
    with tab_pendientes:
        if df_pendientes.empty:
            st.success("🎉 ¡Excelente trabajo! No hay evaluaciones pendientes con estos filtros.")
        else:
            # Selector para evaluar
            lista_para_selector = df_pendientes['Nombre'] + " - (ID: " + df_pendientes['ID'] + ")"
            seleccion = st.selectbox("Seleccione colaborador a evaluar:", lista_para_selector)
            
            if seleccion:
                id_seleccionado = seleccion.split(" - (ID: ")[1][:-1]
                perfil = df_nombrados[df_nombrados['ID'] == id_seleccionado].iloc[0]

                st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px'>
                    <h4>👤 Evaluando a: {perfil['Nombre']}</h4>
                    <p><b>Categoría:</b> {perfil['Categoría']} | <b>Unidad:</b> {perfil['Unidad']} ({perfil['Tipo de unidad']})</p>
                </div>
                """, unsafe_allow_html=True)

                # Buscar sus funciones específicas
                funciones_persona = df_funciones[
                    (df_funciones['Categoría'] == perfil['Categoría']) & 
                    (df_funciones['Tipo de unidad'] == perfil['Tipo de unidad'])
                ]

                if funciones_persona.empty:
                    st.warning("⚠️ No se encontraron funciones configuradas para este perfil.")
                else:
                    # FORMULARIO
                    with st.form("form_evaluacion"):
                        datos_para_enviar = []
                        
                        for idx, fila in funciones_persona.iterrows():
                            criterio = fila['Criterios']
                            tipo_input = str(fila.get('Tipo_Input', 'texto')).strip().lower()
                            
                            st.write(f"🔹 **{criterio}**")
                            key_widget = f"preg_{perfil['ID']}_{idx}"

                            if tipo_input == 'si_no':
                                resp = st.radio("Cumple:", ["Sí", "No", "No Aplica"], horizontal=True, key=key_widget)
                            elif tipo_input == 'numero':
                                resp = st.number_input("Cantidad:", min_value=0, key=key_widget)
                            else:
                                resp = st.text_input("Respuesta:", key=key_widget)
                            
                            datos_para_enviar.append({
                                "id": str(perfil['ID']),
                                "nombre": str(perfil['Nombre']),
                                "unidad": str(perfil['Unidad']),
                                "pregunta": str(criterio),
                                "respuesta": str(resp)
                            })
                            st.markdown("---")
                        
                        observaciones = st.text_area("Observaciones Finales:")
                        boton_enviar = st.form_submit_button("💾 Guardar Evaluación")

                        if boton_enviar:
                            with st.spinner("Enviando a la nube..."):
                                errores = 0
                                for paquete in datos_para_enviar:
                                    paquete['observaciones'] = observaciones
                                    try:
                                        res = requests.post(URL_WEBHOOK, json=paquete)
                                        if res.status_code != 200:
                                            errores += 1
                                    except:
                                        errores += 1
                                
                                if errores == 0:
                                    st.success("✅ ¡Guardado exitosamente!")
                                    # Botón para recargar y actualizar listas
                                    if st.button("🔄 Actualizar lista de pendientes"):
                                        st.cache_data.clear()
                                        st.experimental_rerun()
                                else:
                                    st.error(f"⚠️ Hubo {errores} errores de conexión.")

    # --- PESTAÑA B: HISTORIAL ---
    with tab_historial:
        st.markdown("### Personas ya evaluadas")
        if df_listos.empty:
            st.info("Aún no se ha completado ninguna evaluación de este grupo.")
        else:
            # Tabla limpia solo con datos clave
            st.dataframe(
                df_listos[['ID', 'Nombre', 'Unidad', 'Categoría', 'Tipo de unidad']],
                use_container_width=True,
                hide_index=True
            )
            st.caption("ℹ️ Estos datos ya están seguros en tu Google Sheet.")
