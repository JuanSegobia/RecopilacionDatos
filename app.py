import streamlit as st
import pandas as pd
import plotly.express as px
from functions.data_loader import load_and_clean_data
from functions.product_analysis import top_selling_product_by_month, top_selling_products
from functions.client_analysis import products_bought_by_client, client_share_of_sales, client_returns_count
from functions.typology_analysis import add_typology_column, top_selling_typologies, get_special_categories_summary, get_sales_by_gender

# 👇 nuevos imports
import io
from services.storage_supabase import upload_excel, insert_meta, list_files, download_excel, signed_url
from utils.format_detect import detect_format

st.set_page_config(page_title="Análisis de Ventas", layout="wide")
st.title("📊 Análisis de Datos de Ventas")

# =============================
# BLOQUE NUEVO: gestor de archivos persistentes
# =============================
st.header("0. Gestor de archivos de análisis")

tab1, tab2 = st.tabs(["Subir nuevo", "Abrir guardado"])

df = None

with tab1:
    up = st.file_uploader("Subí tu Excel (temporada o locales)", type=["xlsx","xls"])
    if up is not None:
        df = load_and_clean_data(up)
        file_type = detect_format(df)
        if file_type == "desconocido":
            st.error("No reconozco el formato (temporada/locales). Revisá columnas.")
        else:
            storage_key = upload_excel(up.getvalue(), up.name)
            insert_meta(file_type, up.name, storage_key)
            st.success(f"Guardado como '{file_type}'.")
            st.write("Enlace temporal:", signed_url(storage_key))

with tab2:
    rows = list_files()
    if not rows:
        st.info("No hay archivos guardados aún.")
    else:
        label = lambda r: f"{r['file_type']} · {r['original_name']} · {r['uploaded_at']}"
        selected = st.selectbox("Elegí un archivo", options=rows, format_func=label)
        if selected:
            content = download_excel(selected["storage_key"])
            # Crear un objeto similar a UploadedFile para reutilizar load_and_clean_data
            bytes_data = io.BytesIO(content)
            bytes_data.name = selected["original_name"]  # Añadir nombre para detección de extensión
            
            # Aplicar la misma limpieza que en archivos nuevos
            df = load_and_clean_data(bytes_data)
            
            st.success(f"Archivo abierto: {selected['original_name']}")
            st.write("Vista previa:", df.head())

# Paso 1: Preprocesar solo si hay df
if df is not None:
    st.success("✅ Archivo listo para análisis. Filas: {}".format(len(df)))
    
    # Mostrar columnas encontradas para debug
    with st.expander("🔍 Columnas detectadas en el archivo"):
        st.write("**Columnas encontradas:**", list(df.columns))
        
        # Verificar columnas críticas
        required_columns = ['codigo_del_articulo', 'cantidad_vendida', 'cliente']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ **Columnas críticas faltantes:** {missing_columns}")
            st.write("**Sugerencia:** Verifica que tu archivo Excel tenga columnas como:")
            st.write("- Código de artículo/producto (ej: 'Artículo', 'Código', 'Item')")
            st.write("- Cantidad vendida (ej: 'Unidades', 'Cantidad', 'Cant')")
            st.write("- Cliente (ej: 'Cliente', 'Cod_Cliente')")
            st.info("💡 **Tip:** Si es un archivo guardado, el problema puede estar en el formato original del Excel.")
            st.stop()  # Detener ejecución si faltan columnas críticas
        else:
            st.success("✅ Todas las columnas críticas están presentes")

    # Preprocesar tipología solo si las columnas están disponibles
    try:
        df = add_typology_column(df)
        st.success("✅ Tipologías procesadas correctamente")
    except Exception as e:
        st.error(f"❌ Error al procesar tipologías: {str(e)}")
        st.stop()

    # Paso 2: Seleccionar tipo de análisis
    st.header("1. Seleccionar tipo de análisis")
    analysis_type = st.selectbox(
        "¿Qué análisis deseas realizar?",
        [
            "Productos más comprados por cliente",
            "Tipologías más vendidas",
            "Top productos más vendidos",
            "Peso de cada cliente sobre el total de unidades",
            "Cantidad de devoluciones por cliente",
            "Análisis por género",
            "Categorías especiales (Cierres, CH, Sorteos, etc.)"
        ],
        key="analysis_type"
    )

    if analysis_type != "Selecciona una opción":
        # Paso 3: Filtros (solo se muestran según el tipo de análisis)
        # Determinar qué filtros mostrar según el análisis seleccionado
        show_cliente_filter = analysis_type in ["Productos más comprados por cliente", "Peso de cada cliente sobre el total de unidades"]
        show_producto_filter = analysis_type in ["Productos más comprados por cliente", "Peso de cada cliente sobre el total de unidades"]
        show_tipologia_filter = analysis_type in ["Productos más comprados por cliente", "Peso de cada cliente sobre el total de unidades", "Cantidad de devoluciones por cliente", "Análisis por género"]
        
        # Solo mostrar el header de filtros si hay al menos un filtro que mostrar
        if show_cliente_filter or show_producto_filter or show_tipologia_filter:
            st.header("3. Filtros")
            
            # Filtros dinámicos
            clientes = df['cliente'].dropna().unique().tolist()
            productos = df['descripcion_del_producto'].dropna().unique().tolist()
            tipologias = df['tipologia'].dropna().unique().tolist()

            # Crear columnas dinámicamente según los filtros que se muestren
            filters_to_show = []
            if show_cliente_filter:
                filters_to_show.append("cliente")
            if show_producto_filter:
                filters_to_show.append("producto")
            if show_tipologia_filter:
                filters_to_show.append("tipologia")
            
            if len(filters_to_show) == 1:
                col1 = st.columns(1)[0]
                cols = [col1]
            elif len(filters_to_show) == 2:
                col1, col2 = st.columns(2)
                cols = [col1, col2]
            else:
                col1, col2, col3 = st.columns(3)
                cols = [col1, col2, col3]
            
            # Asignar filtros a columnas
            filter_idx = 0
            cliente_input = ""
            producto_input = ""
            tipologia_sel = "Todas"
            
            if show_cliente_filter:
                with cols[filter_idx]:
                    cliente_input = st.text_input("Filtrar por cliente (código o nombre)", placeholder="Ej: 12345 o Juan Pérez")
                filter_idx += 1
            
            if show_producto_filter:
                with cols[filter_idx]:
                    producto_input = st.text_input("Filtrar por producto (código o nombre)", placeholder="Ej: ABC123 o Remera")
                filter_idx += 1
            
            if show_tipologia_filter:
                with cols[filter_idx]:
                    tipologia_sel = st.selectbox("Filtrar por tipología", ["Todas"] + tipologias)
        else:
            # Si no se muestran filtros, inicializar variables vacías
            cliente_input = ""
            producto_input = ""
            tipologia_sel = "Todas"

        # Aplicar filtros
        df_filt = df.copy()
        
        # Filtro por cliente (busca tanto en código como en nombre)
        if cliente_input.strip():
            cliente_mask = (
                df_filt['cliente'].astype(str).str.contains(cliente_input, case=False, na=False) |
                df_filt['nombre_cliente'].astype(str).str.contains(cliente_input, case=False, na=False)
            )
            df_filt = df_filt[cliente_mask]
        
        # Filtro por producto (busca tanto en código como en descripción)
        if producto_input.strip():
            producto_mask = (
                df_filt['codigo_del_articulo'].astype(str).str.contains(producto_input, case=False, na=False) |
                df_filt['descripcion_del_producto'].astype(str).str.contains(producto_input, case=False, na=False)
            )
            df_filt = df_filt[producto_mask]
        
        # Filtro por tipología
        if tipologia_sel != "Todas":
            df_filt = df_filt[df_filt['tipologia'] == tipologia_sel]
        
        if not isinstance(df_filt, pd.DataFrame):
            df_filt = pd.DataFrame(df_filt)

        # Paso 4: Mostrar resultados del análisis
        st.header("4. Resultados del análisis")
        
        if analysis_type == "Productos más comprados por cliente":
            cliente_analisis = st.text_input("Ingresa el cliente a analizar (código o nombre)", placeholder="Ej: 12345 o Juan Pérez")
            
            if cliente_analisis.strip():
                # Buscar cliente por código o nombre
                cliente_mask = (
                    df_filt['cliente'].astype(str).str.contains(cliente_analisis, case=False, na=False) |
                    df_filt['nombre_cliente'].astype(str).str.contains(cliente_analisis, case=False, na=False)
                )
                df_cliente = df_filt[cliente_mask]
                
                if not df_cliente.empty:
                    result = df_cliente.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
                    result = result.sort_values('cantidad_vendida', ascending=False).head(10)
                    
                    st.dataframe(result)
                    if not result.empty:
                        fig = px.bar(result, x='descripcion_del_producto', y='cantidad_vendida', 
                                title=f'Productos más comprados por cliente que contiene "{cliente_analisis}"')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No se encontraron clientes que coincidan con la búsqueda.")
            else:
                st.info("👆 Ingresa un cliente para ver sus productos más comprados.")
        
        elif analysis_type == "Tipologías más vendidas":
            # No se muestran filtros para este análisis
            
            # Tabla 1: Todos los artículos
            st.subheader("📊 Todos los artículos")
            result_todos = top_selling_typologies(df[df['cuenta_ventas'] == True])
            st.dataframe(result_todos)
            if not result_todos.empty:
                fig1 = px.pie(result_todos, names='tipologia', values='cantidad_vendida', 
                             title='Tipologías más vendidas - Todos los artículos')
                st.plotly_chart(fig1, use_container_width=True)
            
            st.divider()
            
            # Tabla 2: Solo básicos
            st.subheader("🔹 Solo básicos")
            df_basicos = df[(df['cuenta_ventas'] == True) & (df['codigo_del_articulo'].str.startswith("B"))]

            if not df_basicos.empty:
                result_basicos = df_basicos.groupby(['codigo_del_articulo', 'descripcion_del_producto'])['cantidad_vendida'].sum().reset_index()
                result_basicos = result_basicos.sort_values('cantidad_vendida', ascending=False).head(10)
                result_basicos = result_basicos.rename(columns={
                    'codigo_del_articulo': 'Código', 
                    'descripcion_del_producto': 'Descripción', 
                    'cantidad_vendida': 'Cantidad vendida'
                })
                st.dataframe(result_basicos)
                
                fig2 = px.bar(result_basicos, x='Descripción', y='Cantidad vendida', 
                            title='Top 10 productos básicos más vendidos')
                fig2.update_xaxes(tickangle=45)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No se encontraron productos básicos en los datos.")
        
        elif analysis_type == "Top productos más vendidos":
            # No se muestran filtros para este análisis
            n = st.slider("¿Cuántos productos mostrar?", 5, 20, 10)
            result = top_selling_products(df[df['cuenta_ventas'] == True], n)
            
            # Agregar ranking
            if not result.empty:
                result = result.reset_index(drop=True)
                result.insert(0, 'Ranking', range(1, len(result) + 1))
            
            st.dataframe(result)
            if not result.empty:
                fig = px.bar(result, x='descripcion_del_producto', y='cantidad_vendida', 
                           title='Top productos más vendidos')
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
        
        elif analysis_type == "Peso de cada cliente sobre el total de unidades":
            result = client_share_of_sales(df_filt)
            # Calcular total solo de ventas normales (excluir categorías especiales)
            total_unidades = df_filt[df_filt['cuenta_ventas'] == True]['cantidad_vendida'].sum()
            
            # Si hay filtro por cliente o producto, mostrar información específica
            if cliente_input.strip() or producto_input.strip():
                col1, col2 = st.columns([2,1])
                
                with col1:
                    if cliente_input.strip():
                        st.subheader(f"📊 Análisis para cliente: '{cliente_input}'")
                        # Calcular peso del cliente filtrado vs total general (solo ventas normales)
                        cliente_unidades = df_filt[df_filt['cuenta_ventas'] == True]['cantidad_vendida'].sum()
                        total_general = df[df['cuenta_ventas'] == True]['cantidad_vendida'].sum()
                        porcentaje_cliente = (cliente_unidades / total_general) * 100 if total_general > 0 else 0
                        
                        st.metric("Unidades del cliente (ventas normales)", int(cliente_unidades))
                        st.metric("% del total general", f"{porcentaje_cliente:.1f}%")
                        
                        # Mostrar breakdown por cliente específico
                        st.dataframe(result)
                        
                    if producto_input.strip():
                        st.subheader(f"📦 Análisis para producto: '{producto_input}'")
                        # Calcular peso del producto filtrado vs total de ese producto específico (solo ventas normales)
                        producto_unidades = df_filt[df_filt['cuenta_ventas'] == True]['cantidad_vendida'].sum()
                        
                        # Buscar el total vendido de ese producto específico en toda la base (solo ventas normales)
                        producto_mask_total = (
                            df['codigo_del_articulo'].astype(str).str.contains(producto_input, case=False, na=False) |
                            df['descripcion_del_producto'].astype(str).str.contains(producto_input, case=False, na=False)
                        )
                        df_producto_total = df[producto_mask_total & (df['cuenta_ventas'] == True)]
                        total_producto_especifico = df_producto_total['cantidad_vendida'].sum()
                        porcentaje_producto = (producto_unidades / total_producto_especifico) * 100 if total_producto_especifico > 0 else 0
                        
                        st.metric("Unidades del cliente para este producto", int(producto_unidades))
                        st.metric("% del total de este producto", f"{porcentaje_producto:.1f}%")
                        st.metric("Total vendido de este producto (ventas normales)", int(total_producto_especifico))
                        
                        # Mostrar quién compra más este producto
                        agg_dict = {'cantidad_vendida': 'sum'}
                        if 'nombre_cliente' in df_filt.columns:
                            agg_dict['nombre_cliente'] = 'first'
                        if 'localidad' in df_filt.columns:
                            agg_dict['localidad'] = 'first'
                        
                        cliente_producto = df_filt.groupby('cliente').agg(agg_dict).reset_index()
                        cliente_producto = cliente_producto.sort_values('cantidad_vendida', ascending=False)
                        
                        # Agregar ranking
                        cliente_producto.insert(0, 'Ranking', range(1, len(cliente_producto) + 1))
                        
                        st.subheader("Top clientes que compran este producto:")
                        st.dataframe(cliente_producto.head(10))
                        
                with col2:
                    st.metric("Total filtrado", int(total_unidades))
                    st.metric("Total general", int(df[df['cuenta_ventas'] == True]['cantidad_vendida'].sum()))
                    
                    # Gráfico de comparación
                    if cliente_input.strip():
                        fig_data = pd.DataFrame({
                            'Categoría': ['Cliente seleccionado', 'Resto'],
                            'Unidades': [cliente_unidades, total_general - cliente_unidades]
                        })
                        fig = px.pie(fig_data, names='Categoría', values='Unidades', 
                                title=f'Peso del cliente "{cliente_input}" vs Total')
                        st.plotly_chart(fig, use_container_width=True)
                    elif producto_input.strip():
                        # Calcular el total del producto específico para el gráfico
                        producto_mask_total = (
                            df['codigo_del_articulo'].astype(str).str.contains(producto_input, case=False, na=False) |
                            df['descripcion_del_producto'].astype(str).str.contains(producto_input, case=False, na=False)
                        )
                        total_producto_especifico = df[producto_mask_total & (df['cuenta_ventas'] == True)]['cantidad_vendida'].sum()
                        
                        fig_data = pd.DataFrame({
                            'Categoría': ['Cliente seleccionado', 'Otros clientes'],
                            'Unidades': [producto_unidades, total_producto_especifico - producto_unidades]
                        })
                        fig = px.pie(fig_data, names='Categoría', values='Unidades', 
                                title=f'Participación del cliente en producto "{producto_input}"')
                        st.plotly_chart(fig, use_container_width=True)
            else:
                # Vista general sin filtros
                col1, col2 = st.columns([2,1])
                with col1:
                    st.dataframe(result)
                with col2:
                    st.metric("Total neto de unidades", int(total_unidades))
                
                if not result.empty:
                    fig = px.pie(result, names='cliente', values='cantidad_vendida', 
                            title='Peso de cada cliente sobre el total de unidades')
                    st.plotly_chart(fig, use_container_width=True)

        elif analysis_type == "Cantidad de devoluciones por cliente":
            result = client_returns_count(df_filt)
            total_devoluciones = df_filt.loc[df_filt['cantidad_vendida'] < 0, 'cantidad_vendida'].abs().sum()
            col1, col2 = st.columns([2,1])
            with col1:
                st.dataframe(result)
            with col2:
                st.metric("Total de devoluciones (unidades)", int(total_devoluciones))
        
        elif analysis_type == "Análisis por género":
            result = get_sales_by_gender(df_filt)
            st.dataframe(result)
            if not result.empty:
                fig = px.pie(result, names='genero', values='cantidad_vendida', title='Ventas por género')
                st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar total de unidades que cuentan como ventas
            ventas_normales = df_filt[df_filt['cuenta_ventas'] == True]['cantidad_vendida'].sum()
            st.metric("Total unidades vendidas (excluye categorías especiales)", int(ventas_normales))
        
        elif analysis_type == "Categorías especiales (Cierres, CH, Sorteos, etc.)":
            summary = get_special_categories_summary(df)  # Usar df original, no filtrado
            
            # Crear tabs para cada categoría
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Cierres", "Cheques", "Sorteos", "Perfuminas", "Otros Códigos"])
            
            with tab1:
                st.subheader("🔒 Cierres")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cantidad de registros", summary['cierres']['cantidad'])
                with col2:
                    st.metric("Total unidades", int(summary['cierres']['unidades']))
                
                if not summary['cierres']['detalle'].empty:
                    st.dataframe(summary['cierres']['detalle'])
                else:
                    st.info("No se encontraron registros de cierres en los datos.")
            
            with tab2:
                st.subheader("🏷️ Cheques")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cantidad de registros", summary['ch']['cantidad'])
                with col2:
                    st.metric("Total unidades", int(summary['ch']['unidades']))
                
                if not summary['ch']['detalle'].empty:
                    st.dataframe(summary['ch']['detalle'])
                else:
                    st.info("No se encontraron registros de cheques en los datos.")
            
            with tab3:
                st.subheader("🎲 Sorteos")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cantidad de registros", summary['sorteos']['cantidad'])
                with col2:
                    st.metric("Total unidades", int(summary['sorteos']['unidades']))
                
                if not summary['sorteos']['detalle'].empty:
                    st.dataframe(summary['sorteos']['detalle'])
                else:
                    st.info("No se encontraron registros de sorteos en los datos.")
            
            with tab4:
                st.subheader("🌸 Perfuminas")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cantidad de registros", summary['perfuminas']['cantidad'])
                with col2:
                    st.metric("Total unidades", int(summary['perfuminas']['unidades']))
                
                if not summary['perfuminas']['detalle'].empty:
                    st.dataframe(summary['perfuminas']['detalle'])
                else:
                    st.info("No se encontraron registros de perfuminas en los datos.")
            
            with tab5:
                st.subheader("❓ Otros Códigos")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cantidad de registros", summary['otros_codigos']['cantidad'])
                with col2:
                    st.metric("Total unidades", int(summary['otros_codigos']['unidades']))
                
                if not summary['otros_codigos']['detalle'].empty:
                    st.dataframe(summary['otros_codigos']['detalle'])
                else:
                    st.info("No se encontraron otros códigos especiales en los datos.")
                    
            # Resumen general
            # st.subheader("📊 Resumen general")
            #total_especiales = (summary['cierres']['unidades'] + summary['ch']['unidades'] + 
            #                  summary['sorteos']['unidades'] + summary['perfuminas']['unidades'] + 
            #                  summary['otros_codigos']['unidades'])
            #ventas_normales = df_filt[df_filt['cuenta_ventas'] == True]['cantidad_vendida'].sum()
            #
            #col1, col2, col3 = st.columns(3)
            #with col1:
            #    st.metric("Ventas normales", int(ventas_normales))
            #with col2:
            #    st.metric("Categorías especiales", int(total_especiales))
            #with col3:
            #    st.metric("Total general", int(ventas_normales + total_especiales)) 

else:
    st.info("👆 Por favor, sube un archivo Excel para comenzar el análisis.")

st.markdown("---")
st.caption("💡 Puedes agregar nuevas funcionalidades fácilmente en el futuro, como exportar resultados o comparar clientes/tipologías.") 