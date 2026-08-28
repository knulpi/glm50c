"""PyInstaller launcher: a plain script entry point so the analysis walks
the glm50c package from src/ (passed via --paths) without relying on the
installed console-script shim."""

from glm50c.cli import main

if __name__ == "__main__":
    main()
