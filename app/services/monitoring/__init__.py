"""Unified error monitoring: catalog, intake and incidents."""



def is_intake_request(scope, path):
    """The three dedicated transports, without treating legacy events as diagnostics."""
    if scope.get("method") != "POST":
        return False
    if path in ("/api/v3/android/diagnostics", "/api/v3/pwa/diagnostics"):
        return True
    if path != "/api/miniapp/event":
        return False
    # Match Starlette's Headers.get: only the first header value applies.
    value = next((value for name, value in scope.get("headers", ()) if name == b"x-hsk-diagnostic"), None)
    return value == b"diag.v1"
