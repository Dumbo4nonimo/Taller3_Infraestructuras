"""
Taller 3 - Infraestructuras
Análisis concurrente (Map y Reduce con hilos) de precios de insumos agropecuarios.
Fuente de datos: DANE - SIPSA-I 2026 (insumos agrícolas e insumos pecuarios).

Para cada combinación (tipo de insumo, departamento, categoría CPC) calcula:
número de registros, precio promedio, precio mínimo y precio máximo.
"""
import csv
import glob
import os
import threading
import time

# ----------------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------------
NUM_HILOS = 4                  # Número de hilos (secciones) para la fase Map
MIN_REGISTROS_RESUMEN = 100    # Mínimo de registros para aparecer en el resumen
BASE = os.path.dirname(os.path.abspath(__file__))  # Carpeta donde está este script

ARCHIVOS = {
    "agricola": "Insumos agricolas - BD SIPSA_I 2026.csv",
    "pecuario": "insumos pecuarios - BD SIPSA_I 2026.csv",
}

# Códigos DIVIPOLA (DANE) de los 25 departamentos presentes en los datos
DEPARTAMENTOS = {
    "05": "Antioquia", "08": "Atlántico", "11": "Bogotá D.C.", "13": "Bolívar",
    "15": "Boyacá", "17": "Caldas", "18": "Caquetá", "19": "Cauca",
    "20": "Cesar", "23": "Córdoba", "25": "Cundinamarca", "41": "Huila",
    "47": "Magdalena", "50": "Meta", "52": "Nariño", "54": "Norte de Santander",
    "63": "Quindío", "66": "Risaralda", "68": "Santander", "70": "Sucre",
    "73": "Tolima", "76": "Valle del Cauca", "81": "Arauca", "85": "Casanare",
    "86": "Putumayo",
}


# ----------------------------------------------------------------------------
# Lectura de datos
# ----------------------------------------------------------------------------
def buscar_archivo(nombre):
    """Busca el CSV dentro de la carpeta del proyecto (incluye subcarpetas)."""
    rutas = glob.glob(os.path.join(BASE, "**", nombre), recursive=True)
    if not rutas:
        raise FileNotFoundError(
            f"No se encontró '{nombre}' dentro de {BASE}. "
            "Descomprime el zip del DANE en la carpeta del proyecto."
        )
    return rutas[0]


def leer_lineas(ruta):
    """Lee el archivo y devuelve sus líneas SIN interpretarlas (sin encabezado)."""
    with open(ruta, encoding="latin-1") as archivo:  # El CSV viene en latin-1
        lineas = archivo.read().splitlines()
    return lineas[1:]  # Se descarta la primera línea (encabezado)


# ----------------------------------------------------------------------------
# Fase MAP: resume una sección del archivo
# ----------------------------------------------------------------------------
def map_function(seccion, results, index, tipo):
    """
    Procesa una sección de líneas y guarda un resumen parcial en results[index].
    El resumen es un diccionario: (tipo, departamento, cpc) -> [n, suma, mínimo, máximo]
    """
    resumen = {}
    for linea in seccion:
        campos = linea.split(";")           # El separador del CSV es ';'
        if len(campos) != 8:                # Línea mal formada: se ignora
            continue
        departamento = campos[1]
        cpc = campos[2]
        precio = int(campos[7].strip().replace(".", ""))  # '194.000' -> 194000

        clave = (tipo, departamento, cpc)
        if clave in resumen:
            r = resumen[clave]
            r[0] += 1                       # cantidad de registros
            r[1] += precio                  # suma de precios
            if precio < r[2]:
                r[2] = precio               # mínimo
            if precio > r[3]:
                r[3] = precio               # máximo
        else:
            resumen[clave] = [1, precio, precio, precio]
    results[index] = resumen                # Cada hilo escribe solo en SU posición


# ----------------------------------------------------------------------------
# Fase REDUCE: combina los resúmenes parciales
# ----------------------------------------------------------------------------
def reduce_function(mapped_results):
    """Combina los diccionarios parciales en un único diccionario total."""
    total = {}
    for resumen in mapped_results:
        for clave, (n, suma, minimo, maximo) in resumen.items():
            if clave in total:
                t = total[clave]
                t[0] += n                   # se suman las cantidades
                t[1] += suma                # se suman las sumas de precios
                t[2] = min(t[2], minimo)    # menor de los mínimos
                t[3] = max(t[3], maximo)    # mayor de los máximos
            else:
                total[clave] = [n, suma, minimo, maximo]
    return total


# ----------------------------------------------------------------------------
# Ejecución concurrente y secuencial
# ----------------------------------------------------------------------------
def dividir_en_secciones(lineas, num_secciones):
    """Divide la lista de líneas en secciones de tamaño similar (por líneas completas)."""
    tamano = len(lineas) // num_secciones
    secciones = []
    for i in range(num_secciones):
        inicio = i * tamano
        fin = inicio + tamano if i < num_secciones - 1 else len(lineas)  # la última toma el resto
        secciones.append(lineas[inicio:fin])
    return secciones


def procesar_concurrente(lineas, tipo, num_hilos):
    """Versión concurrente: un hilo por sección (Map) y luego Reduce."""
    secciones = dividir_en_secciones(lineas, num_hilos)
    results = [None] * len(secciones)       # Lista para almacenar los resultados del Map
    hilos = []

    for i, seccion in enumerate(secciones):  # Crear hilos para la fase Map
        hilo = threading.Thread(target=map_function, args=(seccion, results, i, tipo))
        hilos.append(hilo)
        hilo.start()

    for hilo in hilos:                       # Esperar a que todos los hilos terminen
        hilo.join()

    return reduce_function(results)          # Fase Reduce


def procesar_secuencial(lineas, tipo):
    """Versión secuencial (referencia): una sola sección, sin hilos."""
    results = [None]
    map_function(lineas, results, 0, tipo)
    return reduce_function(results)


# ----------------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------------
def pesos(valor):
    """Formatea un número como pesos colombianos: 1234567 -> $1.234.567"""
    return "$" + f"{valor:,.0f}".replace(",", ".")


def guardar_csv(resultado, ruta):
    """Guarda la tabla final (una fila por grupo) en un CSV legible en Excel."""
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo, delimiter=";")
        escritor.writerow(["Tipo", "Departamento", "Código DIVIPOLA", "Categoría CPC",
                           "Registros", "Precio promedio", "Precio mínimo", "Precio máximo"])
        for (tipo, depto, cpc) in sorted(resultado):
            n, suma, minimo, maximo = resultado[(tipo, depto, cpc)]
            escritor.writerow([tipo, DEPARTAMENTOS.get(depto, depto), depto, cpc,
                               n, round(suma / n), minimo, maximo])


def mostrar_resumen(resultado):
    """Muestra los 10 grupos con mayor precio promedio (con suficientes registros)."""
    filas = []
    for (tipo, depto, cpc), (n, suma, minimo, maximo) in resultado.items():
        if n >= MIN_REGISTROS_RESUMEN:
            filas.append((suma / n, tipo, depto, cpc, n, minimo, maximo))
    filas.sort(reverse=True)

    print(f"\nTop 10 grupos con mayor precio promedio (mínimo {MIN_REGISTROS_RESUMEN} registros):")
    print(f"{'Tipo':<9}{'Departamento':<20}{'CPC':<10}{'Registros':>10}"
          f"{'Promedio':>14}{'Mínimo':>14}{'Máximo':>14}")
    for promedio, tipo, depto, cpc, n, minimo, maximo in filas[:10]:
        print(f"{tipo:<9}{DEPARTAMENTOS.get(depto, depto):<20}{cpc:<10}{n:>10}"
              f"{pesos(promedio):>14}{pesos(minimo):>14}{pesos(maximo):>14}")


# ----------------------------------------------------------------------------
# Programa principal
# ----------------------------------------------------------------------------
def main():
    print("=== Análisis concurrente de precios de insumos agropecuarios (SIPSA-I 2026) ===")
    print(f"Hilos por archivo: {NUM_HILOS}\n")

    # 1. Lectura de los archivos (la hace el hilo principal)
    inicio = time.perf_counter()
    datos = {}
    for tipo, nombre in ARCHIVOS.items():
        datos[tipo] = leer_lineas(buscar_archivo(nombre))
        print(f"Archivo {tipo}: {len(datos[tipo]):,} registros leídos".replace(",", "."))
    t_lectura = time.perf_counter() - inicio

    # 2. Procesamiento concurrente (Map con hilos + Reduce)
    inicio = time.perf_counter()
    resultado_conc = {}
    for tipo, lineas in datos.items():
        resultado_conc.update(procesar_concurrente(lineas, tipo, NUM_HILOS))
    t_conc = time.perf_counter() - inicio

    # 3. Procesamiento secuencial (referencia para validar y comparar)
    inicio = time.perf_counter()
    resultado_sec = {}
    for tipo, lineas in datos.items():
        resultado_sec.update(procesar_secuencial(lineas, tipo))
    t_sec = time.perf_counter() - inicio

    # 4. Validación
    total_lineas = sum(len(l) for l in datos.values())
    total_procesados = sum(v[0] for v in resultado_conc.values())
    print("\n--- Validación ---")
    print(f"Grupos obtenidos (tipo, departamento, categoría): {len(resultado_conc)}")
    print(f"Registros procesados: {total_procesados:,} de {total_lineas:,}".replace(",", "."))
    print("Concurrente == Secuencial:", resultado_conc == resultado_sec)

    # 5. Tiempos
    print("\n--- Tiempos (segundos) ---")
    print(f"Lectura de archivos:        {t_lectura:.3f}")
    print(f"Procesamiento concurrente:  {t_conc:.3f}  ({NUM_HILOS} hilos por archivo)")
    print(f"Procesamiento secuencial:   {t_sec:.3f}")
    print(f"Relación secuencial/concurrente: {t_sec / t_conc:.2f}x")

    # 6. Resultados
    mostrar_resumen(resultado_conc)
    ruta_salida = os.path.join(BASE, "resultados_precios_insumos.csv")
    guardar_csv(resultado_conc, ruta_salida)
    print(f"\nTabla completa guardada en: {ruta_salida}")


if __name__ == "__main__":
    main()