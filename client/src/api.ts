import Cookies from './cookie.js';

export default class API {
    /**
     * Fetches data from the server using the GET method.
     * @param url the URL to fetch data from
     * @param params the parameters to include in the request
     * @returns Promise<any>
     */
    private static async get(url: string, params: any) {
        let token = Cookies.get('token');
        if (!token) {
            throw new Error('No token found in cookies');
        }
        const response = await fetch(url + '?' + new URLSearchParams(params), {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }
        });
        return {
            data: await response.json(),
            status: response.status,
        }
    }

    /**
     * Fetches data from the server using the POST method.
     * @param url the URL to fetch data from
     * @param body the body to include in the request
     * @returns Promise<any>
     */
    private static async post(url: string, body: any) {
        let token = Cookies.get('token');
        if (!token) {
            throw new Error('No token found in cookies');
        }
        const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify(body)
        });
        return {
            data: await response.json(),
            status: response.status,
        }
    }

    /**
     * Fetches data from the server using the PUT method.
     * No token is required for this method.
     * @param url the URL to fetch data from
     * @param body the body to include in the request
     * @returns Promise<any>
     */
    private static async get_noauth(url: string, params: any) {
        const response = await fetch(url + '?' + new URLSearchParams(params), {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        return {
            data: await await response.json(),
            status: response.status,
        }
    }

    /**
     * Fetches data from the server using the POST method.
     * No token is required for this method.
     * @param url the URL to fetch data from
     * @param body the body to include in the request
     * @returns Promise<any>
     */
    private static async post_noauth(url: string, body: any) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
        return {
            data: await response.json(),
            status: response.status,
        }
    }

    public static async register(username: string, password: string, remember: boolean) {
        const {data, status} = await API.post_noauth('/api/register', { username, password, remember });
        if (status === 201) {
            let {token} = data;
            Cookies.set('token', token, 1); // set cookie for 1 hour
            return true;
        }
        else if (status === 500) {
            console.error('Error registering user:', data['message']);
            throw new Error('Error registering user');
        }
        else{
            return false;
        }
    }

    public static async login(username: string, password: string, remember: boolean) {
        const {data, status} = await API.post_noauth('/api/login', { username, password, remember });
        if (status === 200) {
            let {token} = data;
            Cookies.set('token', token, 1); // set cookie for 1 hour
            return true;
        }
        else if (status === 500) {
            console.error('Error logging in user:', data['message']);
            throw new Error('Error logging in user');
        }
        else{
            return false;
        }
    }

    public static async logout() {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return false;
        }
        const {data, status} = await API.post('/api/logout', {});
        Cookies.erase('token');
        if (status === 200) {
            return true;
        }
        else if (status === 500) {
            console.error('Error logging out user:', data['message']);
            throw new Error('Error logging out user');
        }
        else{
            return false;
        }
    }

    public static async change_password(password: string) {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return false;
        }
        const {data, status} = await API.post('/api/user/update_password', { password });
        if (status === 200) {
            return true;
        }
        else if (status === 500) {
            console.error('Error changing password:', data['message']);
            throw new Error('Error changing password');
        }
        else{
            return false;
        }
    }

    public static async delete_account() {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return false;
        }
        const {data, status} = await API.post('/api/delete-user', {});
        if (status === 200) {
            Cookies.erase('token');
            return true;
        }
        else if (status === 500) {
            console.error('Error deleting user:', data['message']);
            throw new Error('Error deleting user');
        }
        else{
            return false;
        }
    }

    public static async get_user_info() {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return false;
        }
        const {data, status} = await API.get('/api/user', {});
        if (status === 200) {
            return data;
        }
        else if (status === 500) {
            console.error('Error getting user info:', data['message']);
            throw new Error('Error getting user info');
        }
        else{
            return false;
        }
    }

    public static async get_server_list() {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return {};
        }
        const {data, status} = await API.get('/api/servers', {});
        if (status === 200) {
            return data;
        }
        else if (status === 500) {
            console.error('Error getting server list:', data['message']);
            throw new Error('Error getting server list');
        }
        else{
            return {};
        }
    }

}
