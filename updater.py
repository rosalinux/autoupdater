import os
import requests
import rpm
import argparse
import tempfile
import json
import subprocess
from helpers.helper import update_version_in_spec_file, run_spectool_in_directory, mock_commit


def log_message(log_file, message):
    """
    Logs a message to the specified file, if provided.

    Args:
        log_file (str): Path to the log file.
        message (str): The message to log.

    If log_file is None, this function does nothing.
    """
    if log_file:
        with open(log_file, "a") as file:
            file.write(message + "\n")


def compare_versions(repo_version, upstream_version):
    """
    Compares two versions using rpmdev-vercmp and prints whether an update is needed.
    Args:
        repo_version (str): The current version of the package.
        upstream_version (str): The new version to compare with.

    Returns:
        bool: True if an update is needed, False otherwise.
    """
    try:
        # Run rpmdev-vercmp to compare versions
        result = subprocess.run(
            ["/usr/bin/rpmdev-vercmp", repo_version, upstream_version],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Check the exit code to determine which version is newer
        if result.returncode == 12:
            print(f"Update available: {repo_version} -> {upstream_version}")
            return True
        elif result.returncode == 11:
            print(f"No update needed: {repo_version} is up-to-date with {upstream_version}")
            return False
        elif result.returncode == 0:
            print(f"Versions are the same: {repo_version} == {upstream_version}")
            return False
        else:
            print(f"Error comparing versions {repo_version} and {upstream_version}: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running rpmdev-vercmp: {e}")
        return False


def check_update(package_name, branch="rosa2023.1", base_url="https://abf.io/import"):
    """
    Checks if there is an update available for the given package using nvchecker.

    Args:
        package_name (str): The name of the package to check for updates.
        branch (str): The branch to look for the .nvchecker.toml file.
        base_url (str): Base URL where the .nvchecker.toml file is hosted.

    Returns:
        str: The new version if an update is available, otherwise None.
    """
    nvchecker_url = f"{base_url}/{package_name}/raw/{branch}/.nvchecker.toml"
    tmp_dir = tempfile.gettempdir()
    tmp_nvchecker_path = os.path.join(tmp_dir, ".nvchecker.toml")

    # Check if .nvchecker.toml is accessible
    print(f"Checking if .nvchecker.toml exists at: {nvchecker_url}")
    response = requests.head(nvchecker_url)
    if response.status_code != 200:
        print(f".nvchecker.toml not found for package {package_name}. Skipping update check.")
        return None

    # Download .nvchecker.toml
    print(f"Downloading .nvchecker.toml to: {tmp_nvchecker_path}")
    response = requests.get(nvchecker_url, stream=True)
    if response.status_code == 200:
        with open(tmp_nvchecker_path, "wb") as file:
            file.write(response.content)
        print(f".nvchecker.toml downloaded successfully.")
    else:
        raise Exception(f"Failed to download .nvchecker.toml for package '{package_name}'.")

    # Run nvchecker
    print(f"Running nvchecker for package: {package_name}")
    try:
        result = subprocess.run(
            ["nvchecker", "-c", tmp_nvchecker_path, "--logger", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        # Parse the JSON lines in the output
        for line in result.stdout.splitlines():
            try:
                log_entry = json.loads(line)
                # Check if the log entry corresponds to the specified package and has a "version" key
                if "version" in log_entry:
                    print(f"Found [{package_name}] upstream version: [{log_entry['version']}]")
                    return log_entry["version"]
            except json.JSONDecodeError:
                # Skip lines that are not valid JSON
                continue

        print(f"No update found for package: {package_name}")
        return None

    except subprocess.CalledProcessError as e:
        print(f"Error running nvchecker: {e.stderr}")
        raise

# Example usage:
# Assuming the .nvchecker.toml file exists in the remote repository
# check_update_for_package("qemu", "rosa2023.1")



def fetch_spec_file(package_name, branch="rosa2023.1", base_url="https://abf.io/import"):
    """
    Downloads the spec file for the specified package to a temporary directory.
    """
    # Form the URL for the spec file
    spec_url = f"{base_url}/{package_name}/raw/{branch}/{package_name}.spec"
    tmp_dir = tempfile.gettempdir()
    output_file = os.path.join(tmp_dir, f"{package_name}.spec")

    print(f"Downloading spec file: {spec_url}")
    response = requests.get(spec_url, stream=True)
    if response.status_code == 200:
        with open(output_file, "wb") as file:
            file.write(response.content)
        print(f"Spec file {output_file} downloaded successfully.")
        return output_file
    else:
        raise Exception(f"Failed to download spec file for package '{package_name}'. HTTP status code: {response.status_code}")


def repo_version(spec_file):
    """
    Extracts the Name and Version from the spec file using RPM API.
    """
    print(f"Extracting Name and Version from file: {spec_file}")
    try:
        ts = rpm.TransactionSet()
        # Load the spec file
        ts.parseSpec(spec_file)
        # Expand macros to extract values
        name = rpm.expandMacro("%{name}")
        version = rpm.expandMacro("%{version}")
        print(f"Extracted values from {spec_file}:\n  name: [{name}]\n  version: [{version}]")
        return name, version
    except Exception as e:
        print(f"Error while extracting data from spec file {spec_file}: {e}")
        raise


def handle_update(package_name, branch="rosa2023.1", base_url="https://abf.io/import", log_file=None):
    """
    Handles the package update process:
    1. Clones the project repository into $HOME/<package_name>.
    2. Checks for upstream updates.
    3. Updates the spec file with the new version.
    4. Runs `spectool -g` to download the sources.

    Args:
        package_name (str): The name of the package to update.
        branch (str): The branch to look for spec files and update info.
        base_url (str): The base URL for spec and update info.

    Raises:
        Exception: If any step in the update process fails.
    """
    home_dir = os.path.expanduser("~")
    project_dir = os.path.join(home_dir, package_name)
    project_url = f"git@abf.io:import/{package_name}.git"

    try:
        # Check if the directory already exists
        if os.path.exists(project_dir):
            print(f"Directory already exists: {project_dir}. Pulling latest changes...")
            subprocess.run(
                ["git", "-C", project_dir, "pull"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            # Clone the repository
            print(f"Cloning repository: {project_url} (branch: {branch})")
            subprocess.run(
                ["git", "clone", "-b", branch, project_url, project_dir],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"Repository cloned to {project_dir}")

        # Find the spec file
        spec_file = os.path.join(project_dir, f"{package_name}.spec")
        if not os.path.isfile(spec_file):
            raise FileNotFoundError(f"Spec file not found in cloned repository: {spec_file}")

        # Extract the current repo version
        name, current_version = repo_version(spec_file)

        # Check for upstream updates
        upstream_version = check_update(package_name, branch, base_url)
        if not upstream_version:
            log_message(log_file, f"{package_name} no update available from [{current_version}]")
            return

        # Compare versions
        if compare_versions(current_version, upstream_version):
            print(f"Updating package {package_name} to version {upstream_version}...")

            # Update the version in the spec file
            update_version_in_spec_file(spec_file, upstream_version)

            # Run spectool in the project directory
            run_spectool_in_directory(project_dir)

            # Commit changes
            mock_commit(project_dir, upstream_version)

            # Log success if log_file is provided
            log_message(log_file, f"{package_name} upgraded [{current_version}] to [{upstream_version}]")
        else:
            log_message(log_file, f"{package_name} is already up-to-date.")
    except Exception as e:
        # Log failure if log_file is provided
        if log_file:
            log_message(log_file, f"{package_name} failed to update from [{current_version}] to [{upstream_version}]: {e}")
        print(f"Error handling update for package '{package_name}': {e}")

def handle_file(file_path, branch="rosa2023.1", base_url="https://abf.io/import", log_file=None):
    """
    Reads package names from a file and handles updates for each package.
    """
    try:
        with open(file_path, "r") as file:
            package_names = [line.strip() for line in file if line.strip()]
        for package_name in package_names:
            handle_update(package_name, branch, base_url, log_file)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Script to update package spec files and sources.")
    parser.add_argument("--package", nargs="+", help="List of packages to update.")
    parser.add_argument("--file", help="File with a list of package names to update.")
    parser.add_argument("--branch", default="rosa2023.1", help="Git branch to look for spec files.")
    parser.add_argument("--log", help="Path to a log file.")

    args = parser.parse_args()
    branch = args.branch
    log_file = args.log

    if args.package:
        for package_name in args.package:
            handle_update(package_name, branch, log_file=log_file)
    elif args.file:
        handle_file(args.file, branch, log_file=log_file)
    else:
        print("Error: You must specify either --package or --file.")

if __name__ == "__main__":
    main()
