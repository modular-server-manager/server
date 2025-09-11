import Cookies from '../scripts/cookie.js';
import API from '../scripts/api.js';

// Check if the user is already logged in
const token = Cookies.get('token');
if (token) {
    // Redirect to the dashboard if the user is already logged in
    window.location.href = '/app/dashboard';
}

const loginTab = document.getElementById('login-tab') as HTMLButtonElement;
const registerTab = document.getElementById('register-tab') as HTMLButtonElement;
const authForm = document.getElementById('auth-form') as HTMLFormElement;
const submitBtn = document.getElementById('submit-btn') as HTMLButtonElement;
const authMessage = document.getElementById('auth-message') as HTMLDivElement;
const confirmPasswordGroup = document.getElementById('confirm-password-group') as HTMLDivElement;
const confirmPasswordInput = document.getElementById('confirm-password') as HTMLInputElement;



let mode: 'login' | 'register' = 'login';

function setMode(newMode: 'login' | 'register') {
    mode = newMode;
    if (mode === 'login') {
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
        submitBtn.textContent = 'Login';
        confirmPasswordGroup.style.display = 'none';
    } else {
        loginTab.classList.remove('active');
        registerTab.classList.add('active');
        submitBtn.textContent = 'Register';
        confirmPasswordGroup.style.display = 'flex';
    }
    authMessage.textContent = '';
}

loginTab.addEventListener('click', () => setMode('login'));
registerTab.addEventListener('click', () => setMode('register'));

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authMessage.textContent = '';
    const username = (document.getElementById('username') as HTMLInputElement).value;
    const password = (document.getElementById('password') as HTMLInputElement).value;
    const confirmPassword = confirmPasswordInput.value;

    if (mode === 'register') {
        if (!confirmPassword) {
            authMessage.style.color = 'red';
            authMessage.textContent = 'Please confirm your password.';
            return;
        }
        if (password !== confirmPassword) {
            authMessage.style.color = 'red';
            authMessage.textContent = 'Passwords do not match.';
            return;
        }
    }

    const method = mode === 'login' ? API.login : API.register;

    try {
        const success = await method(username, password, true);

        if (success) {
            window.location.href = '/app/dashboard';
        }
        else if (mode === 'register') {
            authMessage.style.color = 'red';
            authMessage.textContent = 'Registration failed. Please try again.';
        }
        else {
            authMessage.style.color = 'red';
            authMessage.textContent = 'Invalid username or password.';
        }

    } catch (err) {
        authMessage.style.color = 'red';
        authMessage.textContent = 'An error occurred. Please try again later.';
    }
});
