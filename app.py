import streamlit as st
import pandas as pd
from io import BytesIO

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Evaluación Nombramiento", layout="wide")

st.title("🎓 Sistema de Evaluación para Nombramiento")
st.markdown("Seleccione un colaborador para cargar sus criterios específicos.")

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    # dtype=str asegura que leamos todo como texto para evitar errores de formato
    df_n = pd.read_csv('nombrados.csv', dtype=str) 
    df_f = pd.read_csv('funciones.csv', dtype=str)
    return df_n, df_f

try:
    df_nombrados, df_funciones = cargar_datos()

    # --- BARRA LATERAL (SELECTOR) ---
    st.sidebar.header("🔍 Buscar Colaborador")
    # Creamos un buscador amigable
    lista_busqueda = df_nombrados['Nombre'] + " - (ID: " + df_nombrados['ID'] + ")"
    seleccion = st.sidebar.selectbox("Escriba o seleccione:", lista_busqueda)

    # --- LÓGICA PRINCIPAL ---
    if seleccion:
        # 1. Recuperar datos del colaborador
        nombre_real = seleccion.split(" - (ID:")[0]
        perfil = df_nombrados[df_nombrados['Nombre'] == nombre_real].iloc[0]

        # 2. Mostrar Tarjeta de Datos
        st.info(f"📂 **Evaluando a:** {perfil['Nombre']}")
        
        col1, col2, col3 = st.columns(3)
        col1.write(f"**ID:** {perfil['ID']}")
        col1.write(f"**Categoría:** {perfil['Categoría']}")
        col2.write(f"**Unidad:** {perfil['Unidad']}")
        col2.write(f"**Sub Unidad:** {perfil['Sub Unidad']}")
        col3.write(f"**Tipo de Unidad:** {perfil['Tipo de unidad']}")
        
        st.divider()

        # 3. Filtrar Funciones (El Cruce Mágico)
        funciones_a_evaluar = df_funciones[
            (df_funciones['Categoria'] == perfil['Categoría']) & 
            (df_funciones['Tipo de unidad'] == perfil['Tipo de unidad'])
        ]

        st.subheader("📋 Criterios de Evaluación")

        if funciones_a_evaluar.empty:
            st.warning(f"⚠️ No hay funciones configuradas para: {perfil['Categoría']} - {perfil['Tipo de unidad']}")
        else:
            with st.form("form_evaluacion"):
                resultados_temp = [] 
                
                # --- AQUÍ ESTÁ EL CAMBIO IMPORTANTE ---
                # Iteramos sobre cada función encontrada
                for index, fila in funciones_a_evaluar.iterrows():
                    st.write(f"🔹 **{fila['Funcion_Descripcion']}**")
                    
                    # Leemos qué tipo de input pide el Excel
                    tipo = str(fila['Tipo_Input']).strip().lower() # Convertimos a minúscula por si acaso
                    
                    respuesta = "" # Variable para guardar lo que escriban

                    # DECISIÓN DINÁMICA DE WIDGET
                    if tipo == 'si_no':
                        respuesta = st.radio(
                            "Seleccione una opción:",
                            ["Sí", "No", "No Aplica"],
                            key=f"input_{index}",
                            horizontal=True
                        )
                    
                    elif tipo == 'texto':
                        respuesta = st.text_input(
                            "Ingrese el detalle requerido:",
                            key=f"input_{index}"
                        )
                    
                    elif tipo == 'numero':
                        respuesta = st.number_input(
                            "Ingrese la cantidad:",
                            min_value=0, 
                            step=1,
                            key=f"input_{index}"
                        )
                    
                    else:
                        # Si te olvidaste de poner el tipo en el Excel, pone texto por defecto
                        respuesta = st.text_input("Respuesta:", key=f"input_{index}")

                    # Guardamos el resultado en la lista temporal
                    resultados_temp.append({
                        "ID": perfil['ID'],
                        "Nombre": perfil['Nombre'],
                        "Criterio": fila['Funcion_Descripcion'],
                        "Respuesta": respuesta
                    })
                    st.markdown("---") 
                
                # Campo final de observaciones
                observaciones = st.text_area("Observaciones Finales:")
                boton_enviar = st.form_submit_button("✅ Finalizar Evaluación")

            # 4. Generar Excel
            if boton_enviar:
                df_resultados = pd.DataFrame(resultados_temp)
                df_resultados['Observaciones_Generales'] = observaciones
                
                # Generar descarga
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_resultados.to_excel(writer, index=False)
                    
                st.success("¡Datos capturados! Descarga el archivo abajo:")
                st.download_button(
                    label="📥 Descargar Excel de Resultados",
                    data=buffer,
                    file_name=f"Evaluacion_{perfil['ID']}.xlsx",
                    mime="application/vnd.ms-excel"
                )

except Exception as e:
    st.error(f"❌ Ocurrió un error: {e}. Revisa que tus archivos CSV tengan las columnas correctas.")
