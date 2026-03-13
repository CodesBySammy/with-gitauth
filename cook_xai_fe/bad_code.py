import sqlite3
from hashlib import md5

def process_user_data(username, password, roles=[]):
    """
    Simulated user processing function with multiple issues.
    """
    # 🐛 Bug 1: Mutable default argument 'roles=[]' (Catched by AST Engine)
    roles.append("USER")
    
    # 🔴 Bug 2: Security vulnerability - Weak hashing (Catched by CodeBERT)
    hashed_pw = md5(password.encode()).hexdigest()
    
    try:
        # 🔴 Bug 3: Security vulnerability - SQL Injection (Catched by CodeBERT)
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + hashed_pw + "'"
        cursor.execute(query)
        res = cursor.fetchone()
        
        # 🔴 Bug 4: High Cyclomatic Complexity (Catched by AST Engine)
        if res:
            if res[2] == "ADMIN":
                print("Admin login")
                if "SUPER" in roles:
                    print("Super admin!")
                    if len(password) < 8:
                        print("Warning: Admin password very short")
                        if username.startswith("test"):
                            print("Oh no, test admin account used!")
            else:
                print("Normal user login")
                if len(password) < 8:
                    print("Warning: Password very short")
                    
    except Exception:
        # 🚨 Bug 5: Silent Failure (Catched by AST Engine)
        pass 
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    process_user_data("admin", "1234")
