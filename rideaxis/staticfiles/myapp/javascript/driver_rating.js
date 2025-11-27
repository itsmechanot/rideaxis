document.addEventListener("DOMContentLoaded", () => {
  const rateBtn = document.getElementById("rateDriverBtn");
  const ratingPanel = document.getElementById("ratingPanel");
  const stars = document.querySelectorAll(".stars i");
  const message = document.getElementById("ratingMessage");
  const actionButtons = document.querySelector(".action-buttons");

  // Toggle rating panel visibility + move button left
  rateBtn.addEventListener("click", () => {
    const isActive = actionButtons.classList.toggle("active");
    ratingPanel.classList.toggle("active", isActive);
  });

  // Function to send rating to server
  const sendRating = (value) => {
    fetch(rateDriverUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({ rating: value }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          message.textContent = `${data.message} (Avg: ${data.average_rating}★)`;
          message.style.color = "green";

          // Disable stars after rating
          stars.forEach((s) => s.classList.add("disabled"));
        } else {
          message.textContent = data.error || "Something went wrong!";
          message.style.color = "red";
        }
      })
      .catch(() => {
        message.textContent = "Network error!";
        message.style.color = "red";
      });
  };

  // Handle star clicks
  stars.forEach((star) => {
    star.addEventListener("click", function () {
      if (this.classList.contains("disabled")) return; // prevent re-rating

      const value = this.getAttribute("data-value");

      // Highlight stars up to the selected one
      stars.forEach((s) => s.classList.remove("selected"));
      stars.forEach((s) => {
        if (parseInt(s.dataset.value) <= parseInt(value)) {
          s.classList.add("selected");
        }
      });

      // Send rating to backend
      sendRating(value);
    });
  });
});
