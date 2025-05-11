import Cookies from './cookie.js';

export default class API {
    /**
     * Fetches data from the server using the GET method.
     * @param url the URL to fetch data from
     * @param params the parameters to include in the request
     * @returns Promise<any>
     */
    static async get(url: string, params: any) {
        let token = Cookies.get('token');
        if (!token) {
            console.error('No token found in cookies');
            return;
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
    static async post(url: string, body: any) {
        const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + Cookies.get('token')
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
    static async get_noauth(url: string, params: any) {
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
    static async post_noauth(url: string, body: any) {
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
}
