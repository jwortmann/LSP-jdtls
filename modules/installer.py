import os
import sublime
import shutil
import zipfile
import tarfile
import tempfile
from urllib.request import urlopen

from LSP.plugin.core.views import get_storage_path
from LSP.plugin.core.typing import Callable, Union

from .constants import STORAGE_DIR
from .constants import INSTALL_DIR
from .constants import SETTINGS_FILENAME
from .constants import JDTLS_VERSION
from .constants import LOMBOK_VERSION
from .constants import JDTLS_URL
from .constants import LOMBOK_URL
from .constants import DATA_DIR
from .constants import VSCODE_PLUGINS


def _jdtls_version() -> str:
    version = sublime.load_settings(SETTINGS_FILENAME).get("version")
    return version or JDTLS_VERSION


# File Download / Extraction
############################

def download_file(url: str, file_name: str) -> None:
    with urlopen(url) as response, open(file_name, "wb") as out_file:
        shutil.copyfileobj(response, out_file)


def _extract_file(
    url: str,
    path: str,
    open_function: Union[
        Callable[[str], zipfile.ZipFile], Callable[[str], tarfile.TarFile]
    ],
):
    with tempfile.TemporaryDirectory() as download_dir:
        compressed_file = os.path.join(download_dir, "compressed_file")
        download_file(url, compressed_file)
        uncompress_dir = os.path.join(download_dir, "uncompress_dir")
        os.makedirs(uncompress_dir)
        with open_function(compressed_file) as compressed_file:
            compressed_file.extractall(uncompress_dir)
        shutil.move(uncompress_dir, path)


def extract_zip(url: str, path: str):
    """
    Extracts the zip at `url` to `path`.
    The zip is extracted into `path` if it already exists.
    """
    _extract_file(url, path, lambda x: zipfile.ZipFile(x, "r"))


def extract_tar(url: str, path: str):
    """
    Extracts the tar at `url` to `path`.
    The tar is extracted into `path` if it already exists.
    """
    _extract_file(url, path, lambda x: tarfile.open(x, "r:gz"))


# Path definitions
##################

def storage_subpath() -> str:
    return os.path.join(get_storage_path(), STORAGE_DIR)


def install_path() -> str:
    return os.path.join(storage_subpath(), INSTALL_DIR)


def jdtls_path() -> str:
    return os.path.join(
        install_path(), "jdtls-{version}".format(version=_jdtls_version())
    )


def jdtls_data_path() -> str:
    return os.path.join(storage_subpath(), DATA_DIR)


def vscode_plugin_path(plugin: dict) -> str:
    return os.path.join(
        install_path(),
        "{name}-{version}".format(
            name=plugin["name"],
            version=plugin["version"]
        ),
    )


def lombok_jar_path() -> str:
    return os.path.join(
        install_path(),
        "lombok-{version}.jar".format(version=LOMBOK_VERSION),
    )


# Install / Update
###################

def needs_update_or_installation() -> bool:
    result = not os.path.isdir(jdtls_path())
    result |= not os.path.isfile(lombok_jar_path())
    for plugin in VSCODE_PLUGINS:
        result |= not os.path.isdir(vscode_plugin_path(plugin))
    return result


def install_or_update() -> None:
    version = _jdtls_version()
    basedir = storage_subpath()
    if os.path.isdir(basedir):
        shutil.rmtree(basedir)
    os.makedirs(basedir)

    # fmt: off
    sublime.status_message("LSP-jdtls: downloading jdtls...")
    extract_tar(JDTLS_URL.format(version=version), jdtls_path())
    sublime.status_message("LSP-jdtls: downloading lombok...")
    download_file(LOMBOK_URL.format(version=LOMBOK_VERSION), lombok_jar_path())
    for plugin in VSCODE_PLUGINS:
        sublime.status_message("LSP-jdtls: {name}...".format(name=plugin["name"]))
        extract_zip(plugin["url"].format(version=plugin["version"]), vscode_plugin_path(plugin))
    # fmt: on
