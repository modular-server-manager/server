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
        mcVersionElement.textContent = server_info.mc_version;

        
        const modloaderVersionElement = document.getElementById("modloader-version") as HTMLSpanElement;
        if (server_info.type === "vanilla") {
            modloaderVersionElement.textContent = "Vanilla";
        }
        else {
            modloaderVersionElement.textContent = `${server_info.type} ${server_info.modloader_version}`;
        }

        const ramElement = document.getElementById("ram") as HTMLSpanElement;
        ramElement.textContent = `${server_info.ram}`;

        const startedAtElement = document.getElementById("started-at") as HTMLSpanElement;
        startedAtElement.textContent = server_info.started_at ? `${new Date(server_info.started_at).toLocaleString()}` : "N/A";

        const runningForElement = document.getElementById("running-for") as HTMLSpanElement;
        if (server_info.started_at) {
            const startedAt = new Date(server_info.started_at);

            function updateRunningFor() {
                const now = new Date();
                const diff = Math.floor((now.getTime() - startedAt.getTime()) / 1000); // in seconds
                const hours = Math.floor(diff / 3600);
                const minutes = Math.floor((diff % 3600) / 60);
                const seconds = diff % 60;
                runningForElement.textContent = `${hours}h ${minutes}m ${seconds}s`;
            }

            updateRunningFor();
            setInterval(updateRunningFor, 1000);
        }
        else {
            runningForElement.textContent = "Server is not running";
        }

        const startServerButton = document.getElementById("start-server") as HTMLButtonElement;
        if (server_info.started_at) {
            startServerButton.disabled = true;
            startServerButton.textContent = "Server is running";
        } else {
            startServerButton.disabled = false;
            startServerButton.textContent = "Start Server";
        }
        startServerButton.addEventListener("click", () => {
            API.start_server(server_name as string).then(() => {
                window.location.reload();
            }).catch((error) => {
                console.error("Error starting server:", error);
                alert("Failed to start the server. Check the console for details.");
            });
        });

        const stopServerButton = document.getElementById("stop-server") as HTMLButtonElement;
        if (!server_info.started_at) {
            stopServerButton.disabled = true;
            stopServerButton.textContent = "Server is not running";
        } else {
            stopServerButton.disabled = false;
            stopServerButton.textContent = "Stop Server";
        }
        stopServerButton.addEventListener("click", () => {
            API.stop_server(server_name as string).then(() => {
                window.location.reload();
            }).catch((error) => {
                console.error("Error stopping server:", error);
                alert("Failed to stop the server. Check the console for details.");
            });
        });

        const restartServerButton = document.getElementById("restart-server") as HTMLButtonElement;
        if (!server_info.started_at) {
            restartServerButton.disabled = true;
            restartServerButton.textContent = "Server is not running";
        } else {
            restartServerButton.disabled = false;
            restartServerButton.textContent = "Restart Server";
        }
        restartServerButton.addEventListener("click", () => {
            API.restart_server(server_name as string).then(() => {
                window.location.reload();
            }).catch((error) => {
                console.error("Error restarting server:", error);
                alert("Failed to restart the server. Check the console for details.");
            });
        });

    }).catch((error) => {
        console.error("Error loading server info:", error);
        window.location.href = "/app/dashboard";
    });
}

load_data();
