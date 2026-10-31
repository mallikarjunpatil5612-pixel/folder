/**
 * Home Rental Management System - Client Side JavaScript
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Menu Toggle
  const mobileToggle = document.querySelector(".mobile-toggle");
  const navMenu = document.querySelector(".nav-menu");
  if (mobileToggle && navMenu) {
    mobileToggle.addEventListener("click", function () {
      navMenu.classList.toggle("open");
    });
  }

  // 2. Flash Message Auto-Dismiss
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.opacity = "0";
      alert.style.transition = "opacity 0.4s ease";
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

  // 3. Favourites AJAX Toggle
  const favButtons = document.querySelectorAll(".fav-btn");
  favButtons.forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      const propId = this.dataset.propertyId;
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");

      if (!propId) return;

      fetch(`/api/favourite/toggle/${propId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken || "",
          "X-Requested-With": "XMLHttpRequest"
        }
      })
        .then((res) => {
          if (res.status === 401 || res.redirected) {
            window.location.href = "/login";
            return null;
          }
          return res.json();
        })
        .then((data) => {
          if (data && data.success) {
            const icon = this.querySelector("i");
            if (data.is_favourite) {
              this.classList.add("active");
              icon.classList.remove("fa-regular");
              icon.classList.add("fa-solid");
            } else {
              this.classList.remove("active");
              icon.classList.remove("fa-solid");
              icon.classList.add("fa-regular");
            }
          } else if (data && data.error) {
            alert(data.error);
          }
        })
        .catch((err) => console.error("Error toggling favourite:", err));
    });
  });

  // 4. Image Upload File Preview
  const photoInput = document.getElementById("photo-input");
  const previewContainer = document.getElementById("photo-preview");
  if (photoInput && previewContainer) {
    photoInput.addEventListener("change", function () {
      previewContainer.innerHTML = "";
      const files = Array.from(this.files);
      files.forEach((file) => {
        if (file.type.startsWith("image/")) {
          const reader = new FileReader();
          reader.onload = function (e) {
            const thumb = document.createElement("div");
            thumb.style.width = "80px";
            thumb.style.height = "80px";
            thumb.style.borderRadius = "8px";
            thumb.style.overflow = "hidden";
            thumb.style.border = "1px solid #e2e8f0";
            thumb.innerHTML = `<img src="${e.target.result}" style="width:100%;height:100%;object-fit:cover;">`;
            previewContainer.appendChild(thumb);
          };
          reader.readAsDataURL(file);
        }
      });
    });
  }
});

// Modal helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = "flex";
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = "none";
  }
}
