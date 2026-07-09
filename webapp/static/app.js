const tray = document.getElementById("tray");
const emptyState = document.getElementById("emptyState");
const runBtn = document.getElementById("runBtn");
const clearBtn = document.getElementById("clearBtn");

const CATEGORY_LABELS = {
  urgent_support: "Urgent Support",
  sales_lead: "Sales Lead",
  spam: "Spam",
  newsletter: "Newsletter",
  general: "General",
};

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function renderEmailCard(row, index) {
  const p = row.priority;
  const card = document.createElement("div");
  card.className = "email-card";
  card.style.animationDelay = `${index * 35}ms`;

  card.innerHTML = `
    <div class="priority-rail p${p}"></div>
    <div class="email-body">
      <div class="email-top">
        <p class="email-subject">${escapeHtml(row.subject)}</p>
        <span class="email-meta">${escapeHtml(row.processed_at || "")}</span>
      </div>
      <p class="email-sender">${escapeHtml(row.sender)}</p>
      <div class="badge-row">
        <span class="badge badge-priority p${p}">P${p}</span>
        <span class="badge">${CATEGORY_LABELS[row.category] || row.category}</span>
        <span class="badge">conf ${Number(row.confidence).toFixed(2)}</span>
        <span class="badge badge-engine">${row.engine}</span>
      </div>
      <p class="email-reasoning">${escapeHtml(row.reasoning)}</p>
      <button class="reply-toggle">▸ view suggested reply</button>
      <div class="reply-box">${escapeHtml(row.suggested_reply)}</div>
    </div>
  `;

  card.querySelector(".reply-toggle").addEventListener("click", (e) => {
    const box = card.querySelector(".reply-box");
    box.classList.toggle("open");
    e.target.textContent = box.classList.contains("open")
      ? "▾ hide suggested reply"
      : "▸ view suggested reply";
  });

  return card;
}

async function loadEmails() {
  const res = await fetch("/api/emails");
  const rows = await res.json();

  tray.querySelectorAll(".email-card").forEach((el) => el.remove());

  if (rows.length === 0) {
    emptyState.style.display = "block";
  } else {
    emptyState.style.display = "none";
    rows.forEach((row, i) => tray.appendChild(renderEmailCard(row, i)));
  }
}

async function loadStats() {
  const res = await fetch("/api/stats");
  const data = await res.json();
  document.getElementById("statTotal").textContent = data.total;
  document.getElementById("statUrgent").textContent = data.by_category.urgent_support || 0;
  document.getElementById("statSales").textContent = data.by_category.sales_lead || 0;
  document.getElementById("statGeneral").textContent = data.by_category.general || 0;
  document.getElementById("statSpam").textContent = data.by_category.spam || 0;
  document.getElementById("statNewsletter").textContent = data.by_category.newsletter || 0;
}

async function refreshAll() {
  await Promise.all([loadEmails(), loadStats()]);
}

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  runBtn.textContent = "Processing…";
  try {
    await fetch("/api/process", { method: "POST" });
    await refreshAll();
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Run Triage";
  }
});

clearBtn.addEventListener("click", async () => {
  await fetch("/api/clear", { method: "POST" });
  await refreshAll();
});

refreshAll();
