import pandas as pd
import os
import csv
import sys
import re

# Pedimos la ruta al CSV
ruta_csv = input("Introduce la ruta al archivo CSV: ").strip()

# Verificamos existencia del archivo
if not os.path.exists(ruta_csv) or not os.path.isfile(ruta_csv):
    print(f"❌ Archivo no encontrado: {ruta_csv}")
    sys.exit(1)

# Pedimos el tipo de CSV
print("\nSelecciona el tipo de datos del CSV:")
print("  1. Climatología diaria")
print("  2. Climatología mensual/anual")
print("  3. Extremos Registrados")
print("  4. Valores Normales")
tipo = input("Número de opción: ").strip()

try:
    tipo_int = int(tipo)
except ValueError:
    print("❌ Opción inválida.")
    sys.exit(1)

# Leemos el CSV
df = pd.read_csv(ruta_csv, sep=';', decimal=',', quoting=csv.QUOTE_NONNUMERIC)

# --- Función para limpiar valores tipo "28.4(01)" o "28/22.2(01)" ---
def limpiar_valor(v):
    if isinstance(v, str):
        v = v.strip()
        if '/' in v:  # casos como "28/22.2(01)" → tomamos solo el segundo número
            partes = v.split('/')
            v = partes[-1]
        v = re.sub(r"\(.*?\)", "", v)  # quita paréntesis
        v = v.replace(',', '.')
    try:
        return float(v)
    except:
        return None
# Procesamiento según el tipo
match tipo_int:
    case 1:  # Climatología diaria
        print("🧹 Procesando climatología diaria (viento)...")
        columnas_viento = ["fecha", "estacion", "velmedia", "racha", "dir_racha"]
        df_viento = df[columnas_viento].copy()

        def es_valido_diario(row):
            try:
                return (
                    0 <= float(row["velmedia"]) <= 150 and
                    0 <= float(row["racha"]) <= 300 and
                    0 <= float(row["dir_racha"]) <= 360
                )
            except (ValueError, TypeError):
                return False

        df_limpio = df_viento[df_viento.apply(es_valido_diario, axis=1)]

    case 2:  # Climatología mensual/anual
        print("🧹 Procesando climatología mensual/anual (viento)...")
        columnas_viento = ["fecha", "estacion", "w_racha", "w_med", "w_rec"]
        df_viento = df[columnas_viento].copy()
        df_viento["fecha"] = pd.to_datetime(df_viento["fecha"].astype(str) + "-01", format="%Y-%m-%d", errors="coerce")

  # 🔧 Limpiar valores antes de validar
        for col in ["w_racha", "w_med", "w_rec"]:
            df_viento[col] = df_viento[col].apply(limpiar_valor)

        def es_valido_mensual(row):
            try:
                return (
                    0 <= float(row["w_racha"]) <= 300 and
                    0 <= float(row["w_med"]) <= 150 and
                    0 <= float(row["w_rec"]) <= 300
                )
            except (ValueError, TypeError):
                return False

        df_limpio = df_viento[df_viento.apply(es_valido_mensual, axis=1)]
        df_limpio = df_limpio.sort_values(by="fecha")
    case 3:  # Extremos registrados
        print("🧹 Procesando extremos registrados (viento)...")

        columnas_viento = ["fecha_ocurrencia", "estacion", "rachMax_kmh", "dirRachMax_grados", "dia", "anio"]
    
        # Incluir "hora" si existe en el DataFrame original
        if "hora" in df.columns:
            columnas_viento.append("hora")

        df_viento = df[columnas_viento].copy()

    # ➤ Limpieza básica de columnas numéricas
        def limpiar_int(valor):
            try:
                return int(valor)
            except (ValueError, TypeError):
                return None

        df_viento["dia"] = df_viento["dia"].apply(limpiar_int)
        df_viento["anio"] = df_viento["anio"].apply(limpiar_int)

        # ➤ Limpieza de hora o fecha parcial si existe la columna "hora"
        if "hora" in df_viento.columns:
            def limpiar_hora_o_fecha(valor):
                if isinstance(valor, str):
                    valor = valor.strip().lower()
                # Caso "13-26"
                    if "-" in valor and valor[:2].isdigit() and valor[-2:].isdigit():
                        return valor.replace("-", ":")
                # Caso "20-ago"
                    elif "-" in valor:
                        partes = valor.split("-")
                        if len(partes) == 2:
                            dia, mes = partes
                            meses = {
                            "ene": "01", "feb": "02", "mar": "03", "abr": "04", "may": "05", "jun": "06",
                            "jul": "07", "ago": "08", "sep": "09", "oct": "10", "nov": "11", "dic": "12"
                        }
                            if mes[:3] in meses:
                                return f"{int(dia):02d}-{meses[mes[:3]]}"
                # Caso "may-49"
                    elif valor[:3] in meses and valor[-2:].isdigit():
                        return f"{meses[valor[:3]]}-19{valor[-2:]}"
                return None

        df_viento["hora_limpia"] = df_viento["hora"].apply(limpiar_hora_o_fecha)

    # ➤ Conversión de fecha_ocurrencia a datetime
        df_viento["fecha_ocurrencia"] = pd.to_datetime(df_viento["fecha_ocurrencia"], errors="coerce", dayfirst=True)

    # ➤ Filtro de registros válidos
        def es_valido_extremos(row):
            try:
                return (
                    0 <= float(row["rachMax_kmh"]) <= 300 and
                    0 <= float(row["dirRachMax_grados"]) <= 360 and
                    row["dia"] is not None and 1 <= row["dia"] <= 31 and
                    row["anio"] is not None and 1900 <= row["anio"] <= 2100
                )
            except (ValueError, TypeError):
                return False

        df_limpio = df_viento[df_viento.apply(es_valido_extremos, axis=1)]

    # ➤ Orden final por fecha_ocurrencia, anio, dia
        df_limpio = df_limpio.sort_values(by=["fecha_ocurrencia", "anio", "dia"]).reset_index(drop=True)

    case 4:  # Valores normales
        print("🧹 Procesando valores normales (viento)...")
        # Columnas foco para viento con valores típicos y coef. variación
        columnas_viento = [
            "estacion", "fecha",
            # Ráfagas de viento y velocidad media
            "w_racha_max", "w_racha_min", "w_racha_q1", "w_racha_q2", "w_racha_q3", "w_racha_q4", "w_racha_cv",
            "w_med_max", "w_med_min", "w_med_q1", "w_med_q2", "w_med_q3", "w_med_q4", "w_med_cv"
        ]

        # Filtrar solo las columnas que existen en el dataframe (por si faltan algunas)
        columnas_viento = [col for col in columnas_viento if col in df.columns]

        df_viento = df[columnas_viento].copy()

        # Función para limpiar valores tipo "28.4(01)" o "28/22.2(01)"
        def limpiar_valor(v):
            if isinstance(v, str):
                v = v.strip()
                if '/' in v:  # casos como "28/22.2(01)" → tomamos solo el segundo número
                    partes = v.split('/')
                    v = partes[-1]
                v = re.sub(r"\(.*?\)", "", v)  # quita paréntesis
                v = v.replace(',', '.')
            try:
                return float(v)
            except:
                return None

        # Limpiar columnas numéricas (excepto "estacion" y "fecha")
        cols_a_limpiar = [col for col in columnas_viento if col not in ["estacion", "fecha"]]
        for col in cols_a_limpiar:
            df_viento[col] = df_viento[col].apply(limpiar_valor)

    # Validar que valores de viento estén en rangos razonables
        def es_valido_normales(row):
            try:
            # Validar ráfagas: 0-300 km/h, medias: 0-150 km/h, coef. variación: 0-100%
            # Consideramos None inválido
                for col in cols_a_limpiar:
                    val = row[col]
                    if val is None:
                        return False
                    if "racha" in col and not (0 <= val <= 300):
                        return False
                    if "med" in col and not (0 <= val <= 150):
                        return False
                    if "cv" in col and not (0 <= val <= 100):
                        return False
                return True
            except (ValueError, TypeError):
                return False

        df_limpio = df_viento[df_viento.apply(es_valido_normales, axis=1)]
    case _:
        print("❌ Tipo de archivo no soportado.")
        sys.exit(1)

# Guardamos CSV limpio
salida = os.path.splitext(ruta_csv)[0] + "_viento_limpio.csv"
df_limpio.to_csv(salida, index=False, sep=';', decimal=',', quoting=csv.QUOTE_NONNUMERIC)
print(f"✅ Guardado {len(df_limpio)} registros válidos en: {salida}")


