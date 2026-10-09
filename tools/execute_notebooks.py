"""Виконання notebook із збереженням реальних output cells."""

import argparse
import asyncio
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

from common.utilities import ROOT


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    parser = argparse.ArgumentParser()
    parser.add_argument("labs", nargs="+", choices=["lab01", "lab02", "lab03", "lab04"])
    args = parser.parse_args()
    for lab in args.labs:
        path = ROOT / lab / f"{lab}.ipynb"
        notebook = nbformat.read(path, as_version=4)
        kernel = KernelManager(kernel_name="python3")
        kernel.kernel_spec.argv[0] = sys.executable
        try:
            NotebookClient(
                notebook,
                km=kernel,
                timeout=180,
                resources={"metadata": {"path": str(ROOT)}},
            ).execute()
        finally:
            if kernel.has_kernel:
                kernel.shutdown_kernel(now=True)
        nbformat.write(notebook, path)
        print(f"Виконано та збережено {path.name}")


if __name__ == "__main__":
    main()
