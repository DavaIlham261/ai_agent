document.addEventListener('DOMContentLoaded', () => {
    const greeting = document.getElementById('greeting');
    greeting.addEventListener('click', () => {
        greeting.textContent = 'Halo, dunia!';
    });
});
