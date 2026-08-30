"""
Thin compatibility shim so `python3 tessera_mcp_server.py` works exactly as
documented, without needing `pip install -e .` first (as long as this Tessera/
directory is on PYTHONPATH, which it is when running from here).

Prefer the packaged entry point instead: after `pip install -e ".[mcp]"`,
just run `tessera-mcp` from anywhere.
"""

from tessera.mcp_server import main

if __name__ == "__main__":
    main()
