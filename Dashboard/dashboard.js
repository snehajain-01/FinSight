// =========================================
// CHANGE DASHBOARD SECTION
// =========================================

function showSection(sectionId, clickedButton) {

    // Hide all sections
    const sections =
        document.querySelectorAll(".content-section");

    sections.forEach(section => {
        section.classList.remove("active-section");
    });


    // Show selected section
    const selectedSection =
        document.getElementById(sectionId);

    if (selectedSection) {
        selectedSection.classList.add("active-section");
    }


    // Remove active from all navigation buttons
    const navItems =
        document.querySelectorAll(".nav-item");

    navItems.forEach(item => {
        item.classList.remove("active");
    });


    // Add active to clicked button
    if (clickedButton) {
        clickedButton.classList.add("active");
    }


    // Change page title
    const titles = {

        dashboard: "Dashboard",

        upload: "Upload Document",

        transactions: "Transactions",

        insights: "Insights",

        recommendations: "Recommendations"

    };


    document.getElementById("pageTitle").textContent =
        titles[sectionId] || "Dashboard";
}



// =========================================
// SHOW SECTION FROM OTHER BUTTON
// =========================================

function showSectionByName(sectionId) {

    const navButtons =
        document.querySelectorAll(".nav-item");

    let selectedButton = null;


    navButtons.forEach(button => {

        const onclickValue =
            button.getAttribute("onclick");

        if (
            onclickValue &&
            onclickValue.includes(`'${sectionId}'`)
        ) {

            selectedButton = button;

        }

    });


    showSection(
        sectionId,
        selectedButton
    );

}



// =========================================
// LOGOUT
// =========================================

function logout() {

   
    window.location.href = "../Login/frontend/index.html";


}