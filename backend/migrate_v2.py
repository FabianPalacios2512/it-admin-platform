"""
migrate_v2.py — Migración de Base de Datos: Monitoreo v2.0
============================================================
Agrega soporte Multi-OS (Linux/SSH) al modelo server_configs.

Columnas nuevas:
  - os_type  TEXT NOT NULL DEFAULT 'windows'
  - ssh_user TEXT
  - ssh_key  TEXT
  - ssh_port INTEGER NOT NULL DEFAULT 22

Uso:
    cd backend
    python migrate_v2.py

Seguro de ejecutar múltiples veces (idempotente).
"""

import sqlite3
import os
import sys

# Ruta a la base de datos — ajusta si tu .env la apunta a otro lugar
DB_PATH = os.path.join(os.path.dirname(__file__), "it_platform.db")

MIGRATIONS = [
    ("os_type",  "ALTER TABLE server_configs ADD COLUMN os_type  TEXT NOT NULL DEFAULT 'windows'"),
    ("ssh_user", "ALTER TABLE server_configs ADD COLUMN ssh_user TEXT"),
    ("ssh_key",  "ALTER TABLE server_configs ADD COLUMN ssh_key  TEXT"),
    ("ssh_port", "ALTER TABLE server_configs ADD COLUMN ssh_port INTEGER NOT NULL DEFAULT 22"),
]


def get_existing_columns(cursor) -> set:
    cursor.execute("PRAGMA table_info(server_configs)")
    return {row[1] for row in cursor.fetchall()}


def run():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No se encontró la base de datos en: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    existing = get_existing_columns(cur)
    applied = 0

    for col_name, sql in MIGRATIONS:
        if col_name in existing:
            print(f"  [SKIP]  Columna '{col_name}' ya existe.")
        else:
            try:
                cur.execute(sql)
                conn.commit()
                print(f"  [OK]    Columna '{col_name}' agregada correctamente.")
                applied += 1
            except Exception as e:
                print(f"  [ERROR] No se pudo agregar '{col_name}': {e}")
                conn.rollback()

    conn.close()

    if applied == 0:
        print("\n[OK] La base de datos ya esta actualizada. No se requirieron cambios.")
    else:
        print(f"\n[OK] Migracion completada. Se aplicaron {applied} cambio(s).")


if __name__ == "__main__":
    print(f"Migrando base de datos: {DB_PATH}\n")
    run()
