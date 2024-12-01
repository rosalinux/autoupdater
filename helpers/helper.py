import re
import os
import subprocess


def mock_commit(project_dir, version):
    """
    Runs `abf mock -v` in the project directory, and if successful:
    1. Deletes `abf.yml` if it exists.
    2. Commits the changes to the git repository with a message.
    3. Pushes the changes to the remote repository.
    4. Runs `abf build` to trigger the build.

    Args:
        project_dir (str): Path to the project directory.
        version (str): The new version to include in the commit message.

    Raises:
        Exception: If any step fails.
    """
    try:
        # Step 1: Run `abf mock -v`
        print(f"Running `abf mock -v` in directory: {project_dir}")
        result = subprocess.run(
            ["abf", "mock", "-v"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print(f"`abf mock -v` completed successfully.\n{result.stdout}")

        # Step 2: Remove `abf.yml` if it exists
        abf_yml_path = os.path.join(project_dir, ".abf.yml")
        if os.path.exists(abf_yml_path):
            print(f"Removing {abf_yml_path}")
            os.remove(abf_yml_path)

        # Step 3: upload new sources
        print(f"Committing changes with version {version}")
        subprocess.run(
            ["abf", "put"],
            cwd=project_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        commit_message = f"autoupdate version to {version}"
        subprocess.run(
            ["git", "commit", "-am", commit_message],
            cwd=project_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"Changes committed with message: {commit_message}")

        # Step 4: Git push
        print(f"Pushing changes to remote repository")
        subprocess.run(
            ["git", "push"],
            cwd=project_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Step 5: Run `abf build`
        print(f"Running `abf build` in directory: {project_dir}")
        result = subprocess.run(
            ["abf", "build"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print(f"`abf build` completed successfully.\n{result.stdout}")

    except subprocess.CalledProcessError as e:
        print(f"Error during ABF process: {e.stderr}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise



def update_version_in_spec_file(spec_file_path, new_version):
    """
    Updates the version in the spec file to the specified new version.

    Args:
        spec_file_path (str): Path to the spec file.
        new_version (str): The new version to set.

    Raises:
        Exception: If the spec file cannot be read or updated.
    """
    try:
        # Read the contents of the spec file
        with open(spec_file_path, "r") as file:
            spec_contents = file.read()

        # Replace the "Version:" line with the new version
        updated_spec_contents = re.sub(
            r"^(Version:\s*)(.+)$",
            lambda match: f"{match.group(1)}{new_version}",
            spec_contents,
            flags=re.MULTILINE
        )

        if spec_contents == updated_spec_contents:
            print(f"The version is already set to {new_version} in {spec_file_path}. No changes made.")
            return

        # Write the updated contents back to the spec file
        with open(spec_file_path, "w") as file:
            file.write(updated_spec_contents)

        print(f"Version updated to {new_version} in {spec_file_path}")

    except Exception as e:
        print(f"Error updating the version in spec file {spec_file_path}: {e}")
        raise


def run_spectool_in_directory(project_directory):
    """
    Runs `spectool -g` on the spec file located in the specified directory to download sources
    directly into the project directory.

    Args:
        project_directory (str): Path to the project directory containing the spec file.

    Raises:
        Exception: If the command fails or the spec file is not found.
    """
    try:
        # Check if the directory exists
        if not os.path.isdir(project_directory):
            raise FileNotFoundError(f"Directory not found: {project_directory}")

        # Form the spec file path
        spec_file = os.path.join(project_directory, f"{os.path.basename(project_directory)}.spec")
        if not os.path.isfile(spec_file):
            raise FileNotFoundError(f"Spec file not found: {spec_file}")

        # Execute `spectool -g` in the project directory
        print(f"Running `spectool -g {spec_file}` in directory: {project_directory}")
        result = subprocess.run(
            ["spectool", "-g", spec_file],
            cwd=project_directory,  # Change working directory to project_directory
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        # Output the command result
        print(result.stdout)
        print("Sources downloaded successfully into the project directory.")

    except subprocess.CalledProcessError as e:
        print(f"Error running spectool: {e.stderr}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise


#spec_file = "/home/omv/dos2unix/dos2unix.spec"
#new_version = "7.3.0"
#update_version_in_spec_file(spec_file, new_version)

#project_directory = "/home/omv/dos2unix"
#run_spectool_in_directory(project_directory)
