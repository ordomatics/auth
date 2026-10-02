// A plain script: the login page is not part of any Owl app. A no-op on every
// page without the button.
(function () {
    "use strict";

    function field(name) {
        const el = document.querySelector(`input[name="${name}"]`);
        return el ? el.value : "";
    }

    function showError(button, message) {
        const p = document.createElement("p");
        p.className = "alert alert-danger";
        p.setAttribute("role", "alert");
        p.textContent = message;
        button.parentNode.insertBefore(p, button);
    }

    function signIn(button, response) {
        fetch("/auth_google/signin", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({credential: response.credential, csrf_token: field("csrf_token")}),
        })
            .then((r) => r.json())
            .then((data) => {
                if (data.ok) {
                    window.location.href = field("redirect") || "/web";
                } else {
                    showError(button, data.error);
                }
            })
            .catch(() => showError(button, "Google sign-in failed."));
    }

    function render(attempt = 0) {
        const button = document.getElementById("o_auth_google");
        if (!button) {
            return;
        }
        const gis = window.google && window.google.accounts && window.google.accounts.id;
        if (!gis) {
            // The Google script loads async and may not have run yet.
            if (attempt < 25) {
                setTimeout(() => render(attempt + 1), 200);
            }
            return;
        }
        gis.initialize({client_id: button.dataset.clientId, callback: (r) => signIn(button, r)});
        gis.renderButton(button, {type: "standard", theme: "outline", size: "large", width: button.clientWidth || 280});
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => render());
    } else {
        render();
    }
})();
