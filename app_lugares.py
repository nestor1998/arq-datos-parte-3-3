import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Lugares Históricos", layout="wide")

st.title("Mapa Mundial de Lugares Históricos")

st.info("Sube el archivo TXT con lugares históricos para visualizarlos en un mapa mundial.")


def normalizar_texto(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).strip()
    texto = " ".join(texto.split())

    return texto


def normalizar_titulo(texto):
    texto = normalizar_texto(texto)
    return texto.title()


def leer_archivo_lugares(archivo):
    try:
        df = pd.read_csv(archivo, sep=";", encoding="utf-8")
    except:
        archivo.seek(0)
        df = pd.read_csv(archivo, sep=";", encoding="latin1")

    df.columns = df.columns.str.strip()

    columnas_nuevas = {}

    for col in df.columns:
        col_limpia = col.strip().lower()

        if "nombre" in col_limpia:
            columnas_nuevas[col] = "Nombre"
        elif "direcci" in col_limpia or "direcciÛn" in col_limpia:
            columnas_nuevas[col] = "Direccion"
        elif "geo" in col_limpia:
            columnas_nuevas[col] = "Georeferencia"

    df = df.rename(columns=columnas_nuevas)

    columnas_requeridas = ["Nombre", "Direccion", "Georeferencia"]

    for columna in columnas_requeridas:
        if columna not in df.columns:
            st.error(f"Falta la columna requerida: {columna}")
            return pd.DataFrame()

    df["Nombre"] = df["Nombre"].apply(normalizar_titulo)
    df["Direccion"] = df["Direccion"].apply(normalizar_texto)
    df["Georeferencia"] = df["Georeferencia"].apply(normalizar_texto)

    coordenadas = df["Georeferencia"].str.split(",", expand=True)

    if coordenadas.shape[1] < 2:
        st.error("La columna Georeferencia no tiene formato válido: latitud, longitud")
        return pd.DataFrame()

    df["Latitud"] = pd.to_numeric(coordenadas[0].str.strip(), errors="coerce")
    df["Longitud"] = pd.to_numeric(coordenadas[1].str.strip(), errors="coerce")

    antes_invalidos = len(df)

    df = df.dropna(subset=["Latitud", "Longitud"])

    df = df[
        (df["Latitud"] >= -90) &
        (df["Latitud"] <= 90) &
        (df["Longitud"] >= -180) &
        (df["Longitud"] <= 180)
    ]

    invalidos = antes_invalidos - len(df)

    antes_duplicados = len(df)

    df = df.drop_duplicates(subset=["Nombre", "Latitud", "Longitud"])

    duplicados = antes_duplicados - len(df)

    df = df.sort_values("Nombre").reset_index(drop=True)

    return df, invalidos, duplicados


def crear_mapa(df, lugar_seleccionado=None):
    if lugar_seleccionado:
        fila = df[df["Nombre"] == lugar_seleccionado].iloc[0]
        centro = [fila["Latitud"], fila["Longitud"]]
        zoom = 13
    else:
        centro = [20, 0]
        zoom = 2

    mapa = folium.Map(location=centro, zoom_start=zoom)

    for _, row in df.iterrows():
        popup = f"""
        <b>{row['Nombre']}</b><br>
        {row['Direccion']}<br>
        Latitud: {row['Latitud']}<br>
        Longitud: {row['Longitud']}
        """

        folium.Marker(
            location=[row["Latitud"], row["Longitud"]],
            popup=popup,
            tooltip=row["Nombre"]
        ).add_to(mapa)

    return mapa


archivo = st.file_uploader(
    "Cargar archivo TXT de lugares históricos",
    type=["txt", "csv"]
)

if archivo is not None:
    df_lugares, invalidos, duplicados = leer_archivo_lugares(archivo)

    if df_lugares.empty:
        st.warning("No se pudieron procesar lugares válidos.")
        st.stop()

    st.success("Archivo cargado, limpiado y procesado correctamente.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Lugares válidos", len(df_lugares))
    col2.metric("Registros inválidos eliminados", invalidos)
    col3.metric("Duplicados eliminados", duplicados)

    st.subheader("Seleccionar lugar")

    lugar_seleccionado = st.selectbox(
        "Elige un lugar para llegar directamente en el mapa:",
        ["Mostrar todos"] + df_lugares["Nombre"].tolist()
    )

    if lugar_seleccionado == "Mostrar todos":
        lugar_mapa = None
    else:
        lugar_mapa = lugar_seleccionado

        fila = df_lugares[df_lugares["Nombre"] == lugar_seleccionado].iloc[0]

        st.write(f"Nombre: {fila['Nombre']}")
        st.write(f"Dirección: {fila['Direccion']}")
        st.write(f"Latitud: {fila['Latitud']}")
        st.write(f"Longitud: {fila['Longitud']}")

    st.subheader("Mapa mundial de lugares cargados")

    mapa = crear_mapa(df_lugares, lugar_mapa)

    st_folium(
        mapa,
        width=1200,
        height=600
    )

    st.subheader("Tabla de lugares cargados")

    buscar = st.text_input("Buscar lugar:")

    df_mostrar = df_lugares.copy()

    if buscar:
        df_mostrar = df_mostrar[
            df_mostrar["Nombre"].str.contains(buscar, case=False, na=False)
        ]

    df_mostrar.index = range(1, len(df_mostrar) + 1)

    st.dataframe(df_mostrar, use_container_width=True)

    txt_salida = df_lugares.to_string(index=False)

    st.download_button(
        label="Descargar TXT procesado",
        data=txt_salida,
        file_name="lugares_historicos_procesados.txt",
        mime="text/plain"
    )

    csv_salida = df_lugares.to_csv(index=False, encoding="utf-8-sig")


else:
    st.warning("Aún no has subido un archivo.")