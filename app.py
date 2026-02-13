# 1. IMPORTAR HERRAMIENTAS
import streamlit as st  # Traemos al "Mesero" (hace la web)
import pandas as pd     # Traemos al "Excel Virtual" (lee datos)

# 2. CARGAR DATOS
# Aquí le decimos al programa: "Lee los archivos CSV que subimos"
df_personas = pd.read_csv('postulantes.csv')
df_funciones = pd.read_csv('funciones.csv')

# 3. INTERFAZ (LO VISUAL)
st.title("Evaluación de Personal") # Pone el título grande

# Creamos una cajita desplegable (selectbox) con los nombres de la columna 'Nombre'
nombre_seleccionado = st.selectbox("Elige al colaborador:", df_personas['Nombre'])

# 4. CEREBRO (EL FILTRO)
# Buscamos en la tabla de personas toda la info del nombre seleccionado
datos_persona = df_personas[df_personas['Nombre'] == nombre_seleccionado].iloc[0]

# Mostramos en pantalla su categoría y unidad para confirmar
st.write(f"Evaluando a un: {datos_persona['Categoria']} de {datos_persona['Unidad']}")

# EL PASO CRUCIAL:
# Le decimos al Excel de funciones: 
# "Filtra y dame solo las filas donde la Categoria coincida con la de esta persona
# Y TAMBIÉN donde la Unidad coincida con la de esta persona".
funciones_a_evaluar = df_funciones[
    (df_funciones['Categoria'] == datos_persona['Categoria']) & 
    (df_funciones['Unidad'] == datos_persona['Unidad'])
]

# 5. GENERAR EL FORMULARIO
# Si la lista no está vacía, hacemos un bucle (loop)
if not funciones_a_evaluar.empty:
    with st.form("mi_formulario"):
        # Para cada función encontrada, dibuja una pregunta
        for index, fila in funciones_a_evaluar.iterrows():
            st.write(f"Función: {fila['Funcion']}")
            st.radio("¿Cumple?", ["Sí", "No"], key=index) # Botones de opción
        
        # Botón para enviar
        boton_guardar = st.form_submit_button("Guardar Evaluación")
        
        if boton_guardar:
            st.success("¡Evaluación completada!")
else:
    st.error("No hay funciones configuradas para este perfil.")
