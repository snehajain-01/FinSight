// Login page is now served by the same Flask app that hosts the API,
// so requests can just use relative paths.
const BACKEND_URL = "";


// =========================================
// SHOW LOGIN
// =========================================

function showLogin() {

    document.getElementById("loginSection").style.display = "block";
    document.getElementById("registerSection").style.display = "none";

    // Update tabs
    document.getElementById("loginTab").classList.add("active");
    document.getElementById("registerTab").classList.remove("active");
}


// =========================================
// SHOW REGISTER
// =========================================

function showRegister() {

    document.getElementById("loginSection").style.display = "none";
    document.getElementById("registerSection").style.display = "block";

    // Update tabs
    document.getElementById("loginTab").classList.remove("active");
    document.getElementById("registerTab").classList.add("active");
}


// =========================================
// REGISTER
// =========================================

document
    .getElementById("registerForm")
    .addEventListener("submit", async function (event) {

        event.preventDefault();

        const name =
            document.getElementById("registerName").value.trim();

        const email =
            document.getElementById("registerEmail").value.trim();

        const password =
            document.getElementById("registerPassword").value;


        try {

            const response = await fetch(
                `${BACKEND_URL}/api/register`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        name: name,
                        email: email,
                        password: password
                    })
                }
            );


            // Read response ONLY ONCE
            const data = await response.json();


            document.getElementById("registerMessage").textContent =
                data.message || "Registration completed.";


            if (response.ok) {

                // Clear form
                document.getElementById("registerForm").reset();

                // Move to Login after 1 second
                setTimeout(() => {
                    showLogin();
                }, 1000);
            }

        } catch (error) {

            console.error("Registration error:", error);

            document.getElementById("registerMessage").textContent =
                "Unable to connect to the server.";
        }

    });


// =========================================
// LOGIN
// =========================================

document
    .getElementById("loginForm")
    .addEventListener("submit", async function (event) {

        event.preventDefault();


        const email =
            document.getElementById("loginEmail").value.trim();

        const password =
            document.getElementById("loginPassword").value;


        try {

            const response = await fetch(
                `${BACKEND_URL}/api/login`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        email: email,
                        password: password
                    })
                }
            );


            // IMPORTANT:
            // Read the response only ONCE
            const data = await response.json();


            document.getElementById("loginMessage").textContent =
                data.message || "Login completed.";


            // =====================================
            // LOGIN SUCCESSFUL
            // =====================================

            if (response.ok) {

                console.log("LOGIN SUCCESS");
                console.log("Server response:", data);

                // The server has already set a signed session cookie
                // identifying this user - the Dashboard reads it via
                // /api/me, so there's nothing to store client-side.

                // Open Dashboard
                window.location.href =
                    "/dashboard.html";
            }

        } catch (error) {

            console.error("Login error:", error);

            document.getElementById("loginMessage").textContent =
                "Unable to connect to the server.";
        }

    });