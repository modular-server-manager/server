import ensure_token from "./ensure_token.js";
import API from "./api.js";
import Cookies from "./cookie.js";

ensure_token();

const disconnectBtn = document.getElementById('disconnect') as HTMLButtonElement;


disconnectBtn.addEventListener('click', async () => {
    const token = Cookies.get('token');
    if (!token) {
        window.location.href = '/app/dashboard';
        return;
    }
    const response = await API.post('/api/logout', { token });
    if (response.status === 200) {
        Cookies.erase('token');
        window.location.href = '/app/dashboard';
    } else {
        console.error('Failed to disconnect:', response);
    }
});