import os
import psycopg2
import sqlparse
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def create_database_if_not_exists(db_params):
    """Create the database if it doesn't exist."""
    try:
        # Connect to PostgreSQL server without specifying a database
        conn_params = db_params.copy()
        conn_params['dbname'] = 'postgres'
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_params['dbname'],))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {db_params['dbname']}")
            print(f"Database {db_params['dbname']} created successfully!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        raise

def drop_triggers_if_exist(cur):
    """Drop existing triggers to avoid conflicts."""
    try:
        cur.execute("""
            DROP TRIGGER IF EXISTS update_agents_updated_at ON core.agents;
            DROP TRIGGER IF EXISTS update_rate_limits_updated_at ON security.rate_limits;
        """)
    except Exception as e:
        print(f"Warning when dropping triggers: {str(e)}")

def init_database():
    # Load environment variables
    load_dotenv()
    
    # Database connection parameters
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'user': os.getenv('DB_USER', 'mycosoft'),
        'password': os.getenv('DB_PASSWORD', 'mycosoft'),
        'dbname': os.getenv('DB_NAME', 'mycosoft')
    }
    
    try:
        # 1) Create DB if needed
        create_database_if_not_exists(db_params)
        
        # 2) Connect to the DB
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # 3) Drop old triggers
        drop_triggers_if_exist(cur)
        
        # 4) Read the entire SQL file
        with open('migrations/init.sql', 'r') as f:
            sql_script = f.read()
        
        # 5) Use sqlparse to safely split the script into statements
        statements = sqlparse.split(sql_script)
        
        # 6) Execute each statement individually
        for statement in statements:
            statement = statement.strip()
            if statement:  # Skip any empty strings that can appear
                try:
                    cur.execute(statement)
                except Exception as e:
                    # If something "already exists" we can ignore — otherwise, raise the error
                    if 'already exists' not in str(e):
                        raise
                    print(f"Warning: {str(e)}")
        
        # 7) Ensure the rate_limits table has the correct structure
        try:
            cur.execute("""
                ALTER TABLE security.rate_limits 
                ADD CONSTRAINT rate_limits_service_endpoint_key 
                UNIQUE (service, endpoint)
            """)
        except Exception as e:
            if 'already exists' not in str(e):
                print(f"Warning when adding constraint: {str(e)}")
        
        # 8) Insert initial rate limits
        rate_limits = [
            ('stripe', '/v1/customers', 100, 60),
            ('stripe', '/v1/payments', 100, 60),
            ('mercury', '/v1/accounts', 50, 60),
            ('mercury', '/v1/transactions', 50, 60),
            ('openai', '/v1/chat/completions', 60, 60),
            ('anthropic', '/v1/messages', 30, 60),
            ('azure', '/v1/chat/completions', 100, 60),
            ('google', '/v1/generate', 100, 60)
        ]
        
        for service, endpoint, max_requests, time_window in rate_limits:
            try:
                # First try to update existing record
                cur.execute("""
                    UPDATE security.rate_limits 
                    SET max_requests = %s, 
                        time_window = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE service = %s AND endpoint = %s
                """, (max_requests, time_window, service, endpoint))
                
                # If no rows were updated, insert new record
                if cur.rowcount == 0:
                    cur.execute("""
                        INSERT INTO security.rate_limits 
                        (service, endpoint, max_requests, time_window)
                        VALUES (%s, %s, %s, %s)
                    """, (service, endpoint, max_requests, time_window))
            except Exception as e:
                print(f"Warning when handling rate limit for {service} {endpoint}: {str(e)}")
        
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def verify_database():
    """Verify database setup by checking tables and connections."""
    load_dotenv()
    
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'user': os.getenv('DB_USER', 'mycosoft'),
        'password': os.getenv('DB_PASSWORD', 'mycosoft'),
        'dbname': os.getenv('DB_NAME', 'mycosoft')
    }
    
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()
        
        # Check schemas
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('core', 'financial', 'monitoring', 'security')
        """)
        schemas = cur.fetchall()
        print("Schemas present:", [s[0] for s in schemas])
        
        # Check tables
        tables_to_check = [
            'core.agents', 'core.messages', 
            'financial.transactions',
            'monitoring.metrics', 'monitoring.alerts',
            'security.api_keys', 'security.rate_limits'
        ]
        
        for table in tables_to_check:
            schema, table_name = table.split('.')
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                )
            """, (schema, table_name))
            exists = cur.fetchone()[0]
            print(f"Table {table}: {'✓' if exists else '✗'}")
        
        # Check rate limits
        cur.execute("SELECT COUNT(*) FROM security.rate_limits")
        rate_limits_count = cur.fetchone()[0]
        print(f"Rate limits configured: {rate_limits_count}")
        
        print("\nDatabase verification completed successfully!")
        
    except Exception as e:
        print(f"Error during verification: {str(e)}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_database()
    verify_database() 