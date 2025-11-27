document.addEventListener('DOMContentLoaded', function() {
  const navbarToggle = document.querySelector('.navbar-toggle');
  const navbarMenu = document.querySelector('.navbar-menu');
  const navLinks = document.querySelectorAll('.navbar-menu li a');
  const bars = document.querySelectorAll('.bar');

  if (!navbarToggle) return;

  navbarToggle.addEventListener('click', () => {
    navbarMenu.classList.toggle('active');
    animateBars();
  });

  function animateBars() {
    bars[0].style.transform = navbarMenu.classList.contains('active') ? 'rotate(45deg) translate(8px, 8px)' : '';
    bars[1].style.opacity = navbarMenu.classList.contains('active') ? '0' : '1';
    bars[2].style.transform = navbarMenu.classList.contains('active') ? 'rotate(-45deg) translate(7px, -7px)' : '';
  }

  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      if (!link.closest('.dropdown')) {
        navbarMenu.classList.remove('active');
        animateBars();
      }
    });
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.navbar-menu') && !e.target.closest('.navbar-toggle')) {
      navbarMenu.classList.remove('active');
      animateBars();
    }
  });
});

function toggleMobileProfile(e) {
  e.preventDefault();
  const menu = e.target.closest('.mobile-dropdown').querySelector('.mobile-profile-menu');
  menu.classList.toggle('show');
}
