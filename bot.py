#!/usr/bin/env python
# Wrapper to launch the modular main.py entry point
import asyncio
import main

if __name__ == "__main__":
    try:
        asyncio.run(main.main())
    except (KeyboardInterrupt, SystemExit):
        pass
