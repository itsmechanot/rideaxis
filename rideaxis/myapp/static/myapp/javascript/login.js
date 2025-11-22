document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('container');
    const registerBtn = document.getElementById('register');
    const loginBtn = document.getElementById('login');

    // Toggle between forms
    registerBtn.addEventListener('click', (e) => {
        e.preventDefault();
        container.classList.add('active');
    });

    loginBtn.addEventListener('click', (e) => {
        e.preventDefault();
        container.classList.remove('active');
    });

    // Handle popup
    const overlay = document.getElementById('popup-overlay');
    if (!overlay) return;

    const card = overlay.querySelector('.popup-card');
    const titleEl = document.getElementById('popup-title');
    const textEl = document.getElementById('popup-text');
    const iconEl = document.getElementById('popup-icon');
    const btn = document.getElementById('popup-action');

    const isError =
        card.classList.contains('popup-error') ||
        card.className.includes('error') ||
        card.className.includes('popup-error');

    const isSuccess =
        card.classList.contains('popup-success') ||
        card.className.includes('success') ||
        card.className.includes('popup-success');

    // Set icon and title based on status
    if (isError) {
        titleEl.textContent = 'Something went wrong';
        iconEl.textContent = '⚠';
    } else if (isSuccess) {
        titleEl.textContent = 'Success!';
        iconEl.textContent = '✔';
    } else {
        titleEl.textContent = 'Notice';
        iconEl.textContent = 'ℹ';
    }

    document.body.classList.add('blurred');

    btn.addEventListener('click', () => {
        // Close popup animation
        card.style.transform = 'scale(0.96)';
        card.style.opacity = '0';
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.remove();
            document.body.classList.remove('blurred');
        }, 220);

        // Redirect only on success
        if (isSuccess) {
            setTimeout(() => {
                window.location.href = '/profile';
            }, 250);
        }
    });
});
