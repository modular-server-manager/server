import ensure_token from "./ensure_token.js";
import API from "./api.js";

ensure_token();

const server_list = document.getElementById("server-list") as HTMLUListElement;

// fill the server list with the servers
async function fill_server_list() {
    const servers = await API.get_server_list();
    /*
    {
        "name": server.name,
        "mc_version": str(server.mc_version),
        "forge_version": str(server.forge_version),
        "status": server.status.name,
        "path": server.path
    }
    */
    if (servers) {
        for (const server of servers) {
            const row = document.createElement("button");
            row.className = "server";
            let color = "green";
            if (server.status === "STOPPED") {
                color = "red";
            } else if (server.status === "STARTING" || server.status === "STOPPING") {
                color = "yellow";
            }
            row.innerHTML = `
                <div class="server-name" style="color: ${color}">${server.name}</div>
                <div class="server-mc-version">minecraft: ${server.mc_version}</div>
                <div class="server-forge-version">forge: ${server.forge_version}</div>
                <div class="server-status" style="color: ${color}">${server.status}</div>
                `;
            row.addEventListener("click", () => {
                // open the server page
                window.location.href = `/app/server?s=${server.name}`;
            });
            server_list.appendChild(row);
        }
    }
}

fill_server_list();
