"""
Taller 3 - Infraestructuras
Comparación de tiempos: versión secuencial vs. versión concurrente con 1, 2, 4 y 8 hilos.
Reutiliza las funciones de analisis_insumos_concurrente.py (deben estar en la misma carpeta).
"""
import csv
import os
import statistics
import time

import analisis_insumos_concurrente as base

HILOS_A_PROBAR = [1, 2, 4, 8]
REPETICIONES = 7   # Cada configuración se mide varias veces y se toma la mediana


def medir(funcion):
    """Ejecuta la función una vez y devuelve cuánto tardó (en segundos)."""
    inicio = time.perf_counter()
    funcion()
    return time.perf_counter() - inicio


def main():
    # La lectura se hace una sola vez: aquí solo se mide el procesamiento
    datos = {}
    for tipo, nombre in base.ARCHIVOS.items():
        datos[tipo] = base.leer_lineas(base.buscar_archivo(nombre))
    total = sum(len(l) for l in datos.values())
    print(f"Registros a procesar: {total:,}".replace(",", "."))
    print(f"Repeticiones por configuración: {REPETICIONES} (se reporta la mediana)\n")

    def secuencial():
        for tipo, lineas in datos.items():
            base.procesar_secuencial(lineas, tipo)

    def concurrente(num_hilos):
        for tipo, lineas in datos.items():
            base.procesar_concurrente(lineas, tipo, num_hilos)

    # Calentamiento: una pasada sin medir, para que la primera medición no salga inflada
    secuencial()
    concurrente(4)

    # Las configuraciones se alternan en cada repetición, así ninguna se favorece por el orden
    configuraciones = [("Secuencial", 1, secuencial)]
    for n in HILOS_A_PROBAR:
        configuraciones.append(("Concurrente", n, lambda n=n: concurrente(n)))

    tiempos = {i: [] for i in range(len(configuraciones))}
    for _ in range(REPETICIONES):
        for i, (version, n, funcion) in enumerate(configuraciones):
            tiempos[i].append(medir(funcion))

    t_sec = statistics.median(tiempos[0])
    filas = []
    for i, (version, n, funcion) in enumerate(configuraciones):
        t = statistics.median(tiempos[i])
        filas.append((version, n, t, t_sec / t))

    print(f"{'Versión':<14}{'Hilos':>6}{'Mediana (s)':>14}{'Aceleración':>14}")
    for version, n, t, acel in filas:
        print(f"{version:<14}{n:>6}{t:>14.3f}{acel:>13.2f}x")

    ruta = os.path.join(base.BASE, "tiempos_hilos.csv")
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo, delimiter=";")
        escritor.writerow(["Versión", "Hilos", "Mediana (s)", "Aceleración"])
        for version, n, t, acel in filas:
            escritor.writerow([version, n, f"{t:.3f}".replace(".", ","),
                               f"{acel:.2f}".replace(".", ",")])
    print(f"\nTabla guardada en: {ruta}")


if __name__ == "__main__":
    main()