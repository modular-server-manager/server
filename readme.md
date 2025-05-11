# Forge server manager

## API endpoints

### Authentication

- **POST `/api/login`**  
  Authenticate a user.  
  **Access:** Public  
  **Body:** `{ "username": string, "password": string, "remember": boolean }`  
  **Returns:** `{ "token": string }` on success.

- **POST `/api/register`**  
  Register a new user.  
  **Access:** Public  
  **Body:** `{ "username": string, "password": string, "remember": boolean }`  
  **Returns:** `{ "token": string }` on success.

- **POST `/api/logout`**  
  Logout the current user.  
  **Access:** User (requires Authorization header)  
  **Headers:** `Authorization: Bearer <token>`  
  **Returns:** `{ "message": "Logged out" }`

- **GET `/api/user`**  
  Get information about the current user.  
  **Access:** User (requires Authorization header)  
  **Headers:** `Authorization: Bearer <token>`  
  **Returns:** `{ "username": string, "access_level": string }`

---

### Server Management

- **GET `/api/mc_versions`**  
  List available Minecraft versions.  
  **Access:** User (requires Authorization header)  
  **Headers:** `Authorization: Bearer <token>`  
  **Returns:** `["1.20.1", "1.19.4", ...]`

- **GET `/api/forge_versions/<mc_version>`**  
  List Forge versions for a given Minecraft version.  
  **Access:** User (requires Authorization header)  
  **Headers:** `Authorization: Bearer <token>`  
  **Returns:**  
  ```json
  {
    "1.20.1-47.1.0": { "recommended": true, "latest": false, "bugged": false },
    ...
  }
  ```

- **GET `/api/servers`**  
  List all configured servers.  
  **Access:** User (requires Authorization header)  
  **Headers:** `Authorization: Bearer <token>`  
  **Returns:** `["server1", "server2", ...]`

- **GET `/api/server/<server_name>`**  
  Get information about a specific server.  
  **Access:** User (requires Authorization header)  
  **Headers:** `Authorization: Bearer <token>`  
  **Returns:** `{ ...server info... }`

- **POST `/api/create_server`**  
  Create a new server.  
  **Access:** Operator (requires Authorization header)  
  **Headers:** `Authorization: Bearer <token>`  
  **Body:** `{ "name": string, "mc_version": string, "forge_version": string }`  
  **Returns:** `{ "message": "Server Created" }` on success.

---

All endpoints return standard HTTP status codes and error messages in case of failure.
