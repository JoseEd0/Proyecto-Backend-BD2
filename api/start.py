#!/usr/bin/env python3
"""
Script de inicio para la API del Parser SQL
Proyecto CS2702 - Base de Datos 2 UTEC

Este script instala dependencias e inicia el servidor FastAPI
"""

import subprocess
import sys
import os


def install_requirements():
    """Instalar las dependencias necesarias"""
    print("📦 Instalando dependencias...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error instalando dependencias")
        return False


def start_server():
    """Iniciar el servidor FastAPI"""
    print("\n🚀 Iniciando servidor FastAPI...")
    print("📖 Documentación API: http://localhost:8000/docs")
    print("🌐 Interfaz Web: http://localhost:8000/")
    print("⏹️  Presiona Ctrl+C para detener\n")

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload",
            ]
        )
    except KeyboardInterrupt:
        print("\n⏹️  Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")


def main():
    """Función principal"""
    print("=" * 60)
    print("🗄️  API PARSER SQL - CS2702 UTEC")
    print("=" * 60)

    # Cambiar al directorio de la API
    api_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(api_dir)

    # Verificar si las dependencias están instaladas
    try:
        import fastapi
        import uvicorn

        print("✅ Dependencias ya instaladas")
    except ImportError:
        if not install_requirements():
            sys.exit(1)

    # Iniciar servidor
    start_server()


if __name__ == "__main__":
    main()
