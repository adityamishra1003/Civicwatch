#!/usr/bin/env python3
"""
CivicWatch — One-command launcher
Run: python run.py
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    os.chdir(Path(__file__).parent)

    # Check .env
    if not Path('.env').exists():
        print("📝 Creating .env from template...")
        import shutil
        shutil.copy('.env.example', '.env')
        print("⚠️  .env created. Add your ANTHROPIC_API_KEY to .env for the AI chatbot.")
        print("   (The app works without it — only the chatbot needs the key)\n")

    # Load env
    from dotenv import load_dotenv
    load_dotenv()

    # Create dirs
    os.makedirs('data/uploads', exist_ok=True)
    os.makedirs('data/chroma', exist_ok=True)

    host = os.getenv('APP_HOST', '127.0.0.1')
    port = os.getenv('APP_PORT', '8000')

    print("=" * 50)
    print("⚡  CivicWatch AI Civic Issue Monitor")
    print("=" * 50)
    print(f"🌐  Citizen Portal:  http://{host}:{port}")
    print(f"📊  Admin Dashboard: http://{host}:{port}/admin")
    print(f"📚  API Docs:        http://{host}:{port}/docs")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")

    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'backend.main:app',
        '--host', host,
        '--port', port,
        '--reload'
    ])

if __name__ == '__main__':
    main()
