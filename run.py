import sys
import subprocess
import os

def run():
    # Menggunakan executable Python saat ini
    python_exe = sys.executable

    if len(sys.argv) > 1 and sys.argv[1].lower() == "fastapi":
        print("=" * 65)
        print(" [PatentGuard] Menjalankan Backend FastAPI & Web Dashboard...")
        print(" Server URL: http://localhost:8000")
        print("=" * 65)
        subprocess.run([python_exe, "-m", "uvicorn", "app:app", "--port", "8000", "--reload"])
    else:
        print("=" * 65)
        print(" [PatentGuard] Menjalankan Aplikasi Web Terpadu (Streamlit)...")
        print(" Membuka antarmuka Streamlit di peramban...")
        print("=" * 65)
        subprocess.run([python_exe, "-m", "streamlit", "run", "streamlit_app.py"])

if __name__ == "__main__":
    run()
