/*
 * Frontend logic — plain JS, no build step.
 * Talks ONLY to the backend's REST API (never directly to the storage
 * service). This mirrors the architecture: the frontend doesn't know
 * or care that a separate storage service even exists.
 *
 * IMPORTANT: this is the one line you change when you deploy the
 * backend somewhere other than your own machine (Day 3).
 */

// TODO (Day 3 deployment step): replace this with your deployed backend URL,
// e.g. "https://your-backend.azurewebsites.net" — then redeploy the frontend.
const BACKEND_URL = "http://localhost:5000";

const statusText = document.getElementById("status-text");
const uploadForm = document.getElementById("upload-form");
const ownerInput = document.getElementById("owner-input");
const fileInput = document.getElementById("file-input");
const uploadMessage = document.getElementById("upload-message");
const filesTbody = document.getElementById("files-tbody");
const refreshBtn = document.getElementById("refresh-btn");

// ---- System status check ----
async function checkStatus() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/health`);
    const data = await res.json();

    if (data.status === "ok" && data.storage_service_reachable) {
      statusText.textContent = "Connected — backend and storage service are both online.";
      statusText.className = "status-ok";
    } else if (data.status === "ok") {
      statusText.textContent = "Backend is online, but it cannot reach the storage service.";
      statusText.className = "status-bad";
    }
  } catch (err) {
    statusText.textContent = "Cannot reach the backend at " + BACKEND_URL;
    statusText.className = "status-bad";
  }
}

// ---- Load and render file list ----
async function loadFiles() {
  filesTbody.innerHTML = "<tr><td colspan='5'>Loading…</td></tr>";
  try {
    const res = await fetch(`${BACKEND_URL}/api/files`);
    const data = await res.json();

    if (!data.files || data.files.length === 0) {
      filesTbody.innerHTML = "<tr><td colspan='5'>No files uploaded yet.</td></tr>";
      return;
    }

    filesTbody.innerHTML = "";
    data.files.forEach((f) => {
      const row = document.createElement("tr");

      const sizeKb = (f.size_bytes / 1024).toFixed(1) + " KB";
      const uploadedAt = new Date(f.upload_time).toLocaleString();

      row.innerHTML = `
        <td>${escapeHtml(f.original_name)}</td>
        <td>${escapeHtml(f.owner || "")}</td>
        <td>${sizeKb}</td>
        <td>${uploadedAt}</td>
        <td><button class="download-btn" data-id="${f.id}" data-name="${escapeHtml(f.original_name)}">Download</button></td>
      `;
      filesTbody.appendChild(row);
    });

    document.querySelectorAll(".download-btn").forEach((btn) => {
      btn.addEventListener("click", () => downloadFile(btn.dataset.id, btn.dataset.name));
    });
  } catch (err) {
    filesTbody.innerHTML = "<tr><td colspan='5'>Could not load files — is the backend running?</td></tr>";
  }
}

// ---- Upload handler ----
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  uploadMessage.textContent = "Uploading…";

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("owner", ownerInput.value);

  try {
    const res = await fetch(`${BACKEND_URL}/api/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (res.ok) {
      uploadMessage.textContent = `Uploaded "${data.file.original_name}" successfully.`;
      uploadForm.reset();
      loadFiles();
    } else {
      uploadMessage.textContent = "Upload failed: " + (data.error || "unknown error");
    }
  } catch (err) {
    uploadMessage.textContent = "Upload failed — is the backend running?";
  }
});

// ---- Download handler ----
async function downloadFile(fileId, fileName) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/download/${fileId}`);
    if (!res.ok) {
      alert("Download failed.");
      return;
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert("Download failed — is the backend running?");
  }
}

// ---- Utility: prevent basic HTML injection in file/owner names ----
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

refreshBtn.addEventListener("click", loadFiles);

// Initial load
checkStatus();
loadFiles();