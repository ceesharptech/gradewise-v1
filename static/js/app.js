/* ═══════════════════════════════════════════════════════
   app.js  —  Student Performance Prediction System
═══════════════════════════════════════════════════════ */

"use strict";

// ── State ────────────────────────────────────────────────
let allStudents = [];
let currentUser = null;
let gradeChart = null;
let pfChart = null;
let selectedFile = null;

// ── Priority config ──────────────────────────────────────
const PRIORITY = {
  CRITICAL: {
    bg: "#fef2f2",
    text: "#dc2626",
    border: "#fecaca",
    dot: "#dc2626",
  },
  HIGH: { bg: "#fff7ed", text: "#ea580c", border: "#fed7aa", dot: "#ea580c" },
  MEDIUM: { bg: "#fefce8", text: "#ca8a04", border: "#fde68a", dot: "#ca8a04" },
  LOW: { bg: "#eff6ff", text: "#2563eb", border: "#bfdbfe", dot: "#2563eb" },
  NONE: { bg: "#f0fdf4", text: "#16a34a", border: "#bbf7d0", dot: "#16a34a" },
};

const GRADE_COLOURS = {
  A: { bg: "#dcfce7", text: "#16a34a" },
  B: { bg: "#dbeafe", text: "#2563eb" },
  C: { bg: "#fef9c3", text: "#ca8a04" },
  D: { bg: "#ffedd5", text: "#ea580c" },
  F: { bg: "#fee2e2", text: "#dc2626" },
};

// ── Colour helpers ───────────────────────────────────────
function scoreColour(s) {
  if (s >= 70) return "#16a34a";
  if (s >= 50) return "#2563eb";
  if (s >= 45) return "#d97706";
  return "#dc2626";
}

// ── Toast ────────────────────────────────────────────────
function toast(msg, type = "success") {
  const el = document.getElementById("toast");
  const ico = document.getElementById("toast-icon");
  const txt = document.getElementById("toast-msg");
  ico.textContent = type === "success" ? "✓" : type === "error" ? "✕" : "!";
  txt.textContent = msg;
  el.className = `toast toast-${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), 3500);
}

// ── Auth guard: redirect 401 to login ───────────────────
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, opts);
  if (res.status === 401) {
    window.location.href = "/login";
    return null;
  }
  return res;
}

async function doLogout() {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
}

// ── Tab navigation ───────────────────────────────────────
function showTab(name, el) {
  document
    .querySelectorAll(".tab-section")
    .forEach((s) => s.classList.add("hidden"));
  document
    .querySelectorAll(".nav-item")
    .forEach((n) => n.classList.remove("active"));

  document.getElementById(`tab-${name}`).classList.remove("hidden");
  const target = el?.classList?.contains("nav-item")
    ? el
    : document.querySelector(`[data-tab="${name}"]`);
  if (target) target.classList.add("active");

  if (name === "dashboard") loadDashboard();
  if (name === "students") renderStudentsTable(allStudents);
  if (name === "reports") populatePDFSelect();
  if (name === "settings") loadSettings();
  if (name === "admin") loadAdminUsers();
}

function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function updateLabel(lblId, inputId) {
  document.getElementById(lblId).textContent =
    document.getElementById(inputId).value;
}

// ── Load current user, set sidebar ──────────────────────
async function loadCurrentUser() {
  const res = await apiFetch("/api/auth/me");
  if (!res) return;
  currentUser = await res.json();

  set("nav-fullname", currentUser.full_name);
  set("nav-role", currentUser.role === "admin" ? "Administrator" : "Lecturer");
  document.getElementById("nav-avatar").textContent = currentUser.full_name
    .charAt(0)
    .toUpperCase();

  if (currentUser.role === "admin") {
    document
      .querySelectorAll(".nav-admin")
      .forEach((el) => el.classList.remove("hidden"));
  }
}

// ── Dashboard ────────────────────────────────────────────
async function loadDashboard() {
  const res = await apiFetch("/api/dashboard");
  if (!res) return;
  const data = await res.json();
  const s = data.stats;
  const ui = data.upload_info;
  const hasData = s && s.total_students > 0;

  document.getElementById("dash-empty").style.display = hasData
    ? "none"
    : "flex";
  document.getElementById("score-breakdown-card").style.display = hasData
    ? "block"
    : "none";
  if (!hasData) return;

  set("d-total", s.total_students);
  set("d-pass", s.pass_rate + "%");
  set("d-avg", s.average_score);
  set("d-risk", s.at_risk_count);
  set("d-pass-sub", `${s.pass_count} passed · ${s.fail_count} failed`);
  set(
    "d-risk-sub",
    `${s.at_risk_count} student${s.at_risk_count !== 1 ? "s" : ""} flagged`,
  );
  set("d-avg-sub", `Highest: ${s.highest_score}  ·  Lowest: ${s.lowest_score}`);

  // Priority summary in stat card
  const pd = s.priority_distribution || {};
  const critical = (pd.CRITICAL || 0) + (pd.HIGH || 0);
  if (critical > 0)
    document.getElementById("d-risk-sub").textContent +=
      `  ·  ${critical} critical/high priority`;

  if (ui) {
    const badge = document.getElementById("upload-badge");
    badge.classList.remove("hidden");
    set("upload-badge-text", `${ui.filename} · ${ui.uploaded_at}`);
  }

  renderCharts(s);
}

function renderCharts(s) {
  const gd = s.grade_distribution || {};
  const gradeLabels = ["A", "B", "C", "D", "F"];
  const gradeColors = ["#16a34a", "#2563eb", "#ca8a04", "#ea580c", "#dc2626"];

  if (gradeChart) gradeChart.destroy();
  gradeChart = new Chart(document.getElementById("gradeChart"), {
    type: "bar",
    data: {
      labels: gradeLabels,
      datasets: [
        {
          label: "Students",
          data: gradeLabels.map((g) => gd[g] || 0),
          backgroundColor: gradeColors,
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { family: "Geist" } },
          grid: { color: "#f1f5f9" },
        },
        x: {
          ticks: { font: { family: "Geist", weight: "600" } },
          grid: { display: false },
        },
      },
      responsive: true,
      maintainAspectRatio: false,
    },
  });

  if (pfChart) pfChart.destroy();
  pfChart = new Chart(document.getElementById("pfChart"), {
    type: "doughnut",
    data: {
      labels: ["Pass", "Fail"],
      datasets: [
        {
          data: [s.pass_count, s.fail_count],
          backgroundColor: ["#16a34a", "#dc2626"],
          borderWidth: 0,
          hoverOffset: 6,
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
    },
  });

  const legendEl = document.getElementById("donut-legend");
  const total = s.pass_count + s.fail_count;
  legendEl.innerHTML = [
    { label: "Pass", count: s.pass_count, colour: "#16a34a" },
    { label: "Fail", count: s.fail_count, colour: "#dc2626" },
  ]
    .map(
      (item) => `
    <div class="donut-legend-item">
      <div class="donut-legend-left">
        <div class="legend-dot" style="background:${item.colour}"></div>
        <span>${item.label}</span>
      </div>
      <div>
        <span class="legend-count">${item.count}</span>
        <span class="legend-pct">${total ? Math.round((item.count / total) * 100) : 0}%</span>
        <span class="legend-arrow">›</span>
      </div>
    </div>`,
    )
    .join("");
}

// ── File upload ──────────────────────────────────────────
function dragOver(e) {
  e.preventDefault();
  document.getElementById("drop-zone").classList.add("dragover");
}
function dragLeave() {
  document.getElementById("drop-zone").classList.remove("dragover");
}
function dropFile(e) {
  e.preventDefault();
  dragLeave();
  processFileSelection(e.dataTransfer.files[0]);
}
function handleFileSelect(e) {
  processFileSelection(e.target.files[0]);
}

function processFileSelection(file) {
  if (!file) return;
  const ext = file.name.split(".").pop().toLowerCase();
  if (!["csv", "xlsx", "xls"].includes(ext)) {
    toast("Only CSV or Excel files are accepted", "error");
    return;
  }
  selectedFile = file;
  set("file-name", file.name);
  set("file-size", `${(file.size / 1024).toFixed(1)} KB`);
  document.getElementById("file-info").classList.remove("hidden");
  const btn = document.getElementById("upload-btn");
  btn.disabled = false;
  btn.classList.remove("btn-disabled");
}

function clearFile() {
  selectedFile = null;
  document.getElementById("file-info").classList.add("hidden");
  document.getElementById("file-input").value = "";
  document.getElementById("upload-result").classList.add("hidden");
  const btn = document.getElementById("upload-btn");
  btn.disabled = true;
  btn.classList.add("btn-disabled");
}

async function uploadFile() {
  if (!selectedFile) return;
  const prog = document.getElementById("upload-progress");
  const fill = document.getElementById("progress-fill");
  prog.classList.remove("hidden");

  let p = 0;
  const ticker = setInterval(() => {
    p = Math.min(p + Math.random() * 14, 88);
    fill.style.width = p + "%";
    set("progress-pct", Math.round(p) + "%");
  }, 200);

  const fd = new FormData();
  fd.append("file", selectedFile);

  try {
    const res = await apiFetch("/api/upload-bulk", {
      method: "POST",
      body: fd,
    });
    if (!res) return;
    const data = await res.json();

    clearInterval(ticker);
    fill.style.width = "100%";
    set("progress-pct", "100%");
    setTimeout(() => prog.classList.add("hidden"), 700);

    if (!res.ok) {
      showUploadResult(
        false,
        data.error || (data.errors ? data.errors.join("\n") : "Upload failed"),
        null,
      );
      return;
    }
    allStudents = await (await apiFetch("/api/students")).json();
    showUploadResult(true, data.message, data);
    loadDashboard();
    toast(`${data.upload_info.successful} students processed successfully`);
  } catch (err) {
    clearInterval(ticker);
    prog.classList.add("hidden");
    toast("Upload failed: " + err.message, "error");
  }
}

function showUploadResult(ok, msg, data) {
  const box = document.getElementById("upload-result");
  box.classList.remove("hidden");
  if (ok && data) {
    const ui = data.upload_info;
    box.style.cssText =
      "background:#f0fdf4;border:1px solid #bbf7d0;padding:14px 16px;border-radius:8px";
    box.innerHTML = `
      <p style="font-size:13px;font-weight:600;color:#15803d;margin-bottom:12px">${msg}</p>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center">
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px">
          <p style="font-size:11px;color:#94a3b8">Total</p>
          <p style="font-size:20px;font-weight:700;color:#0f172a">${ui.total}</p>
        </div>
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px">
          <p style="font-size:11px;color:#94a3b8">Processed</p>
          <p style="font-size:20px;font-weight:700;color:#16a34a">${ui.successful}</p>
        </div>
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px">
          <p style="font-size:11px;color:#94a3b8">Errors</p>
          <p style="font-size:20px;font-weight:700;color:#dc2626">${ui.failed}</p>
        </div>
      </div>
      ${
        data.errors?.length
          ? `
        <div style="margin-top:10px;padding:10px 12px;background:#fff;border:1px solid #fecaca;
                    border-radius:8px;max-height:80px;overflow-y:auto">
          ${data.errors.map((e) => `<p style="font-size:11.5px;color:#dc2626">• ${e}</p>`).join("")}
        </div>`
          : ""
      }`;
  } else {
    box.style.cssText =
      "background:#fef2f2;border:1px solid #fecaca;padding:14px 16px;border-radius:8px";
    box.innerHTML = `<p style="font-size:13px;font-weight:500;color:#dc2626">${msg}</p>`;
  }
}

async function downloadTemplate() {
  window.location.href = "/api/template";
}

// ── Single prediction ────────────────────────────────────
async function submitSingle() {
  const name = document.getElementById("p-name").value.trim();
  if (!name) {
    toast("Please enter a student name", "warning");
    return;
  }

  const payload = {
    name,
    student_id: document.getElementById("p-id").value.trim() || undefined,
    exam_score: +document.getElementById("p-exam").value,
    test1: +document.getElementById("p-t1").value,
    test2: +document.getElementById("p-t2").value,
    test3: +document.getElementById("p-t3").value,
    assignment1: +document.getElementById("p-a1").value,
    assignment2: +document.getElementById("p-a2").value,
    assignment3: +document.getElementById("p-a3").value,
    attendance: +document.getElementById("p-att").value,
  };

  try {
    const res = await apiFetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res) return;
    const data = await res.json();
    if (!res.ok) {
      toast(
        Array.isArray(data.error) ? data.error.join(", ") : data.error,
        "error",
      );
      return;
    }

    allStudents = await (await apiFetch("/api/students")).json();
    renderSingleResult(data);
    toast("Prediction generated successfully");
  } catch (err) {
    toast("Error: " + err.message, "error");
  }
}

function renderSingleResult(s) {
  document.getElementById("predict-empty").classList.add("hidden");
  document.getElementById("predict-result").classList.remove("hidden");

  const col = scoreColour(s.final_score);
  document.getElementById("r-score").textContent = s.final_score.toFixed(2);
  document.getElementById("r-score").style.color = col;

  const gc = GRADE_COLOURS[s.grade_category] || {
    bg: "#f1f5f9",
    text: "#475569",
  };
  styleResultBadge("r-grade-card", "r-grade", s.grade_category, gc.bg, gc.text);

  const pfOk = s.pass_fail === "Pass";
  styleResultBadge(
    "r-pf-card",
    "r-pf",
    s.pass_fail,
    pfOk ? "#f0fdf4" : "#fef2f2",
    pfOk ? "#16a34a" : "#dc2626",
  );

  const arOk = s.at_risk !== "Yes";
  styleResultBadge(
    "r-risk-card",
    "r-risk",
    s.at_risk === "Yes" ? "At Risk" : "On Track",
    arOk ? "#f0fdf4" : "#fef2f2",
    arOk ? "#16a34a" : "#dc2626",
  );

  document.getElementById("r-breakdown").innerHTML = [
    { label: "Exam Score", sub: "60%", val: s.exam_score, colour: "#2563eb" },
    { label: "Avg Test", sub: "20%", val: s.avg_test, colour: "#7c3aed" },
    {
      label: "Avg Assignments",
      sub: "10%",
      val: s.avg_assignment,
      colour: "#16a34a",
    },
    { label: "Attendance", sub: "10%", val: s.attendance, colour: "#d97706" },
  ]
    .map(
      (it) => `
    <div class="breakdown-item">
      <div class="breakdown-header">
        <span>${it.label} <span style="color:#94a3b8;font-size:11.5px">(${it.sub})</span></span>
        <span class="breakdown-score">${it.val.toFixed(1)}</span>
      </div>
      <div class="breakdown-track">
        <div class="breakdown-fill" style="width:${it.val}%;background:${it.colour}"></div>
      </div>
    </div>`,
    )
    .join("");

  const rfBox = document.getElementById("r-risk-box");
  if (s.risk_factors?.length) {
    rfBox.classList.remove("hidden");
    document.getElementById("r-risk-list").innerHTML = s.risk_factors
      .map((f) => `<li>${f}</li>`)
      .join("");
  } else rfBox.classList.add("hidden");

  // Recommendations
  renderRecommendationsInline(s, "predict-result");
}

function styleResultBadge(cardId, valId, text, bg, textCol) {
  document.getElementById(valId).textContent = text;
  document.getElementById(valId).style.color = textCol;
  document.getElementById(cardId).style.background = bg;
}

// ── Recommendations ──────────────────────────────────────
function renderRecommendationsInline(s, containerId) {
  const recs = s.recommendations || [];
  const overall = s.recommendation_priority || "NONE";
  if (!recs.length) return;

  const container = document.getElementById(containerId);
  const existing = container.querySelector(".recs-section");
  if (existing) existing.remove();

  const p = PRIORITY[overall] || PRIORITY.NONE;
  const section = document.createElement("div");
  section.className = "recs-section card";
  section.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <h4 class="card-title">Intervention Recommendations</h4>
      <span class="priority-badge" style="background:${p.bg};color:${p.text};border:1px solid ${p.border}">
        <span style="width:7px;height:7px;border-radius:50%;background:${p.dot};display:inline-block"></span>
        ${overall} PRIORITY
      </span>
    </div>
    ${recs
      .map((r) => {
        const rp = PRIORITY[r.priority] || PRIORITY.NONE;
        return `<div class="rec-card" style="background:${rp.bg};border-color:${rp.border}">
        <div class="rec-header">
          <div class="rec-priority-dot" style="background:${rp.dot}"></div>
          <span class="rec-title" style="color:${rp.text}">${r.title}</span>
        </div>
        <p class="rec-detail" style="color:${rp.text};opacity:.85">${r.detail}</p>
      </div>`;
      })
      .join("")}`;
  container.appendChild(section);
}

// ── Students table ───────────────────────────────────────
function renderStudentsTable(data) {
  const tbody = document.getElementById("students-table");
  const empty = document.getElementById("students-empty");
  const sub = document.getElementById("students-count-sub");

  sub.textContent = data.length
    ? `${data.length} student${data.length !== 1 ? "s" : ""} loaded`
    : "No students loaded";

  if (!data.length) {
    tbody.innerHTML = "";
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");

  tbody.innerHTML = data
    .map((s, i) => {
      const gc = GRADE_COLOURS[s.grade_category] || {
        bg: "#f1f5f9",
        text: "#475569",
      };
      const pfOk = s.pass_fail === "Pass";
      const arOk = s.at_risk !== "Yes";
      const pp = PRIORITY[s.recommendation_priority] || PRIORITY.NONE;
      return `
    <tr onclick="openModal(${s.id})">
      <td style="color:#2563eb;font-weight:500">${s.student_id}</td>
      <td style="font-weight:500">${s.name}</td>
      <td style="text-align:center">${s.exam_score.toFixed(1)}</td>
      <td style="text-align:center">${s.avg_test.toFixed(1)}</td>
      <td style="text-align:center">${s.avg_assignment.toFixed(1)}</td>
      <td style="text-align:center">${s.attendance.toFixed(1)}%</td>
      <td style="text-align:center;font-weight:700;color:${scoreColour(s.final_score)}">
        ${s.final_score.toFixed(2)}
      </td>
      <td style="text-align:center">
        <span class="badge" style="background:${gc.bg};color:${gc.text}">${s.grade_category}</span>
      </td>
      <td style="text-align:center">
        <span class="badge ${pfOk ? "badge-green" : "badge-red"}">${s.pass_fail}</span>
      </td>
      <td style="text-align:center">
        <span class="badge ${arOk ? "badge-green" : "badge-red"}">${s.at_risk}</span>
      </td>
      <td style="text-align:center">
        <span class="priority-badge" style="background:${pp.bg};color:${pp.text};
              border:1px solid ${pp.border};font-size:11px">
          <span style="width:6px;height:6px;border-radius:50%;background:${pp.dot};
                       display:inline-block"></span>
          ${s.recommendation_priority || "NONE"}
        </span>
      </td>
      <td style="text-align:center">
        <button onclick="event.stopPropagation();exportPDF(${s.id})"
          class="btn btn-outline" style="padding:4px 10px;font-size:11.5px;height:auto">
          PDF
        </button>
      </td>
    </tr>`;
    })
    .join("");
}

function filterStudents() {
  const q = document.getElementById("search-input").value.toLowerCase();
  const grade = document.getElementById("filter-grade").value;
  const risk = document.getElementById("filter-risk").value;
  renderStudentsTable(
    allStudents.filter(
      (s) =>
        (!q ||
          s.name.toLowerCase().includes(q) ||
          s.student_id.toLowerCase().includes(q)) &&
        (!grade || s.grade_category === grade) &&
        (!risk || s.at_risk === risk),
    ),
  );
}

// ── Student detail modal ─────────────────────────────────
async function openModal(id) {
  const res = await apiFetch(`/api/student/${id}`);
  if (!res) return;
  const s = await res.json();

  set("modal-title", s.name);
  set(
    "modal-sub",
    `${s.student_id}  ·  Final Score: ${s.final_score.toFixed(2)}`,
  );

  const col = scoreColour(s.final_score);
  const gc = GRADE_COLOURS[s.grade_category] || {
    bg: "#f1f5f9",
    text: "#475569",
  };

  // Build individual score items dynamically
  const testItems = Object.entries(s)
    .filter(([k]) => /^test\d+$/.test(k))
    .map(
      ([k, v], i) => `<div class="modal-score-item">
      <p>Test ${i + 1}</p><p style="color:#7c3aed">${(+v).toFixed(1)}</p></div>`,
    )
    .join("");
  const asgnItems = Object.entries(s)
    .filter(([k]) => /^assignment\d+$/.test(k))
    .map(
      ([k, v], i) => `<div class="modal-score-item">
      <p>Assignment ${i + 1}</p><p style="color:#16a34a">${(+v).toFixed(1)}</p></div>`,
    )
    .join("");

  document.getElementById("modal-body").innerHTML = `
    <div class="modal-stat-row">
      <div class="modal-stat"><p class="modal-stat-label">Final Score</p>
        <p class="modal-stat-val" style="color:${col}">${s.final_score.toFixed(2)}</p></div>
      <div class="modal-stat" style="background:${gc.bg}"><p class="modal-stat-label">Grade</p>
        <p class="modal-stat-val" style="color:${gc.text}">${s.grade_category}</p></div>
      <div class="modal-stat" style="background:${s.pass_fail === "Pass" ? "#f0fdf4" : "#fef2f2"}">
        <p class="modal-stat-label">Status</p>
        <p class="modal-stat-val" style="color:${s.pass_fail === "Pass" ? "#16a34a" : "#dc2626"}">${s.pass_fail}</p></div>
      <div class="modal-stat" style="background:${s.at_risk === "Yes" ? "#fef2f2" : "#f0fdf4"}">
        <p class="modal-stat-label">At-Risk</p>
        <p class="modal-stat-val" style="color:${s.at_risk === "Yes" ? "#dc2626" : "#16a34a"}">${s.at_risk}</p></div>
    </div>

    <div class="card" style="border:1px solid #e2e8f0">
      <h4 class="card-title" style="margin-bottom:14px">Score Breakdown</h4>
      <div class="breakdown-list">
        ${[
          ["Exam Score", "exam_score", "60%", "#2563eb"],
          ["Avg Test Score", "avg_test", "20%", "#7c3aed"],
          ["Avg Assignment Score", "avg_assignment", "10%", "#16a34a"],
          ["Attendance", "attendance", "10%", "#d97706"],
        ]
          .map(
            ([l, k, w, c]) => `
          <div class="breakdown-item">
            <div class="breakdown-header">
              <span>${l} <span style="color:#94a3b8;font-size:11.5px">(${w})</span></span>
              <span class="breakdown-score">${(+s[k]).toFixed(1)}</span>
            </div>
            <div class="breakdown-track">
              <div class="breakdown-fill" style="width:${s[k]}%;background:${c}"></div>
            </div>
          </div>`,
          )
          .join("")}
      </div>
    </div>

    <div>
      <p class="card-title" style="margin-bottom:10px">Individual Assessment Scores</p>
      <div class="modal-scores-grid">${testItems}${asgnItems}</div>
    </div>

    ${
      s.risk_factors?.length
        ? `<div class="alert-box alert-danger">
          <div class="alert-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            Risk Factors Identified
          </div>
          <ul class="alert-list">
            ${s.risk_factors.map((r) => `<li>${r}</li>`).join("")}
          </ul>
        </div>`
        : `<div style="padding:12px 14px;background:#f0fdf4;border:1px solid #bbf7d0;
                     border-radius:8px;font-size:13px;color:#16a34a;font-weight:500">
           No risk factors. This student is on track.
         </div>`
    }

    ${
      (s.recommendations || []).length
        ? `
      <div id="modal-recs-wrapper"></div>`
        : ""
    }

    <div style="display:flex;justify-content:flex-end">
      <button onclick="exportPDF(${s.id})" class="btn btn-primary" style="gap:6px">
        Download PDF Report
      </button>
    </div>`;

  document.getElementById("modal").classList.remove("hidden");

  // Inject recommendations after DOM is ready
  if ((s.recommendations || []).length) {
    const wrapper = document.getElementById("modal-recs-wrapper");
    wrapper.id = "modal-body-recs";
    renderRecommendationsInline(s, "modal-body-recs");
  }
}

function closeModal() {
  document.getElementById("modal").classList.add("hidden");
}
function handleModalClick(e, modalId) {
  if (e.target === document.getElementById(modalId || "modal")) {
    document.getElementById(modalId || "modal").classList.add("hidden");
  }
}

// ── Settings ─────────────────────────────────────────────
async function loadSettings() {
  const res = await apiFetch("/api/settings");
  if (!res) return;
  const data = await res.json();

  const sc = data.scheme || {};
  const w = sc.weights || {};
  const gb = sc.grade_boundaries || {};
  const es = data.email_settings || {};

  document.getElementById("sc-num-tests").value = sc.num_tests || 3;
  document.getElementById("sc-num-assignments").value = sc.num_assignments || 3;
  document.getElementById("sw-exam").value = w.exam ?? 60;
  document.getElementById("sw-tests").value = w.tests ?? 20;
  document.getElementById("sw-assignments").value = w.assignments ?? 10;
  document.getElementById("sw-attendance").value = w.attendance ?? 10;
  document.getElementById("gb-a").value = gb.A ?? 70;
  document.getElementById("gb-b").value = gb.B ?? 60;
  document.getElementById("gb-c").value = gb.C ?? 50;
  document.getElementById("gb-d").value = gb.D ?? 45;
  document.getElementById("sc-pass-mark").value = sc.pass_mark ?? 45;

  document.getElementById("en-enabled").checked = !!es.notifications_enabled;
  document.getElementById("en-threshold").value = es.threshold ?? 10;
  document.getElementById("en-recipient").value = es.recipient_email || "";
  document.getElementById("en-sender").value = es.sender_email || "";
  document.getElementById("en-smtp").value = es.smtp_server || "smtp.gmail.com";
  document.getElementById("en-port").value = es.smtp_port || 587;

  recalcWeightSum();
}

function recalcWeightSum() {
  const total = ["exam", "tests", "assignments", "attendance"].reduce(
    (s, k) => s + (+document.getElementById(`sw-${k}`).value || 0),
    0,
  );
  const badge = document.getElementById("weight-sum-badge");
  badge.textContent = `Total: ${total}%`;
  badge.className = `weight-sum-badge ${total === 100 ? "weight-sum-ok" : "weight-sum-err"}`;
}

function updateSchemeUI() {
  /* reserved for dynamic field rendering if needed */
}

async function saveScheme() {
  const scheme = {
    num_tests: +document.getElementById("sc-num-tests").value,
    num_assignments: +document.getElementById("sc-num-assignments").value,
    weights: {
      exam: +document.getElementById("sw-exam").value,
      tests: +document.getElementById("sw-tests").value,
      assignments: +document.getElementById("sw-assignments").value,
      attendance: +document.getElementById("sw-attendance").value,
    },
    grade_boundaries: {
      A: +document.getElementById("gb-a").value,
      B: +document.getElementById("gb-b").value,
      C: +document.getElementById("gb-c").value,
      D: +document.getElementById("gb-d").value,
    },
    pass_mark: +document.getElementById("sc-pass-mark").value,
  };

  const res = await apiFetch("/api/settings/scheme", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scheme }),
  });
  if (!res) return;
  const data = await res.json();
  res.ok ? toast("Grading scheme saved") : toast(data.error, "error");
}

async function saveEmailSettings() {
  const settings = {
    notifications_enabled: document.getElementById("en-enabled").checked,
    threshold: +document.getElementById("en-threshold").value,
    recipient_email: document.getElementById("en-recipient").value.trim(),
    sender_email: document.getElementById("en-sender").value.trim(),
    sender_password: document.getElementById("en-password").value,
    smtp_server: document.getElementById("en-smtp").value.trim(),
    smtp_port: +document.getElementById("en-port").value,
  };
  const res = await apiFetch("/api/settings/email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email_settings: settings }),
  });
  if (!res) return;
  const data = await res.json();
  res.ok ? toast("Email settings saved") : toast(data.error, "error");
}

async function sendTestEmail() {
  await saveEmailSettings();
  const res = await apiFetch("/api/settings/email/test", { method: "POST" });
  if (!res) return;
  const data = await res.json();
  res.ok ? toast("Test email sent successfully") : toast(data.error, "error");
}

// ── Admin ─────────────────────────────────────────────────
async function loadAdminUsers() {
  const res = await apiFetch("/api/admin/users");
  if (!res) return;
  const users = await res.json();
  const tbody = document.getElementById("admin-users-table");
  const empty = document.getElementById("admin-users-empty");

  if (!users.length) {
    tbody.innerHTML = "";
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");

  tbody.innerHTML = users
    .map(
      (u) => `
    <tr>
      <td style="font-weight:500">${u.full_name}</td>
      <td style="color:#2563eb">${u.username}</td>
      <td style="color:#64748b">${u.email}</td>
      <td>
        <span class="badge ${u.active ? "badge-green" : "badge-red"}">
          ${u.active ? "Active" : "Inactive"}
        </span>
        ${u.must_change_pw ? '<span class="badge badge-yellow" style="margin-left:4px">Pending PW</span>' : ""}
      </td>
      <td style="color:#64748b;font-size:12px">${u.created_at?.slice(0, 10) || "—"}</td>
      <td style="display:flex;gap:6px;flex-wrap:wrap">
        <button class="admin-action-btn" onclick="resetPassword(${u.id})">Reset PW</button>
        ${
          u.active
            ? `<button class="admin-action-btn danger" onclick="deactivateUser(${u.id})">Deactivate</button>`
            : `<button class="admin-action-btn" onclick="reactivateUser(${u.id})">Reactivate</button>`
        }
      </td>
    </tr>`,
    )
    .join("");
}

function openAddLecturer() {
  document.getElementById("modal-add-lecturer").classList.remove("hidden");
}
function closeAddLecturer() {
  document.getElementById("modal-add-lecturer").classList.add("hidden");
  ["al-name", "al-username", "al-email"].forEach(
    (id) => (document.getElementById(id).value = ""),
  );
  document.getElementById("add-lecturer-error").classList.add("hidden");
}

async function submitAddLecturer() {
  const payload = {
    full_name: document.getElementById("al-name").value.trim(),
    username: document.getElementById("al-username").value.trim(),
    email: document.getElementById("al-email").value.trim(),
  };
  if (!payload.full_name || !payload.username || !payload.email) {
    document.getElementById("add-lecturer-error-msg").textContent =
      "All fields are required.";
    document.getElementById("add-lecturer-error").classList.remove("hidden");
    return;
  }
  const res = await apiFetch("/api/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res) return;
  const data = await res.json();
  if (!res.ok) {
    document.getElementById("add-lecturer-error-msg").textContent = data.error;
    document.getElementById("add-lecturer-error").classList.remove("hidden");
    return;
  }
  closeAddLecturer();
  loadAdminUsers();
  toast(`Lecturer account created for ${data.full_name}`);
}

async function deactivateUser(uid) {
  if (!confirm("Deactivate this lecturer account?")) return;
  const res = await apiFetch(`/api/admin/users/${uid}/deactivate`, {
    method: "POST",
  });
  if (!res) return;
  const data = await res.json();
  res.ok
    ? (loadAdminUsers(), toast("Account deactivated"))
    : toast(data.error, "error");
}

async function reactivateUser(uid) {
  const res = await apiFetch(`/api/admin/users/${uid}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active: true }),
  });
  if (!res) return;
  const data = await res.json();
  res.ok
    ? (loadAdminUsers(), toast("Account reactivated"))
    : toast(data.error, "error");
}

async function resetPassword(uid) {
  if (
    !confirm(
      "Reset this lecturer's password? They will be required to set a new one on next login.",
    )
  )
    return;
  const res = await apiFetch(`/api/admin/users/${uid}/reset-password`, {
    method: "POST",
  });
  if (!res) return;
  const data = await res.json();
  res.ok
    ? (loadAdminUsers(), toast("Password reset"))
    : toast(data.error, "error");
}

// ── Reports ──────────────────────────────────────────────
function populatePDFSelect() {
  const sel = document.getElementById("pdf-student-select");
  sel.innerHTML =
    '<option value="">Select a student</option>' +
    allStudents
      .map(
        (s) => `<option value="${s.id}">${s.name} (${s.student_id})</option>`,
      )
      .join("");
}

async function exportStudentPDF() {
  const id = document.getElementById("pdf-student-select").value;
  if (!id) {
    toast("Please select a student", "warning");
    return;
  }
  exportPDF(+id);
}

function exportPDF(id) {
  window.location.href = `/api/export/student/${id}`;
}
async function exportClassExcel() {
  if (!allStudents.length) {
    toast("No data to export", "warning");
    return;
  }
  window.location.href = "/api/export/class";
}

// ── Clear all ─────────────────────────────────────────────
async function clearData() {
  if (!confirm("Clear all student data? This cannot be undone.")) return;
  await apiFetch("/api/clear", { method: "POST" });
  allStudents = [];
  loadDashboard();
  renderStudentsTable([]);
  populatePDFSelect();
  clearFile();
  document.getElementById("upload-result").classList.add("hidden");
  document.getElementById("upload-badge").classList.add("hidden");
  toast("All data cleared");
}

// ── Init ─────────────────────────────────────────────────
(async () => {
  await loadCurrentUser();
  allStudents = (await (await apiFetch("/api/students")).json()) || [];
  loadDashboard();
  renderStudentsTable(allStudents);
  populatePDFSelect();
})();
