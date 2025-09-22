# Events


## SERVER.STARTING (0x1)

Fired when a server is starting.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.STARTED (0x2)

Fired after a server has started.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.STOPPING (0x3)

Fired when a server is stopping.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.STOPPED (0x4)

Fired after a server has stopped.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.CRASHED (0x5)

Fired when a server has crashed.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.START (0x6)

Request to start a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.STOP (0x7)

Request to stop a server. Returns True if the server was stopped successfully, False otherwise. The emmitter will wait for the server to stop before returning.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

bool

---

## SERVER.RESTART (0x8)

Request to restart a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.CREATE (0x9)

Request to create a new server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| server_type | str | 00003 |
| server_path | str | 00004 |
| autostart | bool | 00005 |
| mc_version | Version | 00006 |
| modloader_version | Version | 00007 |
| ram | int | 00008 |


### Returns:

None

---

## SERVER.DELETE (0xa)

Request to delete a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.RENAME (0xb)

Request to rename a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| new_name | str | 00003 |


### Returns:

None

---

## SERVER.CREATED (0xc)

Fired after a server has been created.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| server_type | str | 00003 |
| server_path | str | 00004 |
| autostart | bool | 00005 |
| mc_version | Version | 00006 |
| modloader_version | Version | 00007 |
| ram | int | 00008 |


### Returns:

None

---

## SERVER.DELETED (0xd)

Fired after a server has been deleted.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

None

---

## SERVER.RENAMED (0xe)

Fired after a server has been renamed.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| new_name | str | 00003 |


### Returns:

None

---

## SERVER.LIST (0xf)

Request a list of all servers. Returns a list of dictionaries containing server information.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |


### Returns:

List[Dict[str, Any]]

---

## SERVER.PING (0x10)

Request to ping a server. Returns the server's status as a string: "online", "offline", or "starting".

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

str

---

## SERVER.SEED (0x11)

Request the world seed of a server. Returns the seed as a string.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

str

---

## SERVER.INFO (0x12)

Request detailed information about a server. Returns a dictionary containing server information.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

Dict[str, Any]

---

## SERVER.CREATING (0x13)

Fired when a server is being created.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| server_type | str | 00003 |
| server_path | str | 00004 |
| autostart | bool | 00005 |
| mc_version | Version | 00006 |
| modloader_version | Version | 00007 |
| ram | int | 00008 |


### Returns:

None

---

## SERVER.STARTED_AT (0x105)

Request the time a server was started. Returns a datetime object representing the start time.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

datetime

---

## CONSOLE.MESSAGE_RECEIVED (0x101)

Fired when a console message is received from a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| from | str | 00003 |
| message | str | 00004 |


### Returns:

None

---

## CONSOLE.LOG_RECEIVED (0x102)

Fired when a log message is received from a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| content | str | 00003 |


### Returns:

None

---

## CONSOLE.SEND_MESSAGE (0x103)

Request to send a message to a server's console.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| _from | str | 00003 |
| message | str | 00004 |


### Returns:

None

---

## CONSOLE.SEND_COMMAND (0x104)

Request to send a command to a server's console.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| command | str | 00003 |


### Returns:

None

---

## PLAYERS.JOINED (0x201)

Fired when a player joins a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| player_name | str | 00003 |


### Returns:

None

---

## PLAYERS.LEFT (0x202)

Fired when a player leaves a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| player_name | str | 00003 |


### Returns:

None

---

## PLAYERS.KICKED (0x203)

Fired when a player is kicked from a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| player_name | str | 00003 |


### Returns:

None

---

## PLAYERS.BANNED (0x204)

Fired when a player is banned from a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| player_name | str | 00003 |


### Returns:

None

---

## PLAYERS.PARDONED (0x205)

No description available.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| player_name | str | 00003 |


### Returns:

None

---

## PLAYERS.KICK (0x206)

Request to kick a player from a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| player_name | str | 00003 |
| reason | str | 00004 |


### Returns:

None

---

## PLAYERS.BAN (0x207)

Request to ban a player from a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| player_name | str | 00003 |
| reason | str | 00004 |


### Returns:

None

---

## PLAYERS.PARDON (0x208)

Request to pardon (unban) a player from a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |
| player_name | str | 00003 |


### Returns:

None

---

## PLAYERS.LIST (0x209)

Request a list of all players currently online on a server.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| server_name | str | 00002 |


### Returns:

list[str]

---

## GET_VERSIONS.MINECRAFT (0x301)

Request a list of all available Minecraft versions.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |


### Returns:

list[Version]

---

## GET_VERSIONS.FORGE (0x302)

Request a list of all available Forge versions for a specific Minecraft version.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |
| mc_version | Version | 00002 |


### Returns:

Dict[Version, Dict[str, Any]]

---

## GET_DIRECTORIES.MINECRAFT (0x401)

Request a list of all available Minecraft directories.

### Arguments: 

| Name | Type | ID |
|------|------|----|
| timestamp | datetime | 00001 |


### Returns:

list[str]

---
