document.addEventListener("DOMContentLoaded", function() {
  const userDropdown = document.querySelector(".user-icon-link");
  const dropdownMenu = userDropdown.nextElementSibling;

  userDropdown.addEventListener("click", function(e) {
    e.preventDefault();
    dropdownMenu.classList.toggle("show");
  });

  // Close if clicking outside
  document.addEventListener("click", function(e) {
    if (!userDropdown.parentElement.contains(e.target)) {
      dropdownMenu.classList.remove("show");
    }
  });
});
