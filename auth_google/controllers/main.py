from odoo import _, http
from odoo.exceptions import AccessDenied
from odoo.http import request

from ..models.google import verify_id_token


class GoogleSignin(http.Controller):

    @http.route("/auth_google/signin", type="http", auth="public", methods=["POST"], csrf=False)
    def signin(self, **kwargs):
        data = request.get_json_data() or {}
        # Login CSRF: a token in a JSON body is one Odoo's own check never sees.
        if not request.validate_csrf(data.get("csrf_token")):
            return request.make_json_response({"error": _("Your session expired. Reload the page.")}, status=400)
        email = verify_id_token(data.get("credential"))
        user = request.env["res.users"]._google_signin_user(email) if email else None
        if not user:
            return request.make_json_response(
                {"error": _("No account here for that Google address.")}, status=403)
        try:
            request.session.authenticate(request.db, {
                "login": user.login, "type": "google_id_token", "token": data.get("credential")})
        except AccessDenied:
            return request.make_json_response({"error": _("Google sign-in failed.")}, status=401)
        return request.make_json_response({"ok": True})
