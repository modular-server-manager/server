import API from "../scripts/api.js";
import Cookies from "../scripts/cookie.js";

const disconnectBtn = document.getElementById('disconnect') as HTMLButtonElement;

disconnectBtn.addEventListener('click', async () => {
    const token = Cookies.get('token');
    if (!token) {
        window.location.reload();
        return;
    }
    await API.logout();
    window.location.reload();
});
