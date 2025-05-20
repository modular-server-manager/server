import ensure_token from "./ensure_token.js";
import API from "./api.js";

ensure_token();

const server_name = new URLSearchParams(window.location.search).get("s");
if (!server_name) {
    window.location.href = "/app/dashboard";
}

async function load_data(){

}

load_data();
