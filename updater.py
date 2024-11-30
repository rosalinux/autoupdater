import os
import requests
import rpm
import argparse
import tempfile

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

def get_nvs(spec_file):
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
        print(f"Extracted values from {spec_file}:\n  Name: {name}\n  Version: {version}")
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
            name, version = get_nvs(spec_file)
            print(f"Package: {name}, Version: {version}")
        except Exception as e:
            print(f"Error processing package '{package_name}': {e}")

if __name__ == "__main__":
    main()
