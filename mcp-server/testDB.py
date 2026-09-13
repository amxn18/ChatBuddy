from db.connection import get_connection
try:
    conn = get_connection()
    print("Success")
    conn.close()
except Exception as e:
    print("failed")
    print(e)