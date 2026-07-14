"""Revoke every operator session and API token after local access loss.

Run only on the trusted host with the production environment configured. The
command never prints credentials, hashes, connection strings, or audit details.
"""

from __future__ import annotations

from getpass import getpass
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.db.production_session import create_production_engine
from app.services.security import AccessConfiguration, AccessService, ProductionAccessStore


def main() -> int:
    engine = create_production_engine()
    try:
        service = AccessService(
            ProductionAccessStore(engine),
            AccessConfiguration(bootstrap_credential="", allowed_origins=frozenset()),
        )
        password = getpass("New operator password: ")
        confirmation = getpass("Confirm new operator password: ")
        if password != confirmation:
            print("Password confirmation does not match")
            return 2
        sessions, tokens = service.recover_operator_password(
            password,
            request_id="local-operator-recovery",
        )
        print(f"Revoked operator access: sessions={sessions}, api_tokens={tokens}")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
