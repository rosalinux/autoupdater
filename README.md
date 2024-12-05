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
Clone the repository:
   ```
   sudo dnf in -y git nvchecker rpmdevtools abf-c-c
   git clone https://github.com/rosalinux/autoupdater.git
   cd updater

   ```

## Usage

Check single package
    ```
   python updater.py --package libexif
   ```

## .nvchecker.toml examples

```
[neovim]
source = "github"
github = "neovim/neovim"
prefix = "v"
use_max_tag = true

[tree-sitter]
source = "git"
git = "https://github.com/tree-sitter/tree-sitter.git"
prefix = "v"

[hyprland]
source = "github"
github = "hyprwm/Hyprland"
prefix = "v"
use_max_tag = true

[systemd]
source = "git"
git = "https://github.com/systemd/systemd.git"
prefix = "v"
exclude_regex = ".*rc.*"

[zlib]
source = "git"
git = "https://github.com/madler/zlib.git"
prefix = "v"

[folder-color-switcher]
source = "regex"
url = "http://packages.linuxmint.com/pool/main/f/folder-color-switcher/"
regex = "([0-9\\.\\-]+).tar.*"

[libedit]
source = "regex"
url = "https://thrysoee.dk/editline/"
regex = "libedit-([0-9\\.\\-]+).tar.gz"
from_pattern = "\\-"
to_pattern = "_"
```
