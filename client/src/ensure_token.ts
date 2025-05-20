import Cookies from "./cookie.js";


export default function ensure_token() {
    const token = Cookies.get('token');
    if (!token) {
        window.location.href = '/app/login';
    }
    else{
        console.info("using token: ", token);
    }
}
