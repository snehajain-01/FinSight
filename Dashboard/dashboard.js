// Dashboard is now served by the same Flask app that hosts the API,
// so requests can just use relative paths.
const API_BASE = "";

const DEFAULT_CATEGORY = "Others";

let transactions = [];
let categories = [];

// Transaction id of the row currently showing its category dropdown
// (a needs-review row is always in this state until resolved).
let editingCategoryId = null;


async function loadCategories() {

    try {

        const response = await fetch(`${API_BASE}/api/categories`);

        if (!response.ok) {
            return;
        }

        const data = await response.json();
        categories = data.categories || [];

    } catch (error) {

        console.error("Unable to load categories:", error);
    }
}


// =========================================
// CURRENT USER
// =========================================

// The server is the source of truth for who's logged in (a signed
// session cookie, set on /api/login) - this is just a local cache of
// what /api/me returned, used for display only.
let currentUser = null;


async function requireLogin() {

    try {

        const response = await fetch(`${API_BASE}/api/me`);

        if (!response.ok) {
            window.location.href = "/";
            return false;
        }

        const data = await response.json();
        currentUser = data.user;

        return true;

    } catch (error) {

        window.location.href = "/";
        return false;
    }
}


function renderUserInfo() {

    const initial =
        (currentUser.name || "U").trim().charAt(0).toUpperCase();

    document.getElementById("userAvatar").textContent = initial;
    document.getElementById("profileCircle").textContent = initial;

    document.getElementById("userName").textContent =
        currentUser.name || "User";

    document.getElementById("userEmail").textContent =
        currentUser.email || "FinSight Account";
}


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

        confirmCategories: "Confirm Categories",

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

async function logout() {

    try {
        await fetch(`${API_BASE}/api/logout`, { method: "POST" });
    } catch (error) {
        console.error("Logout error:", error);
    }

    window.location.href = "/";
}



// =========================================
// UPLOAD DOCUMENT
// =========================================

document
    .getElementById("fileInput")
    .addEventListener("change", async function (event) {

        const file = event.target.files[0];

        if (!file) {
            return;
        }

        await uploadFile(file);

        // Allow re-selecting the same file later
        event.target.value = "";
    });


async function uploadFile(file) {

    const uploadBox = document.getElementById("uploadBox");
    const statusText = document.getElementById("uploadStatusText");
    const chooseButton = document.getElementById("chooseDocumentButton");

    uploadBox.classList.add("is-uploading");
    chooseButton.disabled = true;
    statusText.classList.remove(
        "upload-status-error",
        "upload-status-success"
    );
    statusText.textContent = `Uploading ${file.name}...`;


    try {

        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(
            `${API_BASE}/api/upload`,
            {
                method: "POST",
                body: formData
            }
        );

        if (response.status === 401) {
            window.location.href = "/";
            return;
        }

        const data = await response.json();

        if (!response.ok || !data.success) {

            statusText.classList.add("upload-status-error");
            statusText.textContent =
                data.message || "Upload failed. Please try again.";

            return;
        }

        const newTransactions = data.transactions || [];

        if (!newTransactions.length) {

            statusText.classList.add("upload-status-error");
            statusText.textContent =
                `Couldn't find any transaction details in ` +
                `${file.name}. Try a clearer screenshot or a ` +
                `different file.`;

            return;
        }

        statusText.classList.add("upload-status-success");
        statusText.textContent =
            `${file.name} processed successfully.`;

        // Merge newly extracted transactions into the working set
        transactions = transactions.concat(newTransactions);

        renderTransactions();

        // Jump to the Transactions tab to show the result
        showSectionByName("transactions");

    } catch (error) {

        console.error("Upload error:", error);

        statusText.classList.add("upload-status-error");
        statusText.textContent =
            "Unable to connect to the server.";

    } finally {

        uploadBox.classList.remove("is-uploading");
        chooseButton.disabled = false;
    }
}



// =========================================
// LOAD EXISTING TRANSACTIONS
// =========================================

async function loadTransactions() {

    try {

        const response = await fetch(
            `${API_BASE}/api/transactions`
        );

        if (response.status === 401) {
            window.location.href = "/";
            return;
        }

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        transactions = data.transactions || [];

        renderTransactions();

    } catch (error) {

        console.error("Unable to load transactions:", error);
    }
}



// =========================================
// TRANSACTIONS TABLE SORT
// A display-only ordering - the underlying `transactions` array is
// never reordered, so Insights, Confirm Categories, and everything
// else keep working from the data exactly as it came from the API.
// =========================================

let transactionsSortOrder = "newest";
let transactionsSortListenerAttached = false;

function initTransactionsSortListener() {

    if (transactionsSortListenerAttached) {
        return;
    }

    transactionsSortListenerAttached = true;

    const select = document.getElementById("transactionsSortOrder");
    select.value = transactionsSortOrder;

    select.addEventListener("change", () => {
        transactionsSortOrder = select.value;
        renderTransactions();
    });
}

function getSortedTransactionsForDisplay() {

    const withParsedDates = transactions.map(transaction => ({
        transaction,
        date: parseTransactionDate(transaction.date)
    }));

    const direction = transactionsSortOrder === "oldest" ? 1 : -1;

    withParsedDates.sort((a, b) => {

        // A transaction with no parseable date sinks to the bottom
        // either way, rather than jumping to the top of "newest".
        if (!a.date && !b.date) return 0;
        if (!a.date) return 1;
        if (!b.date) return -1;

        return (a.date - b.date) * direction;
    });

    return withParsedDates.map(entry => entry.transaction);
}


// =========================================
// RENDER TRANSACTIONS + OVERVIEW
// =========================================

function renderTransactions() {

    const emptyState = document.getElementById("transactionsEmpty");
    const tableWrap = document.getElementById("transactionsTableWrap");
    const tableBody = document.getElementById("transactionsTableBody");

    if (!transactions.length) {

        emptyState.style.display = "flex";
        tableWrap.style.display = "none";

        updateOverview();
        updateReviewQueue();
        renderInsights();
        renderRecommendations();

        return;
    }

    emptyState.style.display = "none";
    tableWrap.style.display = "block";

    tableBody.innerHTML = "";

    initTransactionsSortListener();

    getSortedTransactionsForDisplay().forEach(transaction => {

        const row = document.createElement("tr");

        const isDebit =
            (transaction.type || "").toUpperCase() === "DEBIT";

        const leadingCells = [
            transaction.date || "",
            transaction.time || "",
            transaction.merchant || ""
        ];

        leadingCells.forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });

        row.appendChild(buildCategoryCell(transaction));

        const typeCell = document.createElement("td");
        typeCell.textContent = transaction.type || "";
        row.appendChild(typeCell);

        const amountCell = document.createElement("td");
        amountCell.className = isDebit ? "amount-debit" : "amount-credit";
        amountCell.textContent =
            `${isDebit ? "-" : "+"}₹${Number(transaction.amount || 0).toFixed(2)}`;
        row.appendChild(amountCell);

        tableBody.appendChild(row);
    });

    updateOverview();
    updateReviewQueue();
    renderInsights();
    renderRecommendations();
}


// =========================================
// CATEGORY CELL (badge + inline dropdown editor)
// =========================================

// A confidence of 1.0 always means either the user confirmed it
// themselves or it was auto-applied from a merchant they'd already
// confirmed before - "predicted with 100% confidence" would overstate
// what actually happened, so it gets its own label.
function formatConfidence(transaction) {

    const confidence = transaction.confidence;

    if (typeof confidence !== "number") {
        return "";
    }

    if (confidence >= 1) {
        return "Confirmed by you";
    }

    return `${Math.round(confidence * 100)}% confidence`;
}


function buildCategoryCell(transaction) {

    const cell = document.createElement("td");
    cell.className = "category-cell";

    const isEditing =
        transaction.needs_review || editingCategoryId === transaction.id;

    if (!isEditing) {

        const badge = document.createElement("span");
        badge.className = "category-badge";
        badge.textContent = transaction.category || DEFAULT_CATEGORY;
        cell.appendChild(badge);

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "category-edit-btn";
        editButton.title = "Change category";
        editButton.textContent = "✎";
        editButton.addEventListener("click", () => {
            editingCategoryId = transaction.id;
            renderTransactions();
        });
        cell.appendChild(editButton);

        const confidenceLabel = document.createElement("div");
        confidenceLabel.className = "category-confidence";
        confidenceLabel.textContent = formatConfidence(transaction);
        cell.appendChild(confidenceLabel);

        return cell;
    }

    const wrapper = document.createElement("div");
    wrapper.className = "category-edit-wrap";

    if (transaction.needs_review) {

        const flag = document.createElement("span");
        flag.className = "category-review-flag";
        flag.textContent = "Confirm category";

        const confidenceHint = formatConfidence(transaction);

        if (confidenceHint) {
            flag.textContent += ` (suggested: ${confidenceHint})`;
        }

        wrapper.appendChild(flag);
    }

    const select = document.createElement("select");
    select.className = "category-select";

    categories.forEach(category => {

        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;

        if (category === (transaction.category || DEFAULT_CATEGORY)) {
            option.selected = true;
        }

        select.appendChild(option);
    });

    select.addEventListener("change", () => {
        updateTransactionCategory(transaction, select.value);
    });

    select.addEventListener("blur", () => {

        if (
            !transaction.needs_review &&
            editingCategoryId === transaction.id
        ) {
            editingCategoryId = null;
            renderTransactions();
        }
    });

    wrapper.appendChild(select);
    cell.appendChild(wrapper);

    return cell;
}


// Whitespace-insensitive on purpose (mirrors merchant_identity_key()
// on the backend) - different extractors format the same real-world
// merchant differently ("ABDULRAHEEM" from a bank-statement PDF vs.
// "ABDUL RAHEEM" from a screenshot), and without stripping spaces
// entirely those would be treated as two unrelated merchants here too
// (both for bulk-resolving a just-confirmed category across already
// loaded transactions, and for grouping recurring-merchant spend in
// Recommendations).
function normalizeMerchantKey(merchant) {
    return (merchant || "").replace(/\s+/g, "").toLowerCase();
}


// Returns true on success, false otherwise, so callers (the inline
// table editor and the Confirm Categories queue) can react.
async function updateTransactionCategory(transaction, newCategory) {

    try {

        const response = await fetch(
            `${API_BASE}/api/transactions/${encodeURIComponent(transaction.id)}/category`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ category: newCategory })
            }
        );

        if (response.status === 401) {
            window.location.href = "/";
            return false;
        }

        const data = await response.json();

        if (!response.ok || !data.success) {
            console.error("Failed to update category:", data.message);
            return false;
        }

        const isPerson = !!data.is_person;
        const merchantKey = normalizeMerchantKey(transaction.merchant);

        // Once you've answered for a merchant (or person), it's
        // remembered - resolve every other instance already loaded,
        // not just this one, so you're never asked again for it.
        transactions.forEach(candidate => {

            const isSameTransaction = candidate.id === transaction.id;

            const isSameMerchant =
                normalizeMerchantKey(candidate.merchant) === merchantKey;

            if (isSameTransaction || isSameMerchant) {
                candidate.category = newCategory;
                candidate.needs_review = false;
                candidate.is_person = isPerson;
            }
        });

        editingCategoryId = null;

        renderTransactions();

        return true;

    } catch (error) {

        console.error("Category update error:", error);
        return false;
    }
}


// =========================================
// CONFIRM CATEGORIES QUEUE
// =========================================

function updateReviewQueue() {

    const queue = transactions.filter(
        transaction => transaction.needs_review
    );

    const badge = document.getElementById("reviewBadge");

    if (queue.length) {
        badge.textContent = queue.length;
        badge.hidden = false;
    } else {
        badge.hidden = true;
    }

    renderConfirmQueue(queue);
}


function renderConfirmQueue(queue) {

    const container = document.getElementById("confirmQueueArea");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!queue.length) {

        const empty = document.createElement("div");
        empty.className = "empty-table";

        const icon = document.createElement("div");
        icon.className = "table-icon";
        icon.textContent = "✓";
        empty.appendChild(icon);

        const heading = document.createElement("h3");
        heading.textContent = "All caught up";
        empty.appendChild(heading);

        const message = document.createElement("p");
        message.textContent =
            "Every transaction has a category. Upload a new " +
            "statement to review more.";
        empty.appendChild(message);

        container.appendChild(empty);
        return;
    }

    const current = queue[0];
    const isDebit = (current.type || "").toUpperCase() === "DEBIT";

    const card = document.createElement("div");
    card.className = "review-card";

    const progress = document.createElement("div");
    progress.className = "review-progress";
    progress.textContent =
        `${queue.length} transaction${queue.length === 1 ? "" : "s"} ` +
        "need a category";
    card.appendChild(progress);

    const merchantEl = document.createElement("h3");
    merchantEl.className = "review-merchant";
    merchantEl.textContent = current.merchant || "Unknown merchant";
    card.appendChild(merchantEl);

    const meta = document.createElement("p");
    meta.className = "review-meta";
    meta.textContent =
        `${current.date || ""} ${current.time || ""} · ` +
        `${isDebit ? "-" : "+"}₹${Number(current.amount || 0).toFixed(2)}`;
    card.appendChild(meta);

    const confidenceHint = formatConfidence(current);

    if (confidenceHint) {

        const confidenceEl = document.createElement("p");
        confidenceEl.className = "review-confidence";
        confidenceEl.textContent =
            `Suggested: ${current.category || DEFAULT_CATEGORY} ` +
            `(${confidenceHint})`;
        card.appendChild(confidenceEl);
    }

    const hint = document.createElement("p");
    hint.className = "review-hint";
    hint.textContent =
        `Once you pick a category, we'll remember it for ` +
        `"${current.merchant || "this"}" and never ask again.`;
    card.appendChild(hint);

    const select = document.createElement("select");
    select.className = "category-select review-select";

    categories.forEach(category => {

        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;

        if (category === (current.category || DEFAULT_CATEGORY)) {
            option.selected = true;
        }

        select.appendChild(option);
    });

    card.appendChild(select);

    const actions = document.createElement("div");
    actions.className = "review-actions";

    const confirmButton = document.createElement("button");
    confirmButton.type = "button";
    confirmButton.textContent = "Confirm & Continue";

    confirmButton.addEventListener("click", async () => {

        confirmButton.disabled = true;

        const success = await updateTransactionCategory(
            current,
            select.value
        );

        if (success) {

            const remaining =
                transactions.filter(t => t.needs_review).length;

            if (remaining === 0) {
                showSectionByName("transactions");
            }

        } else {

            confirmButton.disabled = false;
        }
    });

    actions.appendChild(confirmButton);

    const skipButton = document.createElement("button");
    skipButton.type = "button";
    skipButton.className = "review-skip-btn";
    skipButton.textContent = "View Transactions Instead";
    skipButton.addEventListener("click", () => {
        showSectionByName("transactions");
    });
    actions.appendChild(skipButton);

    card.appendChild(actions);

    container.appendChild(card);
}


function updateOverview() {

    const totalSpending = transactions
        .filter(
            transaction =>
                (transaction.type || "").toUpperCase() === "DEBIT"
        )
        .reduce(
            (sum, transaction) => sum + Number(transaction.amount || 0),
            0
        );

    const totalSpendingEl = document.getElementById("statTotalSpending");
    const totalSpendingHintEl =
        document.getElementById("statTotalSpendingHint");

    const transactionCountEl =
        document.getElementById("statTransactionCount");
    const transactionCountHintEl =
        document.getElementById("statTransactionCountHint");

    if (!transactions.length) {

        totalSpendingEl.textContent = "—";
        totalSpendingHintEl.textContent = "No data available";

        transactionCountEl.textContent = "—";
        transactionCountHintEl.textContent = "No transactions yet";

        return;
    }

    totalSpendingEl.textContent = `₹${totalSpending.toFixed(2)}`;
    totalSpendingHintEl.textContent = "Across all uploaded statements";

    transactionCountEl.textContent = transactions.length;
    transactionCountHintEl.textContent = "Extracted from your documents";
}



// =========================================
// INSIGHTS
// All computed live from the real `transactions` array (populated
// from MongoDB via /api/transactions) - nothing here is hardcoded.
// =========================================

// Validated categorical palette (see the dataviz skill) checked
// against FinSight's dark navy chart surface - 8 fixed hues for the
// 8 real categories, plus a neutral slate for the "Others" catch-all
// (never generate a 9th hue - a fixed catch-all color is the correct
// treatment for a category that isn't really an identity of its own).
const CATEGORY_COLORS = {
    "Food": "#3987e5",
    "Travel": "#d95926",
    "Shopping": "#199e70",
    "Bills and Utilities": "#c98500",
    "Healthcare": "#d55181",
    "Entertainment": "#008300",
    "Savings": "#9085e9",
    "Education": "#e66767",
    "Others": "#55718f"
};

function colorForCategory(category) {
    return CATEGORY_COLORS[category] || CATEGORY_COLORS["Others"];
}


// =========================================
// DATE PARSING
// Transaction dates come out of the PDF/screenshot extractors as
// human-readable strings in a few different shapes ("Aug 26, 2026",
// "17 Sept 2026", "01Feb,2026") - none of them stored as a machine
// date. This parses what we already have rather than changing what
// the extractors or the table display, so nothing existing breaks.
// =========================================

const MONTH_INDEX = {
    jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
    jul: 6, aug: 7, sep: 8, sept: 8, oct: 9, nov: 10, dec: 11
};

function monthIndexFromName(name) {

    const key = name.toLowerCase().replace(/\./g, "");

    if (MONTH_INDEX[key] !== undefined) {
        return MONTH_INDEX[key];
    }

    return MONTH_INDEX[key.slice(0, 3)];
}

function parseTransactionDate(dateStr) {

    if (!dateStr) {
        return null;
    }

    const text = dateStr.trim();

    // "Aug 26, 2026" / "Aug 26 2026"
    let match = text.match(/^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$/);

    if (match) {

        const month = monthIndexFromName(match[1]);

        if (month !== undefined) {
            return new Date(Number(match[3]), month, Number(match[2]));
        }
    }

    // "17 Sept 2026" / "01Feb,2026" (day and month may or may not be
    // space-separated, comma is optional)
    match = text.match(/^(\d{1,2})\s*([A-Za-z]{3,9})\.?\s*,?\s*(\d{4})$/);

    if (match) {

        const month = monthIndexFromName(match[2]);

        if (month !== undefined) {
            return new Date(Number(match[3]), month, Number(match[1]));
        }
    }

    // Last resort - let the browser take a shot at it (covers ISO
    // dates and anything else reasonably standard).
    const fallback = new Date(text);

    return isNaN(fallback.getTime()) ? null : fallback;
}

function monthKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(key) {

    const [year, month] = key.split("-").map(Number);
    const date = new Date(year, month - 1, 1);

    return date.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}

function dayKey(date) {

    return `${date.getFullYear()}-` +
        `${String(date.getMonth() + 1).padStart(2, "0")}-` +
        `${String(date.getDate()).padStart(2, "0")}`;
}

function dayLabel(date) {
    return date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}


// =========================================
// FORMATTING
// =========================================

function formatCurrency(value) {
    return `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function formatCompactCurrency(value) {

    if (value >= 100000) {
        return `₹${(value / 100000).toFixed(1)}L`;
    }

    if (value >= 1000) {
        return `₹${(value / 1000).toFixed(1)}K`;
    }

    return `₹${Math.round(value)}`;
}


// =========================================
// FILTERS
// =========================================

let insightsFilterListenersAttached = false;

function initInsightsFilterListeners() {

    if (insightsFilterListenersAttached) {
        return;
    }

    insightsFilterListenersAttached = true;

    [
        "insightsMonthFilter",
        "insightsCategoryFilter",
        "insightsFromFilter",
        "insightsToFilter"
    ].forEach(id => {
        document.getElementById(id).addEventListener("change", renderInsights);
    });

    document.getElementById("insightsResetFilters")
        .addEventListener("click", () => {

            document.getElementById("insightsMonthFilter").value = "all";
            document.getElementById("insightsCategoryFilter").value = "all";
            document.getElementById("insightsFromFilter").value = "";
            document.getElementById("insightsToFilter").value = "";

            renderInsights();
        });
}

function populateInsightsFilterOptions() {

    const monthSelect = document.getElementById("insightsMonthFilter");
    const categorySelect = document.getElementById("insightsCategoryFilter");

    // Months are derived from the transactions themselves - real data,
    // never a hardcoded list - so the filter only ever offers months
    // that actually have transactions in them.
    const monthKeys = new Set();

    transactions.forEach(transaction => {

        const date = parseTransactionDate(transaction.date);

        if (date) {
            monthKeys.add(monthKey(date));
        }
    });

    const sortedMonths = Array.from(monthKeys).sort().reverse();

    const previousMonth = monthSelect.value;
    monthSelect.innerHTML = "";

    const allMonthsOption = document.createElement("option");
    allMonthsOption.value = "all";
    allMonthsOption.textContent = "All months";
    monthSelect.appendChild(allMonthsOption);

    sortedMonths.forEach(key => {

        const option = document.createElement("option");
        option.value = key;
        option.textContent = monthLabel(key);
        monthSelect.appendChild(option);
    });

    monthSelect.value =
        (previousMonth === "all" || sortedMonths.includes(previousMonth))
            ? previousMonth
            : "all";

    const previousCategory = categorySelect.value;
    categorySelect.innerHTML = "";

    const allCategoriesOption = document.createElement("option");
    allCategoriesOption.value = "all";
    allCategoriesOption.textContent = "All categories";
    categorySelect.appendChild(allCategoriesOption);

    categories.forEach(category => {

        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        categorySelect.appendChild(option);
    });

    categorySelect.value =
        (previousCategory === "all" || categories.includes(previousCategory))
            ? previousCategory
            : "all";
}

function getFilteredInsightsTransactions() {

    const monthValue = document.getElementById("insightsMonthFilter").value;
    const categoryValue = document.getElementById("insightsCategoryFilter").value;
    const fromValue = document.getElementById("insightsFromFilter").value;
    const toValue = document.getElementById("insightsToFilter").value;

    const fromDate = fromValue ? new Date(fromValue) : null;
    const toDate = toValue ? new Date(toValue) : null;

    if (toDate) {
        toDate.setHours(23, 59, 59, 999);
    }

    return transactions.filter(transaction => {

        const date = parseTransactionDate(transaction.date);

        if (monthValue !== "all" && (!date || monthKey(date) !== monthValue)) {
            return false;
        }

        const category = transaction.category || DEFAULT_CATEGORY;

        if (categoryValue !== "all" && category !== categoryValue) {
            return false;
        }

        if (fromDate && (!date || date < fromDate)) {
            return false;
        }

        if (toDate && (!date || date > toDate)) {
            return false;
        }

        return true;
    });
}


// =========================================
// TREND SERIES
// A trend line grouped only by month collapses to a nearly-straight
// 2-point line for any account with just a month or two of history
// (the common case for a new app) - not a real "trend". Grouping by
// day instead when the data covers a short enough span gives a far
// more realistic, granular line: every day in range is represented
// (including zero-spend days, so gaps read as dips rather than being
// skipped over), and it falls back to monthly grouping once the range
// gets long enough that daily points would be too dense to read.
// =========================================

const TREND_DAILY_SPAN_LIMIT_DAYS = 60;
const MS_PER_DAY = 1000 * 60 * 60 * 24;

function buildTrendSeries(debits) {

    let minDate = null;
    let maxDate = null;

    const dailyTotals = {};

    debits.forEach(transaction => {

        const date = parseTransactionDate(transaction.date);

        if (!date) {
            return;
        }

        const key = dayKey(date);
        dailyTotals[key] = (dailyTotals[key] || 0) + Number(transaction.amount || 0);

        if (!minDate || date < minDate) {
            minDate = date;
        }

        if (!maxDate || date > maxDate) {
            maxDate = date;
        }
    });

    if (!minDate || !maxDate) {
        return [];
    }

    const spanDays = Math.round((maxDate - minDate) / MS_PER_DAY) + 1;

    if (spanDays <= TREND_DAILY_SPAN_LIMIT_DAYS) {

        const series = [];
        const cursor = new Date(minDate);

        while (cursor <= maxDate) {

            const key = dayKey(cursor);

            series.push({
                key,
                label: dayLabel(cursor),
                total: dailyTotals[key] || 0
            });

            cursor.setDate(cursor.getDate() + 1);
        }

        return series;
    }

    const monthlyTotals = {};

    debits.forEach(transaction => {

        const date = parseTransactionDate(transaction.date);

        if (!date) {
            return;
        }

        const key = monthKey(date);
        monthlyTotals[key] = (monthlyTotals[key] || 0) + Number(transaction.amount || 0);
    });

    return Object.entries(monthlyTotals)
        .map(([key, total]) => ({ key, label: monthLabel(key), total }))
        .sort((a, b) => a.key.localeCompare(b.key));
}


// =========================================
// STATS
// =========================================

function computeInsightsStats(filtered) {

    const debits = filtered.filter(
        transaction => (transaction.type || "").toUpperCase() === "DEBIT"
    );

    const totalSpending = debits.reduce(
        (sum, transaction) => sum + Number(transaction.amount || 0),
        0
    );

    const transactionCount = debits.length;
    const averageSpending = transactionCount ? totalSpending / transactionCount : 0;

    const categoryTotals = {};

    debits.forEach(transaction => {

        const category = transaction.category || DEFAULT_CATEGORY;

        categoryTotals[category] =
            (categoryTotals[category] || 0) + Number(transaction.amount || 0);
    });

    const categoryBreakdown = Object.entries(categoryTotals)
        .map(([category, total]) => ({ category, total }))
        .sort((a, b) => b.total - a.total);

    const trend = buildTrendSeries(debits);

    const topExpenses = debits
        .slice()
        .sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0))
        .slice(0, 8);

    return {
        totalSpending,
        transactionCount,
        averageSpending,
        categoryBreakdown,
        trend,
        topExpenses
    };
}


// =========================================
// SHARED CHART HELPERS
// =========================================

let chartTooltipEl = null;

function getChartTooltip() {

    if (!chartTooltipEl) {
        chartTooltipEl = document.createElement("div");
        chartTooltipEl.className = "chart-tooltip";
        chartTooltipEl.hidden = true;
        document.body.appendChild(chartTooltipEl);
    }

    return chartTooltipEl;
}

// Tooltip content is set via textContent (never innerHTML) - category
// and merchant names ultimately come from uploaded documents, so they
// are treated as untrusted text, not markup.
function attachChartTooltip(element, getLines) {

    const show = event => {

        const tooltip = getChartTooltip();
        tooltip.textContent = "";

        getLines().forEach((line, index) => {

            if (index > 0) {
                tooltip.appendChild(document.createElement("br"));
            }

            tooltip.appendChild(document.createTextNode(line));
        });

        tooltip.hidden = false;

        const x = event.clientX ?? element.getBoundingClientRect().left;
        const y = event.clientY ?? element.getBoundingClientRect().top;

        tooltip.style.left = `${x + 16}px`;
        tooltip.style.top = `${y + 16}px`;

        element.classList.add("chart-mark-hover");
    };

    const hide = () => {
        getChartTooltip().hidden = true;
        element.classList.remove("chart-mark-hover");
    };

    element.addEventListener("pointerenter", show);
    element.addEventListener("pointermove", show);
    element.addEventListener("pointerleave", hide);
    element.addEventListener("focus", show);
    element.addEventListener("blur", hide);
}

function renderChartEmptyState(container, message) {

    const empty = document.createElement("div");
    empty.className = "chart-empty";
    empty.textContent = message;
    container.appendChild(empty);
}

function buildCategoryLegend(data, total) {

    const legend = document.createElement("div");
    legend.className = "chart-legend";

    data.forEach(entry => {

        const row = document.createElement("div");
        row.className = "chart-legend-row";

        const swatch = document.createElement("span");
        swatch.className = "chart-legend-swatch";
        swatch.style.background = colorForCategory(entry.category);
        row.appendChild(swatch);

        const name = document.createElement("span");
        name.className = "chart-legend-name";
        name.textContent = entry.category;
        row.appendChild(name);

        const value = document.createElement("span");
        value.className = "chart-legend-value";
        const percent = total ? Math.round((entry.total / total) * 100) : 0;
        value.textContent = `${formatCurrency(entry.total)} · ${percent}%`;
        row.appendChild(value);

        legend.appendChild(row);
    });

    return legend;
}


// =========================================
// DONUT CHART - "Where Did My Money Go?" (by share)
// =========================================

function renderDonutChart(stats) {

    const container = document.getElementById("insightsDonutChart");
    container.innerHTML = "";

    const data = stats.categoryBreakdown;
    const total = stats.totalSpending;

    if (!data.length || !total) {
        renderChartEmptyState(container, "No spending to show yet.");
        return;
    }

    const size = 220;
    const radius = 80;
    const strokeWidth = 26;
    const circumference = 2 * Math.PI * radius;
    const gap = 3;

    const svgNs = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNs, "svg");
    svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
    svg.setAttribute("class", "donut-svg");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Spending by category, donut chart");

    const group = document.createElementNS(svgNs, "g");
    group.setAttribute("transform", `rotate(-90 ${size / 2} ${size / 2})`);
    svg.appendChild(group);

    const track = document.createElementNS(svgNs, "circle");
    track.setAttribute("cx", size / 2);
    track.setAttribute("cy", size / 2);
    track.setAttribute("r", radius);
    track.setAttribute("fill", "none");
    track.setAttribute("stroke", "rgba(255,255,255,0.06)");
    track.setAttribute("stroke-width", strokeWidth);
    group.appendChild(track);

    let offset = 0;

    data.forEach(entry => {

        const fraction = entry.total / total;
        const length = Math.max(fraction * circumference - gap, 0);

        const segment = document.createElementNS(svgNs, "circle");
        segment.setAttribute("cx", size / 2);
        segment.setAttribute("cy", size / 2);
        segment.setAttribute("r", radius);
        segment.setAttribute("fill", "none");
        segment.setAttribute("stroke", colorForCategory(entry.category));
        segment.setAttribute("stroke-width", strokeWidth);
        segment.setAttribute("stroke-linecap", "round");
        segment.setAttribute(
            "stroke-dasharray",
            `${length} ${circumference - length}`
        );
        segment.setAttribute("stroke-dashoffset", -offset);
        segment.setAttribute("class", "donut-segment");
        segment.setAttribute("tabindex", "0");

        attachChartTooltip(segment, () => [
            entry.category,
            `${formatCurrency(entry.total)} · ${Math.round(fraction * 100)}%`
        ]);

        group.appendChild(segment);

        offset += fraction * circumference;
    });

    const centerLabel = document.createElement("div");
    centerLabel.className = "donut-center-label";

    const centerValue = document.createElement("strong");
    centerValue.textContent = formatCompactCurrency(total);
    centerLabel.appendChild(centerValue);

    const centerCaption = document.createElement("span");
    centerCaption.textContent = "Total spent";
    centerLabel.appendChild(centerCaption);

    const wrap = document.createElement("div");
    wrap.className = "donut-wrap";
    wrap.appendChild(svg);
    wrap.appendChild(centerLabel);

    container.appendChild(wrap);
    container.appendChild(buildCategoryLegend(data, total));
}


// =========================================
// BAR CHART - "Where Did My Money Go?" (by amount)
// =========================================

function renderBarChart(stats) {

    const container = document.getElementById("insightsBarChart");
    container.innerHTML = "";

    const data = stats.categoryBreakdown;

    if (!data.length) {
        renderChartEmptyState(container, "No spending to show yet.");
        return;
    }

    const maxValue = Math.max(...data.map(entry => entry.total));

    const list = document.createElement("div");
    list.className = "bar-chart-list";

    data.forEach(entry => {

        const row = document.createElement("div");
        row.className = "bar-chart-row";
        row.setAttribute("tabindex", "0");

        const label = document.createElement("span");
        label.className = "bar-chart-label";
        label.textContent = entry.category;
        row.appendChild(label);

        const track = document.createElement("div");
        track.className = "bar-chart-track";

        const fill = document.createElement("div");
        fill.className = "bar-chart-fill";
        const widthPercent = maxValue ? (entry.total / maxValue) * 100 : 0;
        fill.style.width = `${Math.max(widthPercent, 3)}%`;
        fill.style.background = colorForCategory(entry.category);
        track.appendChild(fill);

        row.appendChild(track);

        const value = document.createElement("span");
        value.className = "bar-chart-value";
        value.textContent = formatCurrency(entry.total);
        row.appendChild(value);

        attachChartTooltip(row, () => [
            entry.category,
            formatCurrency(entry.total)
        ]);

        list.appendChild(row);
    });

    container.appendChild(list);
}


// =========================================
// LINE CHART - Spending Trends
// =========================================

function renderLineChart(stats) {

    const container = document.getElementById("insightsLineChart");
    container.innerHTML = "";

    const trend = stats.trend;

    if (trend.length < 2) {

        renderChartEmptyState(
            container,
            trend.length === 1
                ? "Add more transactions to see a trend."
                : "No spending to show yet."
        );

        return;
    }

    const width = 760;
    const height = 240;
    const paddingLeft = 56;
    const paddingRight = 24;
    const paddingTop = 24;
    const paddingBottom = 34;

    const maxValue = Math.max(...trend.map(point => point.total), 1);
    const plotWidth = width - paddingLeft - paddingRight;
    const plotHeight = height - paddingTop - paddingBottom;

    const points = trend.map((point, index) => ({
        ...point,
        x: paddingLeft + (index / (trend.length - 1)) * plotWidth,
        y: paddingTop + plotHeight - (point.total / maxValue) * plotHeight
    }));

    // A dense daily series would either overlap every x-axis label or
    // drown the line under dozens of full-size dots - thin both down
    // rather than let them collide. The line itself still plots every
    // point either way, so no data is lost, just de-emphasized.
    const maxXLabels = 10;
    const labelStep = Math.max(1, Math.ceil(points.length / maxXLabels));
    const isDense = points.length > 14;
    const dotRadius = isDense ? 3 : 5;

    const svgNs = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNs, "svg");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("class", "line-svg");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Spending trend over time");

    for (let step = 0; step <= 3; step += 1) {

        const y = paddingTop + (plotHeight / 3) * step;

        const gridLine = document.createElementNS(svgNs, "line");
        gridLine.setAttribute("x1", paddingLeft);
        gridLine.setAttribute("x2", width - paddingRight);
        gridLine.setAttribute("y1", y);
        gridLine.setAttribute("y2", y);
        gridLine.setAttribute("class", "line-chart-grid");
        svg.appendChild(gridLine);

        const tickValue = maxValue - (maxValue / 3) * step;

        const tick = document.createElementNS(svgNs, "text");
        tick.setAttribute("x", paddingLeft - 10);
        tick.setAttribute("y", y + 4);
        tick.setAttribute("class", "line-chart-tick");
        tick.setAttribute("text-anchor", "end");
        tick.textContent = formatCompactCurrency(tickValue);
        svg.appendChild(tick);
    }

    const baseline = paddingTop + plotHeight;

    const areaPoints = [
        `${points[0].x},${baseline}`,
        ...points.map(point => `${point.x},${point.y}`),
        `${points[points.length - 1].x},${baseline}`
    ].join(" ");

    const area = document.createElementNS(svgNs, "polygon");
    area.setAttribute("points", areaPoints);
    area.setAttribute("class", "line-chart-area");
    svg.appendChild(area);

    const line = document.createElementNS(svgNs, "polyline");
    line.setAttribute("points", points.map(point => `${point.x},${point.y}`).join(" "));
    line.setAttribute("class", "line-chart-line");
    line.setAttribute("fill", "none");
    svg.appendChild(line);

    points.forEach((point, index) => {

        const dot = document.createElementNS(svgNs, "circle");
        dot.setAttribute("cx", point.x);
        dot.setAttribute("cy", point.y);
        dot.setAttribute("r", dotRadius);
        dot.setAttribute("class", "line-chart-dot");
        dot.setAttribute("tabindex", "0");

        attachChartTooltip(dot, () => [
            point.label,
            formatCurrency(point.total)
        ]);

        svg.appendChild(dot);

        // Thin the x-axis text so a dense (e.g. daily) series doesn't
        // collide into an unreadable smear - the endpoint always gets
        // one regardless, so the series' latest date is never hidden.
        // A regular-interval label that would land within one step of
        // the endpoint is skipped instead of drawn right next to it -
        // otherwise the two overlap into unreadable, garbled text.
        const isLastPoint = index === points.length - 1;
        const isNearLastPoint = points.length - 1 - index < labelStep;

        if ((index % labelStep === 0 && !isNearLastPoint) || isLastPoint) {

            const xLabel = document.createElementNS(svgNs, "text");
            xLabel.setAttribute("x", point.x);
            xLabel.setAttribute("y", height - 10);
            xLabel.setAttribute("class", "line-chart-tick");
            xLabel.setAttribute("text-anchor", "middle");
            xLabel.textContent = point.label;
            svg.appendChild(xLabel);
        }
    });

    container.appendChild(svg);
}


// =========================================
// TOP EXPENSES
// =========================================

function renderTopExpenses(stats) {

    const container = document.getElementById("insightsTopExpenses");
    container.innerHTML = "";

    if (!stats.topExpenses.length) {
        renderChartEmptyState(container, "No expenses to show yet.");
        return;
    }

    stats.topExpenses.forEach(transaction => {

        const row = document.createElement("div");
        row.className = "top-expense-row";

        const swatch = document.createElement("span");
        swatch.className = "chart-legend-swatch";
        swatch.style.background =
            colorForCategory(transaction.category || DEFAULT_CATEGORY);
        row.appendChild(swatch);

        const info = document.createElement("div");
        info.className = "top-expense-info";

        const merchant = document.createElement("strong");
        merchant.textContent = transaction.merchant || "Unknown";
        info.appendChild(merchant);

        const meta = document.createElement("span");
        meta.textContent =
            `${transaction.category || DEFAULT_CATEGORY} · ${transaction.date || ""}`;
        info.appendChild(meta);

        row.appendChild(info);

        const amount = document.createElement("span");
        amount.className = "top-expense-amount";
        amount.textContent = formatCurrency(transaction.amount);
        row.appendChild(amount);

        container.appendChild(row);
    });
}


// =========================================
// PERSONALIZED INSIGHTS
// Rule-based, derived entirely from the computed stats/filtered data -
// no canned copy with placeholder numbers.
// =========================================

function generateInsightCards(stats, filtered) {

    const cards = [];

    if (stats.transactionCount === 0) {
        return cards;
    }

    const topCategory = stats.categoryBreakdown[0];

    if (topCategory && stats.totalSpending > 0) {

        const share = Math.round((topCategory.total / stats.totalSpending) * 100);

        cards.push({
            title: "Biggest category",
            text: `${share}% of your spending (${formatCurrency(topCategory.total)}) ` +
                  `went to ${topCategory.category}.`
        });
    }

    if (stats.trend.length >= 2) {

        const last = stats.trend[stats.trend.length - 1];
        const prev = stats.trend[stats.trend.length - 2];

        if (prev.total > 0) {

            const change = Math.round(((last.total - prev.total) / prev.total) * 100);
            const direction = change >= 0 ? "higher" : "lower";

            cards.push({
                title: "Month over month",
                text: `You spent ${Math.abs(change)}% ${direction} in ${last.label} ` +
                      `than in ${prev.label}.`
            });
        }
    }

    const biggestExpense = stats.topExpenses[0];

    if (biggestExpense && stats.averageSpending > 0) {

        const multiple = (Number(biggestExpense.amount) / stats.averageSpending).toFixed(1);

        cards.push({
            title: "Biggest single expense",
            text: `Your largest expense was ${formatCurrency(biggestExpense.amount)} to ` +
                  `${biggestExpense.merchant} - about ${multiple}x your average transaction.`
        });
    }

    const pendingCount = filtered.filter(transaction => transaction.needs_review).length;

    if (pendingCount > 0) {

        cards.push({
            title: "Needs your attention",
            text: `${pendingCount} transaction${pendingCount === 1 ? "" : "s"} in this ` +
                  `period still need${pendingCount === 1 ? "s" : ""} a category confirmed.`
        });
    }

    return cards;
}

function renderInsightCards(cards) {

    const container = document.getElementById("insightsCards");
    container.innerHTML = "";

    if (!cards.length) {
        renderChartEmptyState(container, "Not enough data yet for personalized insights.");
        return;
    }

    cards.forEach(card => {

        const cardEl = document.createElement("div");
        cardEl.className = "insight-card";

        const title = document.createElement("h4");
        title.textContent = card.title;
        cardEl.appendChild(title);

        const text = document.createElement("p");
        text.textContent = card.text;
        cardEl.appendChild(text);

        container.appendChild(cardEl);
    });
}


// =========================================
// STAT TILES
// =========================================

function renderInsightsStats(stats) {

    document.getElementById("insightsTotalSpending").textContent =
        formatCurrency(stats.totalSpending);

    document.getElementById("insightsTotalSpendingHint").textContent =
        stats.transactionCount ? "Across the selected period" : "No spending in this period";

    document.getElementById("insightsTransactionCount").textContent =
        stats.transactionCount;

    document.getElementById("insightsTransactionCountHint").textContent =
        stats.transactionCount ? "Debit transactions" : "No transactions";

    document.getElementById("insightsAverageSpending").textContent =
        formatCurrency(stats.averageSpending);

    document.getElementById("insightsAverageSpendingHint").textContent =
        stats.transactionCount ? "Per transaction" : "No data";

    const topCategory = stats.categoryBreakdown[0];

    document.getElementById("insightsTopCategory").textContent =
        topCategory ? topCategory.category : "—";

    document.getElementById("insightsTopCategoryHint").textContent =
        topCategory ? formatCurrency(topCategory.total) : "No data";
}


// =========================================
// MASTER RENDER
// =========================================

function renderInsights() {

    const emptyState = document.getElementById("insightsEmpty");
    const content = document.getElementById("insightsContent");

    if (!transactions.length) {
        emptyState.style.display = "flex";
        content.hidden = true;
        return;
    }

    emptyState.style.display = "none";
    content.hidden = false;

    initInsightsFilterListeners();
    populateInsightsFilterOptions();

    const filtered = getFilteredInsightsTransactions();
    const stats = computeInsightsStats(filtered);

    renderInsightsStats(stats);
    renderDonutChart(stats);
    renderBarChart(stats);
    renderLineChart(stats);
    renderTopExpenses(stats);
    renderInsightCards(generateInsightCards(stats, filtered));
}


// =========================================
// RECOMMENDATIONS
// Rule-based, computed from the full (unfiltered) transaction history
// every time it renders - an overall financial-health check rather
// than something scoped to whatever period Insights happens to be
// filtered to. No canned copy: every number quoted comes straight out
// of the real data.
// =========================================

// One visual identity per recommendation type - reuses the same
// icon-circle component the Dashboard's own overview cards use, so
// this stays on the existing FinSight look rather than inventing a
// new pattern.
const RECOMMENDATION_META = {
    overspend: { icon: "⚠️", color: "amber", tag: "Attention" },
    budget: { icon: "🎯", color: "blue", tag: "Budget suggestion" },
    savings: { icon: "💰", color: "green", tag: "Saving opportunity" },
    unusual: { icon: "⚠️", color: "amber", tag: "Attention" },
    recurring: { icon: "🔄", color: "purple", tag: "Recurring payments" },
    trend: { icon: "📈", color: "amber", tag: "Spending pattern" },
    review: { icon: "⚠️", color: "amber", tag: "Attention" },
    cashflow: { icon: "⚠️", color: "blue", tag: "Attention" },
    smallSpends: { icon: "💰", color: "cyan", tag: "Saving opportunity" },
    balanced: { icon: "✨", color: "violet", tag: "Good habit" }
};

function generateRecommendations(allTransactions) {

    const recommendations = [];

    const debits = allTransactions.filter(
        transaction => (transaction.type || "").toUpperCase() === "DEBIT"
    );

    if (!debits.length) {
        return recommendations;
    }

    const totalSpending = debits.reduce(
        (sum, transaction) => sum + Number(transaction.amount || 0),
        0
    );

    const categoryTotals = {};
    const monthsPresent = new Set();

    debits.forEach(transaction => {

        const category = transaction.category || DEFAULT_CATEGORY;

        categoryTotals[category] =
            (categoryTotals[category] || 0) + Number(transaction.amount || 0);

        const date = parseTransactionDate(transaction.date);

        if (date) {
            monthsPresent.add(monthKey(date));
        }
    });

    const monthCount = Math.max(monthsPresent.size, 1);

    const categoryBreakdown = Object.entries(categoryTotals)
        .map(([category, total]) => ({ category, total }))
        .sort((a, b) => b.total - a.total);


    // ---- Overspending alert: a category running hot vs its own history ----

    const globalMonthKeys = Array.from(monthsPresent).sort();
    const latestMonthKey = globalMonthKeys[globalMonthKeys.length - 1];

    if (globalMonthKeys.length >= 2 && latestMonthKey) {

        const categoryMonthlyTotals = {};

        debits.forEach(transaction => {

            const date = parseTransactionDate(transaction.date);

            if (!date) {
                return;
            }

            const category = transaction.category || DEFAULT_CATEGORY;
            const key = monthKey(date);

            if (!categoryMonthlyTotals[category]) {
                categoryMonthlyTotals[category] = {};
            }

            categoryMonthlyTotals[category][key] =
                (categoryMonthlyTotals[category][key] || 0) + Number(transaction.amount || 0);
        });

        let worstOverspend = null;

        Object.entries(categoryMonthlyTotals).forEach(([category, monthly]) => {

            const currentTotal = monthly[latestMonthKey] || 0;
            const priorKeys = Object.keys(monthly).filter(key => key !== latestMonthKey);

            if (!priorKeys.length || currentTotal <= 0) {
                return;
            }

            const priorAverage =
                priorKeys.reduce((sum, key) => sum + monthly[key], 0) / priorKeys.length;

            if (priorAverage <= 0) {
                return;
            }

            const increase = currentTotal - priorAverage;
            const pctIncrease = increase / priorAverage;

            // A meaningful jump, not noise on a category you barely spend in.
            if (pctIncrease >= 0.3 && increase >= 200) {

                if (!worstOverspend || increase > worstOverspend.increase) {
                    worstOverspend = { category, currentTotal, priorAverage, increase, pctIncrease };
                }
            }
        });

        if (worstOverspend) {

            recommendations.push({
                type: "overspend",
                title: `Overspending alert: ${worstOverspend.category}`,
                reason: `You've usually spent about ` +
                        `${formatCurrency(worstOverspend.priorAverage)} a month on ` +
                        `${worstOverspend.category}, but ${monthLabel(latestMonthKey)} is ` +
                        `already at ${formatCurrency(worstOverspend.currentTotal)}.`,
                text: `That's ${Math.round(worstOverspend.pctIncrease * 100)}% above your ` +
                      `usual pace - worth checking what's driving it before the month ends.`,
                potentialSavings: worstOverspend.increase,
                savingsLabel: "Above your usual pace"
            });
        }
    }


    // ---- Budget the dominant category ----

    const topCategory = categoryBreakdown[0];

    if (topCategory && topCategory.category !== "Savings" && totalSpending > 0) {

        const share = topCategory.total / totalSpending;

        if (share >= 0.3) {

            const monthlyAverage = topCategory.total / monthCount;
            const suggestedBudget =
                Math.max(Math.floor((monthlyAverage * 0.9) / 100) * 100, 100);

            recommendations.push({
                type: "budget",
                title: `Set a budget for ${topCategory.category}`,
                reason: `${topCategory.category} is your single largest spending ` +
                        `category, making up ${Math.round(share * 100)}% of everything ` +
                        `you've spent (${formatCurrency(topCategory.total)}).`,
                text: `Try capping it around ${formatCurrency(suggestedBudget)} a month.`,
                potentialSavings: Math.max(monthlyAverage - suggestedBudget, 0),
                savingsLabel: "Potential savings/month"
            });
        }
    }


    // ---- Start/grow savings ----

    const savingsTotal = categoryTotals["Savings"] || 0;
    const savingsShare = totalSpending ? savingsTotal / totalSpending : 0;

    if (savingsShare < 0.05) {

        const suggestedSavings =
            Math.max(Math.round((totalSpending * 0.1) / monthCount / 100) * 100, 100);

        recommendations.push({
            type: "savings",
            title: "Start building your savings",
            reason: savingsTotal > 0
                ? `Only ${Math.round(savingsShare * 100)}% of your spending has gone ` +
                  `toward Savings so far.`
                : `No Savings or investment transactions found in your history.`,
            text: `Try setting aside about ${formatCurrency(suggestedSavings)} a month, ` +
                  `even a small amount.`,
            potentialSavings: suggestedSavings,
            savingsLabel: "Suggested monthly savings"
        });
    }


    // ---- Unusual spending: a transaction well outside your normal range ----

    if (debits.length >= 5) {

        const averageTransaction = totalSpending / debits.length;

        const biggest = debits.reduce(
            (max, transaction) =>
                Number(transaction.amount || 0) > Number(max.amount || 0) ? transaction : max,
            debits[0]
        );

        const biggestAmount = Number(biggest.amount || 0);

        if (averageTransaction > 0 && biggestAmount >= averageTransaction * 3 && biggestAmount >= 500) {

            const multiple = (biggestAmount / averageTransaction).toFixed(1);

            recommendations.push({
                type: "unusual",
                title: "Unusual transaction spotted",
                reason: `${formatCurrency(biggestAmount)} to ` +
                        `${biggest.merchant || "an unknown merchant"} on ` +
                        `${biggest.date || "an unknown date"} is ${multiple}x your typical ` +
                        `transaction of ${formatCurrency(averageTransaction)}.`,
                text: `If this wasn't planned, it's worth a second look.`
            });
        }
    }


    // ---- A recurring expense worth a second look ----

    const merchantStats = {};

    debits.forEach(transaction => {

        if (transaction.is_person) {
            return;
        }

        const key = normalizeMerchantKey(transaction.merchant);

        if (!key) {
            return;
        }

        if (!merchantStats[key]) {
            merchantStats[key] = {
                name: transaction.merchant,
                count: 0,
                total: 0
            };
        }

        merchantStats[key].count += 1;
        merchantStats[key].total += Number(transaction.amount || 0);
    });

    const recurring = Object.values(merchantStats)
        .filter(entry => entry.count >= 3)
        .sort((a, b) => b.total - a.total)[0];

    if (recurring) {

        const illustrativeCut = Math.round((recurring.total * 0.2) / 10) * 10;

        recommendations.push({
            type: "recurring",
            title: "Review a recurring expense",
            reason: `You've paid ${recurring.name} ${recurring.count} times, ` +
                    `totaling ${formatCurrency(recurring.total)}.`,
            text: `If it's a subscription or a habit purchase, check whether you ` +
                  `still need all of it.`,
            potentialSavings: illustrativeCut,
            savingsLabel: "If cut by a fifth"
        });
    }


    // ---- Spending is climbing month over month ----

    if (monthsPresent.size >= 2) {

        const monthlyTotals = {};

        debits.forEach(transaction => {

            const date = parseTransactionDate(transaction.date);

            if (!date) {
                return;
            }

            const key = monthKey(date);
            monthlyTotals[key] = (monthlyTotals[key] || 0) + Number(transaction.amount || 0);
        });

        const sortedMonths = Object.entries(monthlyTotals)
            .map(([key, total]) => ({ key, total }))
            .sort((a, b) => a.key.localeCompare(b.key));

        const last = sortedMonths[sortedMonths.length - 1];
        const prev = sortedMonths[sortedMonths.length - 2];

        if (prev.total > 0) {

            const change = (last.total - prev.total) / prev.total;

            if (change >= 0.2) {

                recommendations.push({
                    type: "trend",
                    title: "Spending is climbing",
                    reason: `You spent ${formatCurrency(last.total)} in ` +
                            `${monthLabel(last.key)} versus ${formatCurrency(prev.total)} ` +
                            `in ${monthLabel(prev.key)}.`,
                    text: `That's ${Math.round(change * 100)}% more - worth checking what ` +
                          `drove the increase.`,
                    potentialSavings: last.total - prev.total,
                    savingsLabel: "Extra spent this month"
                });
            }
        }
    }


    // ---- Cash flow: spending against what's actually come in ----

    const credits = allTransactions.filter(
        transaction => (transaction.type || "").toUpperCase() === "CREDIT"
    );

    const totalReceived = credits.reduce(
        (sum, transaction) => sum + Number(transaction.amount || 0),
        0
    );

    if (totalReceived > 0) {

        const spendRatio = totalSpending / totalReceived;

        // "Received" here only means money that arrived through the
        // same UPI/wallet trail as everything else in the account -
        // not necessarily the person's whole income (salary paid
        // straight to a bank account wouldn't show up here at all).
        // A ratio far past 100% almost always means that gap, not a
        // real overspending signal, so it's capped rather than shown
        // as a nonsense figure like "857%".
        if (spendRatio >= 0.9 && spendRatio <= 2) {

            recommendations.push({
                type: "cashflow",
                title: "Spending is close to what you're receiving",
                reason: `You've spent ${formatCurrency(totalSpending)} against ` +
                        `${formatCurrency(totalReceived)} received through the same ` +
                        `transaction history.`,
                text: `That's ${Math.round(spendRatio * 100)}% - try building in more ` +
                      `of a buffer.`
            });

        } else if (spendRatio <= 0.5) {

            recommendations.push({
                type: "balanced",
                title: "Healthy cash flow",
                reason: `You've spent just ${Math.round(spendRatio * 100)}% of the ` +
                        `${formatCurrency(totalReceived)} you've received.`,
                text: `You're in good shape to save or invest more of it.`
            });
        }
    }


    // ---- Small purchases that quietly add up ----

    const smallSpends = debits.filter(
        transaction => Number(transaction.amount || 0) < 100
    );

    const smallSpendsTotal = smallSpends.reduce(
        (sum, transaction) => sum + Number(transaction.amount || 0),
        0
    );

    if (
        smallSpends.length >= 5 &&
        totalSpending > 0 &&
        smallSpendsTotal / totalSpending >= 0.03
    ) {

        const halfSmall = Math.round((smallSpendsTotal * 0.5) / 10) * 10;

        recommendations.push({
            type: "smallSpends",
            title: "Small purchases add up",
            reason: `You've made ${smallSpends.length} purchases under ₹100, ` +
                    `totaling ${formatCurrency(smallSpendsTotal)}.`,
            text: `Individually small, but worth keeping an eye on.`,
            potentialSavings: halfSmall,
            savingsLabel: "If cut in half"
        });
    }


    // ---- Pending categorizations ----

    const pendingCount = allTransactions.filter(
        transaction => transaction.needs_review
    ).length;

    if (pendingCount > 0) {

        recommendations.push({
            type: "review",
            title: "Confirm pending categories",
            reason: `${pendingCount} transaction${pendingCount === 1 ? "" : "s"} still ` +
                    `need${pendingCount === 1 ? "s" : ""} a category.`,
            text: `Confirming them sharpens every recommendation here.`
        });
    }


    // ---- Fallback: nothing concerning found ----

    if (!recommendations.length) {

        recommendations.push({
            type: "balanced",
            title: "Looking balanced",
            reason: `Your spending is spread across ${categoryBreakdown.length} ` +
                    `categories with no single one dominating.`,
            text: `Keep it up.`
        });
    }

    return recommendations;
}


function renderRecommendations() {

    const emptyState = document.getElementById("recommendationsEmpty");
    const banner = document.getElementById("recommendationsBanner");
    const cardsContainer = document.getElementById("recommendationsCards");

    const recommendations = transactions.length
        ? generateRecommendations(transactions)
        : [];

    if (!recommendations.length) {
        emptyState.style.display = "flex";
        banner.hidden = true;
        cardsContainer.hidden = true;
        return;
    }

    emptyState.style.display = "none";
    banner.hidden = false;
    cardsContainer.hidden = false;
    cardsContainer.innerHTML = "";

    recommendations.forEach(recommendation => {

        const meta = RECOMMENDATION_META[recommendation.type] || RECOMMENDATION_META.balanced;

        const card = document.createElement("div");
        card.className = "recommendation-card";

        const tagRow = document.createElement("div");
        tagRow.className = "recommendation-tag-row";

        const icon = document.createElement("span");
        icon.className = "recommendation-emoji";
        icon.textContent = meta.icon;
        tagRow.appendChild(icon);

        const tag = document.createElement("span");
        tag.className = `recommendation-tag ${meta.color}`;
        tag.textContent = meta.tag;
        tagRow.appendChild(tag);

        card.appendChild(tagRow);

        const divider = document.createElement("div");
        divider.className = "recommendation-divider";
        card.appendChild(divider);

        const title = document.createElement("h4");
        title.textContent = recommendation.title;
        card.appendChild(title);

        // The "why" behind the recommendation, kept visually distinct
        // from the advice itself so the two don't blur together.
        if (recommendation.reason) {

            const reason = document.createElement("p");
            reason.className = "recommendation-reason";
            reason.textContent = recommendation.reason;
            card.appendChild(reason);
        }

        const text = document.createElement("p");
        text.className = "recommendation-text";

        const actionLabel = document.createElement("span");
        actionLabel.textContent = "Suggested action: ";
        text.appendChild(actionLabel);
        text.appendChild(document.createTextNode(recommendation.text));

        card.appendChild(text);

        if (
            typeof recommendation.potentialSavings === "number" &&
            recommendation.potentialSavings > 0
        ) {

            const savings = document.createElement("div");
            savings.className = "recommendation-savings";

            const savingsLabel = document.createElement("span");
            savingsLabel.textContent = recommendation.savingsLabel || "Potential saving";
            savings.appendChild(savingsLabel);

            const savingsValue = document.createElement("strong");
            savingsValue.textContent = formatCurrency(recommendation.potentialSavings);
            savings.appendChild(savingsValue);

            card.appendChild(savings);
        }

        cardsContainer.appendChild(card);
    });
}



// =========================================
// INITIAL LOAD
// =========================================

(async function init() {

    const loggedIn = await requireLogin();

    if (!loggedIn) {
        return;
    }

    renderUserInfo();
    await loadCategories();
    loadTransactions();

})();