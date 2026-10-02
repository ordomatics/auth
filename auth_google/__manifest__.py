{
    "name": "Sign in with Google",
    "summary": "A Google button on the login page, for projects that set a Google client ID",
    "version": "18.0.1.0.0",
    "category": "Hidden/Tools",
    "license": "LGPL-3",
    "author": "Ordomatics",
    "depends": ["auth_signup"],
    "data": ["views/login_templates.xml"],
    "assets": {
        "web.assets_frontend": ["auth_google/static/src/js/login_google.js"],
    },
    "installable": True,
}
