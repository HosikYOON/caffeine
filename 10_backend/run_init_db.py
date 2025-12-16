import psycopg2
import os

# DB Connection Params
DB_HOST = "caffeine-database.c58og6ke6t36.ap-northeast-2.rds.amazonaws.com"
DB_USER = "postgres"
DB_PASS = "caffeineapprds"
DB_NAME = "postgres"
DB_PORT = "5432"

SCRIPT_PATH = r"c:\caffeine\10_backend\init_db_reset.sql"

def run_db_init():
    print(f"Connecting to {DB_HOST}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME,
            port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print(f"Reading SQL script from {SCRIPT_PATH}...")
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()
            
        print("Executing SQL script...")
        cur.execute(sql_script)
        
        print("Database initialization completed successfully.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_db_init()
