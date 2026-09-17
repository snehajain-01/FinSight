// Login page is now served by the same Flask app that hosts the API,
// so requests can just use relative paths.
const BACKEND_URL = "";


// =========================================
// TOGGLE PASSWORD VISIBILITY
// =========================================

function togglePassword(inputId, button) {

    const input = document.getElementById(inputId);
    const isHidden = input.type === "password";

    input.type = isHidden ? "text" : "password";
    button.textContent = isHidden ? "🙈" : "👁";
    button.setAttribute(
        "aria-label",
        isHidden ? "Hide password" : "Show password"
    );
}


// =========================================
// SHOW LOGIN
// =========================================

function showLogin() {

    document.getElementById("loginSection").style.display = "block";
    document.getElementById("registerSection").style.display = "none";
    document.getElementById("forgotSection").style.display = "none";

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
    document.getElementById("forgotSection").style.display = "none";

    // Update tabs
    document.getElementById("loginTab").classList.remove("active");
    document.getElementById("registerTab").classList.add("active");
}


// =========================================
// SHOW FORGOT PASSWORD
// =========================================

function showForgot() {

    document.getElementById("loginSection").style.display = "none";
    document.getElementById("registerSection").style.display = "none";
    document.getElementById("forgotSection").style.display = "block";

    // Neither tab represents this view
    document.getElementById("loginTab").classList.remove("active");
    document.getElementById("registerTab").classList.remove("active");

    // Always start back at step 1 (request the code)
    document.getElementById("forgotRequestForm").style.display = "flex";
    document.getElementById("forgotResetForm").style.display = "none";
    document.getElementById("forgotSubheading").textContent =
        "Enter your email to receive a verification code";
    document.getElementById("forgotMessage").textContent = "";
    document.getElementById("forgotRequestForm").reset();
    document.getElementById("forgotResetForm").reset();
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


// =========================================
// FORGOT PASSWORD - STEP 1: REQUEST OTP
// =========================================

async function requestForgotOtp() {

    const email =
        document.getElementById("forgotEmail").value.trim();

    const forgotMessage = document.getElementById("forgotMessage");

    try {

        const response = await fetch(
            `${BACKEND_URL}/api/forgot-password`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({ email })
            }
        );

        const data = await response.json();

        forgotMessage.textContent =
            data.message || "If that email is registered, a code has been sent.";

        if (response.ok) {

            // Move to step 2 regardless of whether the email exists,
            // so we don't reveal which emails are registered.
            document.getElementById("forgotRequestForm").style.display = "none";
            document.getElementById("forgotResetForm").style.display = "flex";
            document.getElementById("forgotSubheading").textContent =
                `Enter the code sent to ${email}`;
        }

    } catch (error) {

        console.error("Forgot password error:", error);

        forgotMessage.textContent = "Unable to connect to the server.";
    }
}


document
    .getElementById("forgotRequestForm")
    .addEventListener("submit", function (event) {

        event.preventDefault();
        requestForgotOtp();
    });


function resendForgotOtp() {
    requestForgotOtp();
}


// =========================================
// FORGOT PASSWORD - STEP 2: VERIFY OTP + RESET
// =========================================

document
    .getElementById("forgotResetForm")
    .addEventListener("submit", async function (event) {

        event.preventDefault();

        const email =
            document.getElementById("forgotEmail").value.trim();

        const otp =
            document.getElementById("forgotOtp").value.trim();

        const newPassword =
            document.getElementById("forgotNewPassword").value;

        const confirmPassword =
            document.getElementById("forgotConfirmPassword").value;

        const forgotMessage = document.getElementById("forgotMessage");

        if (newPassword !== confirmPassword) {

            forgotMessage.textContent = "Passwords do not match.";
            return;
        }

        try {

            const response = await fetch(
                `${BACKEND_URL}/api/reset-password`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({ email, otp, newPassword })
                }
            );

            const data = await response.json();

            forgotMessage.textContent =
                data.message || "Something went wrong.";

            if (response.ok) {

                setTimeout(() => {
                    showLogin();
                }, 1200);
            }

        } catch (error) {

            console.error("Reset password error:", error);

            forgotMessage.textContent = "Unable to connect to the server.";
        }

    });