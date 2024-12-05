import argparse
import requests
import subprocess
import os
import shutil
import logging

def setup_logging(log_file):
    """Настраивает логгирование в файл."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode='w'),
            logging.StreamHandler()
        ]
    )

def check_file_exists(url):
    """Проверяет наличие файла по указанному URL."""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except requests.RequestException as e:
        logging.error(f"Ошибка при доступе к {url}: {e}")
        return False

def download_file(url, filename):
    """Скачивает файл по указанному URL и сохраняет под заданным именем."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, "wb") as file:
            file.write(response.content)
        logging.info(f"Файл скачан и сохранен как {filename}")
        return True
    except requests.RequestException as e:
        logging.error(f"Ошибка при скачивании {url}: {e}")
        return False

def run_nvchecker(config_file):
    """Запускает nvchecker с указанным конфигурационным файлом."""
    try:
        result = subprocess.run(["nvchecker", "-c", config_file], check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка при выполнении nvchecker: {e}")
        return False

def git_operations(repo_url, branch, file_to_add, commit_message, home_dir):
    """Клонирует репозиторий, добавляет файл, делает коммит и пуш."""
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    repo_path = os.path.join(home_dir, repo_name)

    try:
        if os.path.exists(repo_path):
            logging.info(f"Каталог {repo_path} существует. Удаляем...")
            shutil.rmtree(repo_path)

        subprocess.run(["git", "clone", "-b", branch, repo_url, repo_path], check=True)
        logging.info(f"Клонирован репозиторий {repo_name} в {repo_path}.")

        project_nvchecker_path = os.path.join(repo_path, file_to_add)
        shutil.move(file_to_add, project_nvchecker_path)
        logging.info(f"Файл {file_to_add} перемещен в {project_nvchecker_path}.")

        os.chdir(repo_path)
        subprocess.run(["git", "add", file_to_add], check=True)
        logging.info(f"Файл {file_to_add} добавлен в индекс.")
        subprocess.run(["git", "commit", "-am", commit_message], check=True)
        logging.info(f"Коммит с сообщением '{commit_message}' создан.")
        subprocess.run(["git", "push"], check=True)
        logging.info("Изменения отправлены в удаленный репозиторий.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка при выполнении Git-операции: {e}")
    finally:
        os.chdir(home_dir)

def process_package(package_name, home_dir):
    """Обрабатывает один пакет."""
    rosa_url = f"https://abf.io/import/{package_name}/raw/rosa2023.1/.nvchecker.toml"
    arch_url = f"https://gitlab.archlinux.org/archlinux/packaging/packages/{package_name}/-/raw/main/.nvchecker.toml"

    if check_file_exists(rosa_url):
        logging.info(f"Файл .nvchecker.toml уже существует для {package_name}.")
        return

    logging.info(f"Файл .nvchecker.toml отсутствует для {package_name}. Проверяем в Arch Linux...")

    if not check_file_exists(arch_url):
        logging.warning(f"Файл .nvchecker.toml отсутствует для {package_name} в Arch Linux.")
        return

    local_file = ".nvchecker.toml"
    if not download_file(arch_url, local_file):
        logging.error(f"Не удалось скачать файл для {package_name}.")
        return

    if run_nvchecker(local_file):
        repo_url = f"git@abf.io:import/{package_name}.git"
        branch = "rosa2023.1"
        git_operations(repo_url, branch, local_file, f"autoadd .nvchecker.toml for {package_name}", home_dir)
    else:
        logging.error(f"Ошибка при выполнении nvchecker для {package_name}.")

def main():
    parser = argparse.ArgumentParser(description="Автоматический скрипт для проверки и скачивания .nvchecker.toml.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", help="Имя пакета для обработки.")
    group.add_argument("--file", help="Файл со списком пакетов.")
    parser.add_argument("--log", required=True, help="Файл для сохранения лога.")
    args = parser.parse_args()

    setup_logging(args.log)

    home_dir = os.path.expanduser("~")

    if args.package:
        logging.info(f"Обработка пакета: {args.package}")
        process_package(args.package, home_dir)
    elif args.file:
        try:
            with open(args.file, "r") as f:
                packages = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            logging.error(f"Файл {args.file} не найден.")
            return

        for package_name in packages:
            logging.info(f"Обработка пакета: {package_name}")
            process_package(package_name, home_dir)

if __name__ == "__main__":
    main()
