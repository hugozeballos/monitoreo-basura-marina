console.log("layout.js loaded");
document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("menuToggle");
        console.log("Toggle:", toggle);
    const menu = document.getElementById("navMenu");

    toggle.addEventListener("click", function () {
        console.log("CLICK");
        menu.classList.toggle("open");
    });
});
