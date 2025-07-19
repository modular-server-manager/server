import ensure_token from "../scripts/ensure_token.js";
import API from "../scripts/api.js";

ensure_token();

const server_name = new URLSearchParams(window.location.search).get("s");
if (!server_name) {
    window.location.href = "/app/dashboard";
}

async function load_data(){

}

load_data();
