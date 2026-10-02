import json
import re
from unittest.mock import patch

from odoo.exceptions import AccessDenied
from odoo.tests.common import HttpCase, TransactionCase, tagged

from odoo.addons.auth_google.models import google

CLIENT = "123-test.apps.googleusercontent.com"


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def tokeninfo(**over):
    claims = {"aud": CLIENT, "iss": "https://accounts.google.com",
              "email_verified": "true", "email": "Ada@Example.com"}
    claims.update(over)
    return patch.object(google, "urlopen", return_value=FakeResponse(claims))


@tagged("post_install", "-at_install")
class TestAuthGoogle(TransactionCase):

    def setUp(self):
        super().setUp()
        self.startPatcher(patch.dict("os.environ", {"GOOGLE_CLIENT_ID": CLIENT}))
        self.Users = self.env["res.users"]

    def test_a_valid_token_vouches_for_its_lowercased_email(self):
        with tokeninfo():
            self.assertEqual(google.verify_id_token("t"), "ada@example.com")

    def test_a_token_minted_for_another_app_is_refused(self):
        with tokeninfo(aud="someone-else"):
            self.assertIsNone(google.verify_id_token("t"))

    def test_an_unverified_email_is_refused(self):
        with tokeninfo(email_verified="false"):
            self.assertIsNone(google.verify_id_token("t"))

    def test_without_a_client_id_nothing_is_accepted(self):
        with patch.dict("os.environ", {"GOOGLE_CLIENT_ID": ""}), tokeninfo():
            self.assertIsNone(google.verify_id_token("t"))

    def test_an_existing_user_signs_in_by_login_or_email(self):
        user = self.Users.create({"name": "Ada", "login": "ada@example.com"})
        self.assertEqual(self.Users._google_signin_user("ada@example.com"), user)

    def test_sign_up_closed_means_no_new_account(self):
        self.env["ir.config_parameter"].sudo().set_param("auth_signup.invitation_scope", "b2b")
        self.assertFalse(self.Users._google_signin_user("new@example.com"))

    def test_sign_up_open_creates_a_portal_user(self):
        self.env["ir.config_parameter"].sudo().set_param("auth_signup.invitation_scope", "b2c")

        user = self.Users._google_signin_user("new@example.com")

        self.assertEqual(user.login, "new@example.com")
        self.assertTrue(user._is_portal())

    def test_the_credential_must_match_the_user_it_signs_in(self):
        user = self.Users.create({"name": "Ada", "login": "ada@example.com"})
        other = self.Users.create({"name": "Bob", "login": "bob@example.com"})
        with tokeninfo():
            user.with_user(user)._check_credentials({"type": "google_id_token", "token": "t"}, {})
            with self.assertRaises(AccessDenied):
                other.with_user(other)._check_credentials({"type": "google_id_token", "token": "t"}, {})

    def test_the_client_id_comes_from_the_deployment(self):
        self.assertEqual(self.Users._google_client_id(), CLIENT)
        with patch.dict("os.environ", {"GOOGLE_CLIENT_ID": ""}):
            self.assertEqual(self.Users._google_client_id(), "")


@tagged("post_install", "-at_install")
class TestAuthGoogleRoutes(HttpCase):

    def setUp(self):
        super().setUp()
        self.startPatcher(patch.dict("os.environ", {"GOOGLE_CLIENT_ID": CLIENT}))
        self.user = self.env["res.users"].create({"name": "Ada", "login": "ada@example.com"})

    def _csrf(self):
        page = self.url_open("/web/login").text
        return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    def _signin(self, csrf):
        return self.url_open("/auth_google/signin", data=json.dumps({"credential": "t", "csrf_token": csrf}),
                             headers={"Content-Type": "application/json"})

    def test_the_login_page_offers_google_only_with_a_client_id(self):
        self.assertIn('id="o_auth_google"', self.url_open("/web/login").text)
        with patch.dict("os.environ", {"GOOGLE_CLIENT_ID": ""}):
            self.assertNotIn('id="o_auth_google"', self.url_open("/web/login").text)

    def test_a_google_sign_in_opens_a_session_as_that_user(self):
        with tokeninfo():
            response = self._signin(self._csrf())

        self.assertEqual(response.json(), {"ok": True})
        self.assertEqual(self.url_open("/web/session/get_session_info", data="{}",
                                       headers={"Content-Type": "application/json"}).json()["result"]["uid"],
                         self.user.id)

    def test_without_the_page_csrf_token_nothing_signs_in(self):
        with tokeninfo():
            self.assertEqual(self._signin("forged").status_code, 400)
