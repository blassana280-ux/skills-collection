"""Point d'entrée du mode service : ``python3 -m omni.sandbox --max-ticks 1``."""

from .runtime import main

if __name__ == "__main__":
    raise SystemExit(main())
