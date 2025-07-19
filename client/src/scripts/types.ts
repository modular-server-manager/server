enum AccessLevel {
    USER = 0,        // Global: Can see servers status
    ADMIN = 1,       // Global: Can start/stop servers, see logs, manage settings
    OPERATOR = 2,    // Global: Can manage users and create and delete servers
}

function AccessLevelFromString(level: string): AccessLevel {
    switch (level.toLowerCase()) {
        case "user":
            return AccessLevel.USER;
        case "admin":
            return AccessLevel.ADMIN;
        case "operator":
            return AccessLevel.OPERATOR;
        default:
            throw new Error(`Unknown access level: ${level}`);
    }
};

interface User {
    username: string;
    access_level: AccessLevel;
    registered_at: Date;
    last_login: Date;
}

interface ServerInfo {
    name: string;
    type: string;
    path: string;
    autostart: boolean;
    mc_version: string;
    modloader_version: string;
    ram: number;
}

export { AccessLevel, User, ServerInfo, AccessLevelFromString };