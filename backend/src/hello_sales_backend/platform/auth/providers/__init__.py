"""Auth provider adapters."""

from hello_sales_backend.platform.auth.providers.noop import NoopAuthProvider
from hello_sales_backend.platform.auth.providers.workos import WorkOSAuthProvider

__all__ = [
    "NoopAuthProvider",
    "WorkOSAuthProvider",
]

