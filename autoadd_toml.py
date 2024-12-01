import argparse
import requests
import subprocess
import os
import shutil

def check_file_exists(url):
    """Проверяет наличие файла по указанному URL."""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"Ошибка при доступе к {url}: {e}")
        return False

def download_file(url, filename):
    """Скачивает файл по указанному URL и сохраняет под заданным именем."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, "wb") as file:
            file.write(response.content)
        print(f"Файл скачан и сохранен как {filename}")
        return True
    except requests.RequestException as e:
        print(f"Ошибка при скачивании {url}: {e}")
        return False

def run_nvchecker(config_file):
    """Запускает nvchecker с указанным конфигурационным файлом."""
    try:
        result = subprocess.run(["nvchecker", "-c", config_file], check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении nvchecker: {e}")
        return False

def git_operations(repo_url, branch, file_to_add, commit_message, home_dir):
    """Клонирует репозиторий, добавляет файл, делает коммит и пуш."""
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    repo_path = os.path.join(home_dir, repo_name)

    try:
        # Удаление каталога, если он существует
        if os.path.exists(repo_path):
            print(f"Каталог {repo_path} существует. Удаляем...")
            shutil.rmtree(repo_path)

        # Клонирование репозитория
        subprocess.run(["git", "clone", "-b", branch, repo_url, repo_path], check=True)
        print(f"Клонирован репозиторий {repo_name} в {repo_path}.")

        # Перемещение файла .nvchecker.toml в каталог репозитория
        project_nvchecker_path = os.path.join(repo_path, file_to_add)
        shutil.move(file_to_add, project_nvchecker_path)
        print(f"Файл {file_to_add} перемещен в {project_nvchecker_path}.")

        # Выполнение Git-операций
        os.chdir(repo_path)
        subprocess.run(["git", "add", file_to_add], check=True)
        print(f"Файл {file_to_add} добавлен в индекс.")
        subprocess.run(["git", "commit", "-am", commit_message], check=True)
        print(f"Коммит с сообщением '{commit_message}' создан.")
        subprocess.run(["git", "push"], check=True)
        print("Изменения отправлены в удаленный репозиторий.")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении Git-операции: {e}")
    finally:
        os.chdir(home_dir)

def main():
    parser = argparse.ArgumentParser(description="Автоматический скрипт для проверки и скачивания .nvchecker.toml.")
    parser.add_argument("--package", required=True, help="Имя пакета для проверки.")
    args = parser.parse_args()

    package_name = args.package
    home_dir = os.path.expanduser("~")

    # URL-адреса
    rosa_url = f"https://abf.io/import/{package_name}/raw/rosa2023.1/.nvchecker.toml"
    arch_url = f"https://gitlab.archlinux.org/archlinux/packaging/packages/{package_name}/-/raw/main/.nvchecker.toml"

    # Проверяем наличие файла на ROSA
    if check_file_exists(rosa_url):
        print("Файл .nvchecker.toml уже существует в ROSA. Действие не требуется.")
        return

    print("Файл .nvchecker.toml отсутствует в ROSA. Проверяем в Arch Linux...")

    # Проверяем наличие файла в Arch Linux
    if not check_file_exists(arch_url):
        print("Файл .nvchecker.toml отсутствует в Arch Linux. Завершаем работу.")
        return

    print("Файл .nvchecker.toml найден в Arch Linux. Скачиваем...")

    # Скачиваем файл из Arch Linux
    local_file = ".nvchecker.toml"
    if not download_file(arch_url, local_file):
        print("Не удалось скачать файл. Завершаем работу.")
        return

    print("Запускаем nvchecker...")

    # Запускаем nvchecker
    if run_nvchecker(local_file):
        print("nvchecker выполнен успешно. Выполняем Git-операции...")
        repo_url = f"git@abf.io:import/{package_name}.git"
        branch = "rosa2023.1"
        git_operations(repo_url, branch, local_file, "autoadd .nvchecker.toml", home_dir)
    else:
        print("Ошибка при выполнении nvchecker. Завершаем работу.")

if __name__ == "__main__":
    main()

