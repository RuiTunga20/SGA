document.addEventListener('DOMContentLoaded', function () {
    // ==========================================================
    // LÓGICA DO MENU HAMBURGER
    // ==========================================================
    const hamburgerButton = document.getElementById('hamburger-menu');
    const mainNav = document.getElementById('main-nav');
    if (hamburgerButton && mainNav) {
        hamburgerButton.addEventListener('click', function () {
            mainNav.classList.toggle('is-open');
        });
    }


});
