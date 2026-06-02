const state = {
    emailFilter: "all",
    selectedCategoryId: null,
};

const statusText = document.querySelector("#statusText");
const overviewGrid = document.querySelector("#overviewGrid");
const emailsTable = document.querySelector("#emailsTable");
const filesTable = document.querySelector("#filesTable");
const categoriesList = document.querySelector("#categoriesList");
const categoryEmailsTable = document.querySelector("#categoryEmailsTable");
const resultsTable = document.querySelector("#resultsTable");
const detailTitle = document.querySelector("#detailTitle");
const emailDetail = document.querySelector("#emailDetail");

document.querySelector("#refreshBtn").addEventListener("click", refreshAll);
document.querySelector("#ingestBtn").addEventListener("click", () => runAction("/emails/ingest", "Inbox загружен"));
document.querySelector("#processNextBtn").addEventListener("click", () => runAction("/processing/process-next?limit=5", "Следующие письма обработаны"));
document.querySelector("#processAllBtn").addEventListener("click", () => runAction("/processing/process-all", "Все доступные письма обработаны"));
document.querySelector("#resetDbBtn").addEventListener("click", resetDatabase);

document.querySelectorAll(".nav-link").forEach((button) => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".nav-link").forEach((item) => item.classList.remove("active"));
        document.querySelectorAll(".page-section").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        document.querySelector(`#${button.dataset.target}`).classList.add("active");
    });
});

document.querySelectorAll(".filter").forEach((button) => {
    button.addEventListener("click", async () => {
        document.querySelectorAll(".filter").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        state.emailFilter = button.dataset.filter;
        await loadEmails();
    });
});

refreshAll();

async function refreshAll() {
    setStatus("Обновление данных...");
    try {
        await Promise.all([
            loadOverview(),
            loadEmails(),
            loadInboxFiles(),
            loadCategories(),
            loadClassificationResults(),
        ]);
        setStatus("Данные обновлены");
    } catch (error) {
        setStatus(`Ошибка: ${error.message}`);
    }
}

async function runAction(url, successMessage) {
    const buttons = document.querySelectorAll("button");
    buttons.forEach((button) => {
        button.disabled = true;
    });
    setStatus("Выполняется операция...");

    try {
        const result = await postJson(url);
        setStatus(`${successMessage}. Processed: ${result.processed ?? result.saved ?? 0}`);
        await refreshAll();
    } catch (error) {
        setStatus(`Ошибка: ${error.message}`);
    } finally {
        buttons.forEach((button) => {
            button.disabled = false;
        });
    }
}

async function resetDatabase() {
    const confirmed = window.confirm("Очистить все таблицы БД и создать их заново?");
    if (!confirmed) {
        return;
    }

    const buttons = document.querySelectorAll("button");
    buttons.forEach((button) => {
        button.disabled = true;
    });
    setStatus("БД очищается...");

    try {
        await postJson("/db/reset");
        detailTitle.textContent = "Письмо не выбрано";
        emailDetail.className = "detail-empty";
        emailDetail.textContent = "Выберите письмо в таблице.";
        state.selectedCategoryId = null;
        setStatus("БД очищена и переинициализирована");
        await refreshAll();
    } catch (error) {
        setStatus(`Ошибка: ${error.message}`);
    } finally {
        buttons.forEach((button) => {
            button.disabled = false;
        });
    }
}

async function loadOverview() {
    const data = await getJson("/db/overview");
    const metrics = [
        ["Всего писем", data.total_emails],
        ["Обработано", data.classified],
        ["Ожидают", data.pending],
        ["Мусор", data.garbage],
        ["Категорий", data.categories],
        ["Embeddings", data.embeddings],
    ];

    overviewGrid.replaceChildren(...metrics.map(([label, value]) => {
        const item = document.createElement("div");
        item.className = "metric";

        const number = document.createElement("span");
        number.className = "metric-value";
        number.textContent = value ?? 0;

        const caption = document.createElement("span");
        caption.className = "metric-label";
        caption.textContent = label;

        item.append(number, caption);
        return item;
    }));
}

async function loadEmails() {
    const rows = await getJson(`/emails/list?status=${encodeURIComponent(state.emailFilter)}`);
    renderEmailRows(emailsTable, rows);
}

async function loadInboxFiles() {
    const rows = await getJson("/db/inbox-files");
    filesTable.replaceChildren(...rows.map((file) => {
        return tr([
            file.filename,
            file.extension || "-",
            formatBytes(file.size_bytes),
            badge(file.ingested ? "yes" : "no", file.ingested),
            badge(file.status, file.status !== "not_ingested"),
            file.processing_status || "-",
        ]);
    }));
}

async function loadCategories() {
    const rows = await getJson("/categories/list");
    categoriesList.replaceChildren(...rows.map((category) => {
        const button = document.createElement("button");
        button.className = "category-item";
        button.dataset.categoryId = category.id;

        const name = document.createElement("span");
        name.textContent = category.name;

        const count = document.createElement("span");
        count.className = "badge ok";
        count.textContent = category.emails_count;

        button.append(name, count);
        button.addEventListener("click", () => loadCategoryEmails(category.id));
        return button;
    }));

    if (rows.length && !state.selectedCategoryId) {
        await loadCategoryEmails(rows[0].id);
    }
}

async function loadCategoryEmails(categoryId) {
    state.selectedCategoryId = categoryId;
    document.querySelectorAll(".category-item").forEach((item) => {
        item.classList.toggle("active", Number(item.dataset.categoryId) === Number(categoryId));
    });
    const rows = await getJson(`/categories/${categoryId}/emails`);
    renderEmailRows(categoryEmailsTable, rows, true);
}

async function loadClassificationResults() {
    const rows = await getJson("/classification-results/list");
    resultsTable.replaceChildren(...rows.map((result) => {
        const row = tr([
            result.id,
            result.email_id,
            result.category,
            formatConfidence(result.confidence),
            result.method,
            result.reason || "-",
        ]);
        row.dataset.emailId = result.email_id;
        row.addEventListener("click", () => loadEmailDetail(result.email_id));
        return row;
    }));
}

function renderEmailRows(target, rows, compact = false) {
    if (!rows.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = compact ? 5 : 9;
        cell.textContent = "Нет данных";
        row.append(cell);
        target.replaceChildren(row);
        return;
    }

    target.replaceChildren(...rows.map((email) => {
        const cells = compact
            ? [
                email.id,
                email.filename,
                email.subject,
                formatConfidence(email.confidence),
                email.method || "-",
            ]
            : [
                email.id,
                email.filename,
                email.subject,
                badge(email.status, email.status === "parsed"),
                badge(email.is_garbage ? "yes" : "no", !email.is_garbage),
                email.processing_status || "-",
                email.category || "-",
                formatConfidence(email.confidence),
                email.method || "-",
            ];

        const row = tr(cells);
        row.dataset.emailId = email.id;
        row.addEventListener("click", () => loadEmailDetail(email.id));
        return row;
    }));
}

async function loadEmailDetail(emailId) {
    const email = await getJson(`/emails/${emailId}`);
    const parsed = email.parsed_json?.email || {};
    const classification = email.classification;

    detailTitle.textContent = `#${email.id} ${email.filename}`;
    emailDetail.className = "";
    emailDetail.replaceChildren(
        detailBlock("Тема", parsed.subject || email.subject || "Без темы"),
        detailBlock("Отправитель", formatContact(parsed.sender)),
        detailBlock("Получатели", (parsed.recipients || []).map(formatContact).join(", ") || "-"),
        detailBlock("Дата", parsed.received_at || "-"),
        detailBlock("Тело письма", parsed.body || "-"),
        detailBlock("Вложения", (parsed.attachments || []).join(", ") || "-"),
        detailBlock("Warnings", (email.parsed_json?.warnings || []).join(", ") || "-"),
        detailBlock("Категория", email.category || "-"),
        detailBlock("Confidence", formatConfidence(email.confidence)),
        detailBlock("Method", email.method || "-"),
        detailBlock("Reason", classification?.reason || "-"),
        detailBlock("Исправленная тема", classification?.corrected_subject || parsed.subject || "-"),
        detailBlock("Исправленное тело", classification?.corrected_body || parsed.body || "-"),
        detailBlock("Ошибки найдены", classification?.grammar_issues_found ? "yes" : "no"),
        detailJson("Grammar corrections", classification?.grammar_corrections || []),
        detailJson("Entities", classification?.entities || {}),
        detailJson("Similar emails", classification?.similar_emails || []),
    );
}

function detailBlock(label, value) {
    const block = document.createElement("div");
    block.className = "detail-block";

    const title = document.createElement("div");
    title.className = "detail-label";
    title.textContent = label;

    const content = document.createElement("div");
    content.className = "detail-value";
    content.textContent = value;

    block.append(title, content);
    return block;
}

function detailJson(label, value) {
    const block = document.createElement("div");
    block.className = "detail-block";

    const title = document.createElement("div");
    title.className = "detail-label";
    title.textContent = label;

    const content = document.createElement("pre");
    content.textContent = JSON.stringify(value, null, 2);

    block.append(title, content);
    return block;
}

async function getJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
}

async function postJson(url) {
    const response = await fetch(url, { method: "POST" });
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
}

function tr(values) {
    const row = document.createElement("tr");
    values.forEach((value) => {
        const cell = document.createElement("td");
        if (value instanceof Node) {
            cell.append(value);
        } else {
            cell.textContent = value ?? "-";
        }
        row.append(cell);
    });
    return row;
}

function badge(value, ok) {
    const item = document.createElement("span");
    item.className = `badge ${ok ? "ok" : "bad"}`;
    item.textContent = value;
    return item;
}

function setStatus(message) {
    statusText.textContent = message;
}

function formatContact(contact) {
    if (!contact) {
        return "-";
    }
    if (typeof contact === "string") {
        return contact;
    }
    const name = contact.name ? `${contact.name} ` : "";
    return `${name}<${contact.email || "unknown"}>`;
}

function formatConfidence(value) {
    if (value === null || value === undefined) {
        return "-";
    }
    return Number(value).toFixed(2);
}

function formatBytes(value) {
    if (!value) {
        return "0 B";
    }
    if (value < 1024) {
        return `${value} B`;
    }
    return `${(value / 1024).toFixed(1)} KB`;
}
