import sqlite3

def run():
    conn = sqlite3.connect('it_platform.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE rds_configs ADD COLUMN file_prefix VARCHAR DEFAULT 'nova.ft';")
        conn.commit()
        print("Migration successful")
    except Exception as e:
        print("Migration error:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    run()
