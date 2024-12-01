import os
import requests
import rpm
import argparse
import tempfile
import json
import subprocess

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
                if log_entry.get("name") == package_name and "version" in log_entry:
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


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Script to extract package versions from spec files.")
    parser.add_argument("--package", required=True, nargs="+", help="List of packages to extract versions for.")
    parser.add_argument("--branch", default="rosa2023.1", help="Git branch to look for spec files.")
    args = parser.parse_args()

    package_names = args.package
    branch = args.branch

    for package_name in package_names:
        try:
            # Download the spec file
            spec_file = fetch_spec_file(package_name, branch)
            # Extract Name and Version
            name, version = repo_version(spec_file)
            print(f"package: [{name}], version: [{version}]")
            upstream_version = check_update(package_name)
            if upstream_version:
                compare_versions(version, upstream_version)
        except Exception as e:
            print(f"Error processing package '{package_name}': {e}")

if __name__ == "__main__":
    main()
