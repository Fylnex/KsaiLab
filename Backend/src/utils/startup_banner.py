# -*- coding: utf-8 -*-
"""
Модуль для отображения красивого баннера при запуске приложения.
"""

import platform
import sys
from datetime import datetime

from src.config.settings import settings


def get_system_info():
    """Получает информацию о системе."""
    return {
        "os": f"{platform.system()} {platform.release()}",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "hostname": platform.node(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "platform": platform.platform(),
    }


def get_app_banner():
    """Возвращает красивый ASCII баннер для приложения."""
    banner = """
                                                                                                 
    ███████╗██████╗        ██████╗ ██╗      █████╗ ████████╗███████╗ ██████╗ ██████╗ ███╗   ███╗ 
    ██╔════╝██╔══██╗       ██╔══██╗██║     ██╔══██╗╚══██╔══╝██╔════╝██╔═══██╗██╔══██╗████╗ ████║ 
    █████╗  ██║  ██║       ██████╔╝██║     ███████║   ██║   █████╗  ██║   ██║██████╔╝██╔████╔██║ 
    ██╔══╝  ██║  ██║       ██╔═══╝ ██║     ██╔══██║   ██║   ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║ 
    ███████╗██████╔╝██╗    ██║     ███████╗██║  ██║   ██║   ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║ 
    ╚══════╝╚═════╝ ╚═╝    ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝ 
                                                                                                 
                           🎓 Educational Platform API 🚀                                        
                                                                                                 
    """
    return banner


def get_startup_info():
    """Возвращает информацию о запуске приложения."""
    system = get_system_info()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Используем простые f-строки без выравнивания, чтобы избежать конфликтов и синтаксических ошибок
    # Внешние URL для prod/dev
    if settings.app_domain:
        api_external = f"http://{settings.app_domain}/api"
    else:
        fe_port = settings.frontend_port or 3000
        api_external = f"http://localhost:{fe_port}/api"

    minio_external = settings.public_minio_endpoint or settings.minio_endpoint

    info = (
        f"\n"
        f"      📅 Запуск: {now}\n"
        f"      🖥️  Система: {system['os']} ({system['architecture']})\n"
        f"      🐍 Python: {system['python']}\n"
        f"      🏠 Хост: {system['hostname']}\n"
        f"      🌐 API: {api_external}\n"
        f"      📊 База данных: {settings.postgres_db}@{settings.postgres_host}:{settings.postgres_port}\n"
        f"      📦 MinIO: {minio_external}\n"
        f"      ⚙️  Конфиг: {settings.get_config_source()}\n"
    )
    return info


def print_startup_banner():
    """Выводит полный баннер при запуске."""
    try:
        print(get_app_banner())
        print(get_startup_info())
        print("    " + "=" * 80)
    except UnicodeEncodeError:
        # Fallback для Windows консоли с проблемами кодировки
        print("=" * 80)
        print("Educational Platform API")
        print("=" * 80)
        print(get_startup_info())
        print("    " + "=" * 80)
