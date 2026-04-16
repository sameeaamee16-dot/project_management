function openModal(selector) {
  closeAllModals();
  const modal = document.querySelector(selector);
  if (modal) {
    modal.classList.remove("hidden");
    document.body.classList.add("modal-open");
  }
}

function closeModal(modal) {
  modal.classList.add("hidden");
  if (!document.querySelector(".modal:not(.hidden)")) {
    document.body.classList.remove("modal-open");
  }
}

function closeAllModals() {
  document.querySelectorAll(".modal").forEach((modal) => {
    modal.classList.add("hidden");
  });
  document.body.classList.remove("modal-open");
}

function initializeModals() {
  document.querySelectorAll("[data-modal-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.getAttribute("data-modal-target");
      openModal(target);

      if (target === "#editProjectModal") {
        const form = document.getElementById("editProjectForm");
        form.action = `/admin/projects/${button.dataset.projectId}/edit`;
        document.getElementById("editProjectName").value = button.dataset.projectName || "";
        document.getElementById("editProjectDescription").value =
          button.dataset.projectDescription || "";
        document.getElementById("editProjectStart").value = button.dataset.projectStart || "";
        document.getElementById("editProjectEnd").value = button.dataset.projectEnd || "";
      }

      if (target === "#editTaskModal") {
        const form = document.getElementById("editTaskForm");
        form.action = `/admin/tasks/${button.dataset.taskId}/edit`;
        document.getElementById("editTaskTitle").value = button.dataset.taskTitle || "";
        document.getElementById("editTaskDescription").value = button.dataset.taskDescription || "";
        document.getElementById("editTaskProject").value = button.dataset.taskProject || "";
        document.getElementById("editTaskUser").value = button.dataset.taskUser || "";
        document.getElementById("editTaskSeverity").value = button.dataset.taskSeverity || "Low";
        document.getElementById("editTaskStatus").value = button.dataset.taskStatus || "Not Started";
        document.getElementById("editTaskStart").value = button.dataset.taskStart || "";
        document.getElementById("editTaskDue").value = button.dataset.taskDue || "";
      }
    });
  });

  document.querySelectorAll(".close-modal").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = button.closest(".modal");
      if (modal) closeModal(modal);
    });
  });

  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeModal(modal);
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAllModals();
    }
  });
}

async function markNotificationAsRead(id) {
  await fetch(`/api/notifications/${id}/read`, { method: "POST" });
}

function renderNotifications(items) {
  const list = document.getElementById("notifList");
  const countNode = document.getElementById("notifCount");
  if (!list || !countNode) return;

  countNode.textContent = String(items.length);
  if (!items.length) {
    list.innerHTML = '<li class="muted">No new notifications.</li>';
    return;
  }

  list.innerHTML = items
    .map(
      (item) => `
      <li data-id="${item.id}">
        <span class="notif-type ${item.type}">${item.type.toUpperCase()}</span>
        <p>${item.message}</p>
        <small>${item.created_at}</small>
      </li>`
    )
    .join("");

  list.querySelectorAll("li[data-id]").forEach((li) => {
    li.addEventListener("click", async () => {
      await markNotificationAsRead(li.dataset.id);
      li.remove();
      const newCount = list.querySelectorAll("li[data-id]").length;
      countNode.textContent = String(newCount);
      if (!newCount) {
        list.innerHTML = '<li class="muted">No new notifications.</li>';
      }
    });
  });
}

async function pollNotifications() {
  try {
    const response = await fetch("/api/notifications/poll");
    if (!response.ok) return;
    const payload = await response.json();
    renderNotifications(payload.notifications || []);
  } catch (error) {
    console.error("Notification polling failed", error);
  }
}

function initializeNotifications() {
  const toggle = document.getElementById("notifToggle");
  const dropdown = document.getElementById("notifDropdown");
  const markAll = document.getElementById("markAllReadBtn");

  if (!toggle || !dropdown) return;

  toggle.addEventListener("click", () => {
    dropdown.classList.toggle("hidden");
  });

  if (markAll) {
    markAll.addEventListener("click", async () => {
      await fetch("/api/notifications/read-all", { method: "POST" });
      renderNotifications([]);
    });
  }

  pollNotifications();
  setInterval(pollNotifications, 20000);
}

document.addEventListener("DOMContentLoaded", () => {
  initializeModals();
  initializeNotifications();
});
