import ensure_token from "../scripts/ensure_token.js";
import API from "../scripts/api.js";

ensure_token();

const server_name = new URLSearchParams(window.location.search).get("s");
if (!server_name) {
    window.location.href = "/app/dashboard";
}

async function load_data(){
    API.get_server_info(server_name as string).then((server_info) => {
        if (!server_info) {
            window.location.href = "/app/dashboard";
            return;
        }

        const serverNameElement = document.getElementById("server-name") as HTMLHeadingElement;
        serverNameElement.textContent = server_info.name;

        const mcVersionElement = document.getElementById("mc-version") as HTMLSpanElement;
        mcVersionElement.textContent = `Minecraft Version: ${server_info.mc_version}`;

        const modloaderVersionElement = document.getElementById("modloader-version") as HTMLSpanElement;
        modloaderVersionElement.textContent = `Modloader Version: ${server_info.modloader_version}`;

        const ramElement = document.getElementById("ram") as HTMLSpanElement;
        ramElement.textContent = `RAM: ${server_info.ram} MB`;

        const startedAtElement = document.getElementById("started-at") as HTMLSpanElement;
        startedAtElement.textContent = server_info.started_at ? `Started At: ${new Date(server_info.started_at).toLocaleString()}` : "Not Started";

        const runningForElement = document.getElementById("running-for") as HTMLSpanElement;
        if (server_info.started_at) {
            const startedAt = new Date(server_info.started_at);

            function updateRunningFor() {
                const now = new Date();
                const diff = Math.floor((now.getTime() - startedAt.getTime()) / 1000); // in seconds
                const hours = Math.floor(diff / 3600);
                const minutes = Math.floor((diff % 3600) / 60);
                const seconds = diff % 60;
                runningForElement.textContent = `Running For: ${hours}h ${minutes}m ${seconds}s`;
            }

            updateRunningFor();
            setInterval(updateRunningFor, 1000);
        }
        else {
            runningForElement.textContent = "Not Running";
        }

    }).catch((error) => {
        console.error("Error loading server info:", error);
        window.location.href = "/app/dashboard";
    });
}

load_data();
