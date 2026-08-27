const BACKEND_URL = "http://localhost:4000";


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
                `${BACKEND_URL}/register`,
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
                `${BACKEND_URL}/login`,
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

                // Test whether login itself is successful
                

                // Open Dashboard
                window.location.href =
                    "http://localhost:3000/Dashboard/dashboard.html";
            }

        } catch (error) {

            console.error("Login error:", error);

            document.getElementById("loginMessage").textContent =
                "Unable to connect to the server.";
        }

    });