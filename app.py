import io
import streamlit as st
import pandas as pd
import plotly.express as px

from functions.data_loader import load_and_clean_data
from functions.product_analysis import top_selling_product_by_month, top_selling_products
from functions.client_analysis import products_bought_by_client, client_share_of_sales, client_returns_count
from functions.typology_analysis import add_typology_column, top_selling_typologies, get_special_categories_summary, get_sales_by_gender
from functions.columns_normalizer import normalize_columns

# Storage
from services.storage_supabase import upload_to_path, download_excel, signed_url

# Uploads/metadata
from functions.uploads_service import (
    parse_filename, compute_sha256, build_storage_path,
    check_duplicate, insert_upload_metadata, update_upload_metadata,
    list_uploads
)

# Detección de formato (v2 si está, sinó fallback)
try:
    from utils.format_detect import detect_format_v2
except ImportError:
    from utils.format_detect import detect_format as detect_format_v2

# Limpieza de dominio (fallback no-op si no existe)
try:
    from functions.domain_cleaning import apply_domain_cleaning
except Exception:
    def apply_domain_cleaning(df):
        return df

st.set_page_config(page_title="Análisis de Ventas", layout="wide")
st.title("📊 Análisis de Datos de Ventas")

# =============================
# BLOQUE NUEVO: gestor de archivos persistentes
# =============================
st.header("0. Archivos persistidos (por convención de nombre)")

tab_up, tab_list = st.tabs(["Subir nuevo", "Abrir guardado"])

df = None
context = None

with tab_up:
    up = st.file_uploader("Subí tu Excel (.xlsx o .xls) con nombre válido", type=["xlsx","xls"])
    replace = st.checkbox("Reemplazar si ya existe (conserva histórico)", value=False)

    if up is not None:
        try:
            # 1) Validar NOMBRE por convención
            ctx = parse_filename(up.name)
            st.success(
                f"Contexto detectado → tipo={ctx['file_type']} · scope={ctx['scope']} · "
                f"local={ctx['local_code'] or '—'} · período={ctx['period_str']}"
            )

            # 2) Cargar/Limpiar y DETECTAR FORMATO por columnas
            tmp_df = load_and_clean_data(up)
            tmp_df = normalize_columns(tmp_df)         # 👈 normaliza cabeceras
            tmp_df = apply_domain_cleaning(tmp_df)
            fmt = detect_format_v2(tmp_df)  # dict o str (fallback)

            # Normalizar a dict si vino como string (fallback)
            if isinstance(fmt, str):
                fmt = {"family": fmt, "version": "v1"}

            if fmt["family"] == "desconocido":
                st.error(
                    "Formato de columnas no reconocido.\n"
                    "• Para 'temporada' se esperan: cliente, codigo_del_articulo, descripcion_del_producto, cantidad_vendida\n"
                    "• Para 'locales' se esperan: codigo_del_articulo, descripcion_del_producto, cantidad_vendida"
                )
                st.stop()

            # 3) Duplicados por contexto
            sha = compute_sha256(up.getvalue())
            prev = check_duplicate(ctx["file_type"], ctx["period_month"], ctx["local_code"])
            if prev and not replace:
                st.error("Ya existe un upload para ese contexto. Activá 'Reemplazar' si querés subir uno nuevo.")
                st.stop()

            # 4) Subir a STORAGE en ruta ordenada (con overwrite según checkbox)
            storage_key = build_storage_path(ctx["scope"], ctx["local_code"], ctx["period_month"], up.name)
            upload_to_path(up.getvalue(), storage_key, overwrite=replace)

            format_name = f"{fmt['family']}_v{fmt.get('version','v1')[-1]}"

            if prev and replace:
                # 🔁 REEMPLAZO: actualizamos el row existente en 'uploads'
                row = update_upload_metadata(
                    prev["id"],
                    original_name=up.name,
                    storage_key=storage_key,  # mismo key
                    sha256=sha,
                    format_name=format_name,
                    status="processed",
                    source="upload"
                    # tip: si querés guardar "última fecha de reemplazo", agregamos luego una columna 'replaced_at'
                )
            else:
                # ➕ INSERCIÓN normal
                row = insert_upload_metadata(
                    file_type=ctx["file_type"], scope=ctx["scope"], local_code=ctx["local_code"],
                    period_month=ctx["period_month"], format_name=format_name,
                    original_name=up.name, storage_key=storage_key, sha256=sha,
                    status="processed", source="upload", supersedes_upload_id=None
                )

            st.success("✅ Archivo subido y registrado en uploads.")
            st.caption(f"Storage key: `{storage_key}`")

            # Dejo el df listo por si querés continuar con tu análisis abajo
            df, context = tmp_df, ctx

        except ValueError as e:
            # Errores de nombre inválido (parser)
            st.error(str(e))

with tab_list:
    st.subheader("Abrir un archivo guardado")
    # Filtros
    scope_opt = st.selectbox("Scope", options=["(todos)", "global", "local"], index=0)
    file_type_opt = st.selectbox("Tipo", options=["(todos)", "temporada", "locales"], index=0)

    local_code_opt = None
    if scope_opt == "local":
        local_code_opt = st.selectbox("Local", options=["centenario","5","49","55"])

    # filtros de período (por default mes/año actuales)
    col_a, col_m = st.columns(2)
    with col_a:
        year_opt = st.number_input("Año", min_value=2020, max_value=2100, value=pd.Timestamp.today().year, step=1)
    with col_m:
        month_opt = st.number_input("Mes", min_value=1, max_value=12, value=pd.Timestamp.today().month, step=1)

    # Normalizar valores para el servicio
    filt_scope = None if scope_opt == "(todos)" else scope_opt
    filt_ftype = None if file_type_opt == "(todos)" else file_type_opt

    # Traer datos desde uploads
    rows = list_uploads(scope=filt_scope, local_code=local_code_opt, year=int(year_opt), month=int(month_opt), file_type=filt_ftype)

    if not rows:
        st.info("No hay archivos que coincidan con los filtros.")
    else:
        # Etiqueta compacta
        def fmt_row(r):
            loc = f" · {r['local_code']}" if r["local_code"] else ""
            return f"{r['file_type']} · {r['scope']}{loc} · {r['period_month']} · {r['uploaded_at']}"

        selected = st.selectbox("Elegí un archivo", options=rows, format_func=fmt_row)

        # Abrir
        if selected and st.button("Abrir archivo seleccionado", type="primary"):
            content = download_excel(selected["storage_key"])
            df = pd.read_excel(io.BytesIO(content))
            df = normalize_columns(df)
            # limpieza de dominio mínima (si la tenés)
            try:
                df = apply_domain_cleaning(df)
            except Exception:
                pass

            # contexto mínimo para el pipeline posterior
            context = {
                "file_type": selected["file_type"],
                "scope": selected["scope"],
                "local_code": selected["local_code"],
                "period_month": selected["period_month"],
            }
            st.success(f"Abriste: {fmt_row(selected)}")



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