import secrets

from odoo import api, models
from odoo.exceptions import AccessDenied

from .google import google_client_id, verify_id_token


class ResUsers(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, credential, env):
        if credential.get("type") != "google_id_token":
            return super()._check_credentials(credential, env)
        # Verified again here, whatever called authenticate(): this is the gate.
        email = verify_id_token(credential.get("token"))
        if not email or email not in {(self.login or "").lower(), (self.email or "").strip().lower()}:
            raise AccessDenied()
        return {"uid": self.env.uid, "auth_method": "google_id_token", "mfa": "default"}

    @api.model
    def _google_client_id(self):
        return google_client_id()

    @api.model
    def _google_signin_user(self, email):
        """The user this Google email signs in as, created as a portal user
        when sign-up is open (Odoo's own b2c setting), else none."""
        Users = self.sudo().with_context(active_test=False)
        user = Users.search([("login", "=ilike", email)], limit=1) or \
            Users.search([("partner_id.email", "=ilike", email)], limit=1)
        if user:
            return user if user.active else self.browse()
        if self.env["res.users"].sudo()._get_signup_invitation_scope() != "b2c":
            return self.browse()
        return Users.with_context(no_reset_password=True)._create_user_from_template({
            "login": email, "email": email, "name": email,
            # Never shown or typed: this account signs in through Google.
            "password": secrets.token_urlsafe(32),
        })
