import sqlite3
import os
import sys
from datetime import datetime

def get_db_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "ventas.db")

def crear_tablas():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            sucursal TEXT NOT NULL,
            total REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def registrar_venta(fecha, sucursal, total):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ventas (fecha, sucursal, total)
        VALUES (?, ?, ?)
    ''', (fecha, sucursal, total))
    conn.commit()
    conn.close()

def obtener_ventas_por_sucursal(sucursal, fecha_inicio, fecha_fin):
    """
    Las fechas deben estar en formato 'YYYY-MM-DD' para que SQLite las compare correctamente.
    Retorna una lista de tuplas: (fecha, total)
    """
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT fecha, total FROM ventas
        WHERE sucursal = ? AND fecha >= ? AND fecha <= ?
        ORDER BY fecha ASC
    ''', (sucursal, fecha_inicio, fecha_fin))
    resultados = cursor.fetchall()
    conn.close()
    return resultados
