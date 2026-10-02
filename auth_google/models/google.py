import json
import os
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Google's own signature- and expiry-checked endpoint: no JWT library needed
# to verify one kind of token.
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def google_client_id():
    """The project's own OAuth client: its deployment sets it. Google accepts a
    sign-in only from origins listed on that client, so it cannot be shared."""
    return (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()


def verify_id_token(id_token):
    """The verified email a Google sign-in credential vouches for, or None.

    The audience check stops a token Google really signed, but for some other
    app, from being accepted here.
    """
    client_id = google_client_id()
    if not id_token or not client_id:
        return None
    request = Request("%s?%s" % (TOKENINFO_URL, urlencode({"id_token": id_token})),
                      headers={"User-Agent": "auth_google/1.0"})
    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
    except (URLError, OSError, ValueError):
        return None
    if data.get("aud") != client_id:
        return None
    if data.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        return None
    if str(data.get("email_verified")).lower() != "true":
        return None
    return (data.get("email") or "").strip().lower() or None
