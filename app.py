import streamlit as st
import pandas as pd
import plotly.express as px
from functions.data_loader import load_and_clean_data
from functions.product_analysis import top_selling_product_by_month, top_selling_products
from functions.client_analysis import products_bought_by_client, client_share_of_sales, client_returns_count
from functions.typology_analysis import add_typology_column, top_selling_typologies

st.set_page_config(page_title="Análisis de Ventas", layout="wide")
st.title("📊 Análisis de Datos de Ventas")

st.sidebar.header("1. Subir archivo Excel de ventas")
uploaded_file = st.sidebar.file_uploader("Selecciona el archivo Excel (.xlsx o .xls)", type=["xlsx", "xls"])

df = None
if uploaded_file:
    df = load_and_clean_data(uploaded_file)
    st.success("Archivo cargado correctamente. Filas: {}".format(len(df)))
    # Preprocesar tipología
    df = add_typology_column(df)
else:
    st.info("Por favor, sube un archivo Excel para comenzar.")

if df is not None:
    st.sidebar.header("2. Filtros")
    # Filtros dinámicos
    clientes = df['cliente'].dropna().unique().tolist()
    productos = df['descripcion_del_producto'].dropna().unique().tolist()
    tipologias = df['tipologia'].dropna().unique().tolist()

    cliente_sel = st.sidebar.selectbox("Filtrar por cliente", ["Todos"] + clientes)
    producto_sel = st.sidebar.selectbox("Filtrar por producto", ["Todos"] + productos)
    tipologia_sel = st.sidebar.selectbox("Filtrar por tipología", ["Todas"] + tipologias)

    # Aplicar filtros
    df_filt = df.copy()
    if cliente_sel != "Todos":
        df_filt = df_filt[df_filt['cliente'] == cliente_sel]
    if producto_sel != "Todos":
        df_filt = df_filt[df_filt['descripcion_del_producto'] == producto_sel]
    if tipologia_sel != "Todas":
        df_filt = df_filt[df_filt['tipologia'] == tipologia_sel]
    if not isinstance(df_filt, pd.DataFrame):
        df_filt = pd.DataFrame(df_filt)

    st.sidebar.header("3. Tipo de análisis")
    analysis_type = st.sidebar.selectbox(
        "Selecciona el análisis",
        [
            "Productos más comprados por cliente",
            "Tipologías más vendidas",
            "Top productos más vendidos",
            "Peso de cada cliente sobre el total de unidades",
            "Cantidad de devoluciones por cliente"
        ]
    )

    st.header("Resultados del análisis")
    if analysis_type == "Productos más comprados por cliente":
        cliente = st.selectbox("Selecciona el cliente", clientes)
        if cliente is None:
            cliente = clientes[0] if clientes else ""
        result = products_bought_by_client(df_filt, str(cliente))
        st.dataframe(result)
        if not result.empty:
            fig = px.bar(result, x='descripcion_del_producto', y='cantidad_vendida', title=f'Productos más comprados por {cliente}')
            st.plotly_chart(fig, use_container_width=True)
    elif analysis_type == "Tipologías más vendidas":
        result = top_selling_typologies(df_filt)
        st.dataframe(result)
        if not result.empty:
            fig = px.pie(result, names='tipologia', values='cantidad_vendida', title='Tipologías más vendidas')
            st.plotly_chart(fig, use_container_width=True)
    elif analysis_type == "Top productos más vendidos":
        n = st.slider("¿Cuántos productos mostrar?", 5, 20, 10)
        result = top_selling_products(df_filt, n)
        st.dataframe(result)
        if not result.empty:
            fig = px.bar(result, x='descripcion_del_producto', y='cantidad_vendida', title='Top productos más vendidos')
            st.plotly_chart(fig, use_container_width=True)
    elif analysis_type == "Peso de cada cliente sobre el total de unidades":
        result = client_share_of_sales(df_filt)
        total_unidades = df_filt.loc[df_filt['cantidad_vendida'] > 0, 'cantidad_vendida'].sum()
        col1, col2 = st.columns([2,1])
        with col1:
            st.dataframe(result)
        with col2:
            st.metric("Total de unidades vendidas", int(total_unidades))
        if not result.empty:
            fig = px.pie(result, names='cliente', values='porcentaje', title='Peso de cada cliente sobre el total de unidades')
            st.plotly_chart(fig, use_container_width=True)
    elif analysis_type == "Cantidad de devoluciones por cliente":
        result = client_returns_count(df_filt)
        total_devoluciones = df_filt.loc[df_filt['cantidad_vendida'] < 0].shape[0]
        col1, col2 = st.columns([2,1])
        with col1:
            st.dataframe(result)
        with col2:
            st.metric("Total de devoluciones", int(total_devoluciones))
        if not result.empty:
            fig = px.bar(result, x='cliente', y='cantidad_devoluciones', title='Cantidad de devoluciones por cliente')
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.caption("Puedes agregar nuevas funcionalidades fácilmente en el futuro, como exportar resultados o comparar clientes/tipologías.") 