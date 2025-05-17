import os
import pyodbc
import pandas as pd
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler


class SQLScriptExecutor:
    def __init__(self, server, database, username=None, password=None, use_windows_authentication=True):
        try:
            if use_windows_authentication:
                conn_str = (
                    f'DRIVER={{SQL Server}};'
                    f'SERVER={server};'
                    f'DATABASE={database};'
                    'Trusted_Connection=yes;'
                )
            else:
                conn_str = (
                    f'DRIVER={{SQL Server}};'
                    f'SERVER={server};'
                    f'DATABASE={database};'
                    f'UID={username};'
                    f'PWD={password};'
                )
            self.conn = pyodbc.connect(conn_str)
            logging.info("Successfully connected to SQL Server.")

        except pyodbc.Error as e:
            logging.error(f"Error connecting to SQL Server: {e}")
            raise

    def execute_script(self, sql_script):
        try:
            df = pd.read_sql(sql_script, self.conn)
            return df
        except pyodbc.Error as e:
            logging.error(f"Error executing SQL script: {e}")
            raise

    def execute_multiple_queries(self, queries):
        results = {}
        try:
            for query in queries:
                name = query.get('name') or f"Sheet{len(results) + 1}"
                sql = query['sql']
                df = pd.read_sql(sql, self.conn)
                results[name[:31]] = df  # Limit sheet name to 31 chars
            return results
        except pyodbc.Error as e:
            logging.error(f"Error executing multiple queries: {e}")
            raise

    def export_to_excel(self, dataframe, output_folder):
        try:
            # Create daily folder based on today's date
            today_folder = datetime.now().strftime("%Y-%m-%d")
            daily_folder = os.path.join(output_folder, today_folder)
            os.makedirs(daily_folder, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"SQLResults_{timestamp}_{unique_id}.xlsx"
            full_path = os.path.join(daily_folder, filename)

            dataframe.to_excel(full_path, index=False)
            logging.info(f"Results exported to: {full_path}")
            return full_path
        except Exception as e:
            logging.error(f"Error exporting to Excel: {e}")
            raise

    def export_multiple_to_excel(self, dataframes_dict, output_folder):
        try:
            # Create daily folder based on today's date
            today_folder = datetime.now().strftime("%Y-%m-%d")
            daily_folder = os.path.join(output_folder, today_folder)
            os.makedirs(daily_folder, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"MultiQueryResults_{timestamp}_{unique_id}.xlsx"
            full_path = os.path.join(daily_folder, filename)

            with pd.ExcelWriter(full_path, engine='openpyxl') as writer:
                for sheet_name, df in dataframes_dict.items():
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

            logging.info(f"Multi-sheet Excel saved: {full_path}")
            return full_path
        except Exception as e:
            logging.error(f"Error exporting multi-sheet Excel: {e}")
            raise

    def close_connection(self):
        if hasattr(self, 'conn'):
            self.conn.close()
            logging.info("Database connection closed.")

# Flask App
app = Flask(__name__)
CORS(app)

# Logging setup
def setup_logging():
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'sql_executor.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
            RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        ]
    )

# Output folder path
OUTPUT_FOLDER = r'D:\\Devops\\Python\\Scripts'  # You can update this path if needed

@app.route('/execute-sql', methods=['POST'])
def execute_sql():
    try:
        data = request.get_json()
        server = data.get('server')
        database = data.get('database')
        auth_type = data.get('authentication', {}).get('type', 'windows')
        output_path = data.get("output_path", OUTPUT_FOLDER)  # <-- Custom output path

        if not server or not database:
            return jsonify({"error": "Server and database are required", "status": "failed"}), 400

        if auth_type == 'windows':
            executor = SQLScriptExecutor(server, database)
        elif auth_type == 'sql':
            username = data['authentication'].get('username')
            password = data['authentication'].get('password')
            if not username or not password:
                return jsonify({"error": "Username and password required for SQL authentication", "status": "failed"}), 400
            executor = SQLScriptExecutor(server, database, username, password, use_windows_authentication=False)
        else:
            return jsonify({"error": "Invalid authentication type", "status": "failed"}), 400

        try:
            if 'queries' in data:
                result_dict = executor.execute_multiple_queries(data['queries'])
                excel_path = executor.export_multiple_to_excel(result_dict, output_path)
            else:
                sql_script = data.get('sql_script')
                if not sql_script:
                    return jsonify({"error": "SQL script is required", "status": "failed"}), 400
                results = executor.execute_script(sql_script)
                excel_path = executor.export_to_excel(results, output_path)

            return jsonify({
                "message": "SQL executed successfully",
                "file_path": excel_path,
                "status": "success"
            })

        finally:
            executor.close_connection()

    except Exception as e:
        logging.error(f"Execution error: {e}")
        return jsonify({"error": str(e), "status": "failed"}), 500


def main():
    setup_logging()
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()
