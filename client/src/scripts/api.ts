import Cookies from './cookie.js';
import { AccessLevel, User, ServerInfo, AccessLevelFromString } from './types.js';


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
            data: await response.json(),
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
            return null;
        }
        const {data, status} = await API.get('/api/user', {});
        if (status === 200) {
            data['access_level'] = AccessLevelFromString(data['access_level']);
            return data as User;
        }
        else if (status === 500) {
            console.error('Error getting user info:', data['message']);
            throw new Error('Error getting user info');
        }
        else{
            return null;
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

    public static async get_mc_server_dirs() {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return [];
        }
        const {data, status} = await API.get('/api/list_mc_server_dirs', {});
        if (status === 200) {
            return data["dirs"] as string[];
        }
        else if (status === 500) {
            console.error('Error getting Minecraft server directories:', data['message']);
            throw new Error('Error getting Minecraft server directories');
        }
        else{
            return [];
        }
    }

    public static async create_server(server_info: ServerInfo) {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return false;
        }
        const {data, status} = await API.post('/api/create_server', server_info);
        if (status === 201) {
            return true;
        }
        else if (status === 500) {
            console.error('Error creating server:', data['message']);
            throw new Error('Error creating server');
        }
        else{
            return false;
        }
    }

    public static async get_mc_versions() {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return [];
        }
        const {data, status} = await API.get('/api/mc_versions', {});
        if (status === 200) {
            return data["versions"] as string[];
        }
        else if (status === 500) {
            console.error('Error getting Minecraft versions:', data['message']);
            throw new Error('Error getting Minecraft versions');
        }
        else{
            return [];
        }
    }

    public static async get_forge_versions(mc_version: string) {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return [];
        }
        const {data, status} = await API.get(`/api/forge_versions/${mc_version}`, {});
        if (status === 200) {
            return data["versions"] as string[];
        }
        else if (status === 500) {
            console.error('Error getting Forge versions:', data['message']);
            throw new Error('Error getting Forge versions');
        }
        else{
            return [];
        }
    }

    public static async get_server_info(server_name: string) {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return null;
        }
        const {data, status} = await API.get(`/api/server/${server_name}`, {});
        if (status === 200) {
            return data as ServerInfo;
        }
        else if (status === 500) {
            console.error('Error getting server info:', data['message']);
            throw new Error('Error getting server info');
        }
        else{
            return null;
        }
    }

    public static async start_server(server_name: string) {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return false;
        }
        const {data, status} = await API.post(`/api/start_server/${server_name}`, {});
        if (status === 200) {
            return true;
        }
        else if (status === 500) {
            console.error('Error starting server:', data['message']);
            throw new Error('Error starting server');
        }
        else{
            return false;
        }
    }

    public static async stop_server(server_name: string) {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return false;
        }
        const {data, status} = await API.post(`/api/stop_server/${server_name}`, {});
        if (status === 200) {
            return true;
        }
        else if (status === 500) {
            console.error('Error stopping server:', data['message']);
            throw new Error('Error stopping server');
        }
        else{
            return false;
        }
    }

    public static async restart_server(server_name: string) {
        if (!Cookies.has('token')) {
            console.error('No token found in cookies');
            return false;
        }
        const {data, status} = await API.post(`/api/restart_server/${server_name}`, {});
        if (status === 200) {
            return true;
        }
        else if (status === 500) {
            console.error('Error restarting server:', data['message']);
            throw new Error('Error restarting server');
        }
        else{
            return false;
        }
    }

}
