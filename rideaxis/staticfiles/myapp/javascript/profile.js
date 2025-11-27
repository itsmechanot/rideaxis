document.addEventListener("DOMContentLoaded", () => {
  const seats = document.querySelectorAll(".seat");

  seats.forEach((seat) => {
    seat.addEventListener("click", () => {
      const seatId = seat.dataset.seatId;
      const currentStatus = seat.classList.contains("available") ? "available" : "taken";
      const newStatus = currentStatus === "available" ? "taken" : "available";

      showPopup(`Change this seat to "${newStatus}"?`, "info", [
        {
          label: "Yes",
          action: () => updateSeatStatus(seatId, newStatus, seat),
        },
        {
          label: "Cancel",
        },
      ]);
    });
  });

  function updateSeatStatus(seatId, newStatus, seat) {
    fetch("/update-seat-status/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        seat_id: seatId,
        status: newStatus,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          seat.classList.remove("available", "taken");
          seat.classList.add(newStatus);
          const seatCounter = document.querySelector("#seat-counter");
          if (seatCounter) seatCounter.textContent = data.available_count;
          showPopup("Seat updated successfully!", "success");
        } else {
          showPopup("Error: " + data.error, "error");
        }
      })
      .catch(() => showPopup("An error occurred while updating the seat.", "error"));
  }

  // ✅ Reusable popup function
  function showPopup(message, type = "info", buttons = []) {
    const container = document.getElementById("popup-container");
    const popup = document.createElement("div");
    popup.classList.add("popup", type);

    const msg = document.createElement("div");
    msg.textContent = message;
    popup.appendChild(msg);

    if (buttons.length > 0) {
      const btnContainer = document.createElement("div");
      btnContainer.style.marginTop = "8px";
      btnContainer.style.display = "flex";
      btnContainer.style.gap = "8px";

      buttons.forEach((btn) => {
        const b = document.createElement("button");
        b.textContent = btn.label;
        b.style.background = "var(--primary-color)";
        b.style.color = "#fff";
        b.style.border = "none";
        b.style.borderRadius = "8px";
        b.style.padding = "5px 10px";
        b.style.cursor = "pointer";
        b.addEventListener("click", () => {
          popup.remove();
          if (btn.action) btn.action();
        });
        btnContainer.appendChild(b);
      });

      popup.appendChild(btnContainer);
    } else {
      setTimeout(() => popup.remove(), 3000);
    }

    container.appendChild(popup);
    setTimeout(() => popup.remove(), 4000);
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + "=")) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
});

function openLogoutModal(event) {
    event.preventDefault();
    const modal = document.getElementById('logoutModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeLogoutModal() {
    const modal = document.getElementById('logoutModal');
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
}

// Close modal when clicking outside
document.getElementById('logoutModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeLogoutModal();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeLogoutModal();
    }
});
