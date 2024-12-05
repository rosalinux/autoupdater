# RPM Package Auto-Updater

A script to automate the process of updating RPM package spec files and their sources.

## Features
- Automatically detects and updates package versions using `.nvchecker.toml`.
- Fetches and updates spec files with the latest version.
- Compares current and upstream versions using `rpmdev-vercmp`.
- Optionally logs update results.

## Requirements
- Python 3.x
- RPM development tools (e.g., `rpmdevtools`)
- `nvchecker` for checking upstream versions
- git for repository management

## Installation
1. Clone the repository:
   ```
   sudo dnf in -y git nvchecker rpmdevtools abf-c-c
   git clone https://github.com/rosalinux/autoupdater.git
   cd updater

   ```

## Usage

2. Check single package
    ```
   python updater.py --package libexif
   ```
