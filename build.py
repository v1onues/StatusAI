import os
import sys
import subprocess
import shutil


def run_build():
    print("========================================")
    print("   StatusAI — Desktop Executable Builder ")
    print("========================================")

    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller

        print("[+] PyInstaller buludu.")
    except ImportError:
        print("[-] PyInstaller bulunamadı. Kuruluyor...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[+] PyInstaller başarıyla kuruldu.")

    # 2. Check icon
    icon_param = ""
    if os.path.exists("icon.ico"):
        icon_param = "--icon=icon.ico"
        print("[+] icon.ico bulundu ve eklenecek.")
    else:
        print(
            "[-] warning: icon.ico bulunamadı, varsayılan PyInstaller simgesi kullanılacak."
        )

    # 3. Handle data files syntax for Windows
    data_separator = ";" if sys.platform.startswith("win") else ":"

    print(
        "\n[+] Derleme başlatılıyor.. Lütfen bekleyin. (Bu işlem birkaç dakika sürebilir)"
    )

    # Run PyInstaller
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "StatusAI",
        f"--add-data=templates{data_separator}templates",
        f"--add-data=version.json{data_separator}.",
        f"--add-data=logo.jpg{data_separator}.",
        f"--add-data=icon.ico{data_separator}.",
        "--exclude-module",
        "torch",
        "--exclude-module",
        "tensorflow",
        "--exclude-module",
        "pandas",
        "--exclude-module",
        "numpy",
        "dashboard.py",
    ]

    if icon_param:
        cmd.insert(-1, icon_param)

    try:
        subprocess.check_call(cmd)
        print("\n========================================")
        print("✅ BAŞARILI: Derleme Tamamlandı!")
        print(
            f"✅ Executable şurada bulunabilir: {os.path.join(os.getcwd(), 'dist', 'StatusAI.exe')}"
        )
        print("========================================")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ HATA: PyInstaller derlemesi başarısız oldu. {e}")


if __name__ == "__main__":
    run_build()
