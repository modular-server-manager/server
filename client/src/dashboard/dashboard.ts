import ensure_token from "../scripts/ensure_token.js";
import API from "../scripts/api.js";
import { AccessLevel, ServerInfo } from "../scripts/types.js";

ensure_token();

const server_list = document.getElementById("server-list") as HTMLUListElement;


const status_colors: { [key: string]: string } = {
    "STOPPED" : "darkgray",
    "STARTING" : "orange",
    "RUNNING" : "lightgreen",
    "STOPPING" : "orange",
    "ERROR" : "red",
    "UNKNOWN" : "darkgray"
};

async function get_user_access_level(): Promise<AccessLevel> {
    const user = await API.get_user_info();
    if (user) {
        return user.access_level;
    }
    return AccessLevel.USER; // Default access level if user not found
}


// fill the server list with the servers
async function fill_server_list() {
    // clear the server list
    server_list.innerHTML = "";
    const servers = await API.get_server_list();

    if (servers) {
        for (const server of servers) {
            const row = document.createElement("button");
            row.className = "server";
            let color : string = status_colors[server.status.toUpperCase()] || "darkgray";
            let online_text : string = server.status.charAt(0).toUpperCase() + server.status.slice(1).toLowerCase();

            row.innerHTML = `
                <div class="server-name" style="color: ${color}">${server.name}</div>
                <div class="server-mc-version">minecraft ${server.mc_version}</div>
            `;

            if (server.type != "vanilla") {
                row.innerHTML += `
                    <div class="server-modloader-version">${server.type} ${server.modloader_version}</div>
                `;
            }
            else {
                row.innerHTML += `
                    <div class="server-modloader-version"></div>
                `;
            }
            row.innerHTML +=
            `
                <div class="server-status" style="color: ${color}">${online_text}</div>
            `;
            row.addEventListener("click", () => {
                // open the server page
                window.location.href = `/app/server?s=${server.name}`;
            });
            server_list.appendChild(row);
        }
    }
}


function clear_select_options(selectElement: HTMLSelectElement) {
    selectElement.innerHTML = "<option value='void'></option>";
}

async function update_modloader_versions(mc_version : string) {
    const modloaderVersionInput = document.getElementById('modloader-version') as HTMLSelectElement;
    const modloaderVersions = await API.get_forge_versions(mc_version);
    modloaderVersionInput.innerHTML = modloaderVersions.map(version => `<option value="${version}">${version}</option>`).join('');
}

async function init_create_server_form() {
    const serverType = document.getElementById('server-type') as HTMLSelectElement;
    const modloaderGroup = document.getElementById('modloader-version-group') as HTMLDivElement;
    serverType.addEventListener('change', function() {
        if (serverType.value !== 'vanilla') {
            modloaderGroup.style.display = '';
        } else {
            modloaderGroup.style.display = 'none';
        }
    });
    // Trigger on page load
    if (serverType.value !== 'vanilla') {
        modloaderGroup.style.display = '';
    }

    const mcVersionInput = document.getElementById('mc-version') as HTMLSelectElement;
    const mcVersions = await API.get_mc_versions();
    mcVersionInput.innerHTML = mcVersions.map(version => `<option value="${version}">${version}</option>`).join('');
    mcVersionInput.addEventListener('change', async function() {
        const selectedVersion = mcVersionInput.value;
        if (selectedVersion && selectedVersion !== 'void') {
            await update_modloader_versions(selectedVersion);
        } else {
            clear_select_options(document.getElementById('modloader-version') as HTMLSelectElement);
        }
    });

    const serverPathInput = document.getElementById('server-path') as HTMLSelectElement;
    const serverPaths = await API.get_mc_server_dirs();
    serverPathInput.innerHTML = serverPaths.map(path => `<option value="${path}">${path}</option>`).join('');
}


function show_create_server_form() {
    const create_server_form = document.getElementById("create-server-form") as HTMLDivElement;
    create_server_form.style.display = "block";
}
function hide_create_server_form() {
    const create_server_form = document.getElementById("create-server-form") as HTMLDivElement;
    create_server_form.style.display = "none";
}

async function on_create_server_button() {
    const access_level = await get_user_access_level();
    if (access_level >= AccessLevel.OPERATOR) {
        show_create_server_form();
        const create_server_form = document.getElementById("create-server-form") as HTMLFormElement;
        create_server_form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const server_name = (document.getElementById("server-name") as HTMLInputElement).value;
            const server_type = (document.getElementById("server-type") as HTMLSelectElement).value;
            const server_path = (document.getElementById("server-path") as HTMLInputElement).value;
            const autostart = (document.getElementById("autostart") as HTMLInputElement).checked;
            const ram = (document.getElementById("ram") as HTMLInputElement).value;
            const mc_version = (document.getElementById("mc-version") as HTMLInputElement).value;
            const modloader_version = (document.getElementById("modloader-version") as HTMLInputElement).value;

            const server_info: ServerInfo = {
                name: server_name,
                type: server_type,
                path: server_path,
                autostart: autostart,
                ram: parseInt(ram, 10), // Convert to integer
                mc_version: mc_version,
                modloader_version: modloader_version
            };
            const success = await API.create_server(server_info);
            if (success) {
                hide_create_server_form();
                fill_server_list(); // Refresh the server list
            }
        });
    }
    else {
        alert("You do not have permission to create a server.");
    }
}

async function init_misc() {
    const userInfo = await API.get_user_info();
    if (userInfo && userInfo.access_level >= AccessLevel.OPERATOR) {
        const createServerButton = document.createElement("button");
        createServerButton.id = "create-server-button";
        createServerButton.className = "button";
        createServerButton.innerText = "Create Server";
        createServerButton.addEventListener("click", on_create_server_button);
        const main = document.querySelector("main") as HTMLDivElement;
        main.appendChild(createServerButton);

        const createServerCancelButton = document.getElementById("create-server-cancel") as HTMLButtonElement;
        createServerCancelButton.addEventListener("click", hide_create_server_form);
    }
    else{
        console.log(`User does not have permission to create a server (access level: ${userInfo?.access_level.valueOf()} < AccessLevel.OPERATOR (${AccessLevel.OPERATOR.valueOf()})).`);
    }
}


document.addEventListener("DOMContentLoaded", async () => {
    await init_create_server_form();
    await fill_server_list();
    await init_misc();
});
