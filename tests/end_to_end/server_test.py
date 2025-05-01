import requests
import time
import pytest
import subprocess
import os

BASE_URL = "http://localhost:5000"

BASE_PATH = __file__[:__file__.rfind('/')]  # folder containing this file

CONFIG_FILE = f"{BASE_PATH}/config.json"


def login(username, password):
    return requests.post(f"{BASE_URL}/api/login", json={"username": username, "password": password})

def register(username, password):
    return requests.post(f"{BASE_URL}/api/register", json={"username": username, "password": password})
    
def logout(token):
    return requests.post(f"{BASE_URL}/api/logout", headers={"Authorization": f"{token}"})



class TestRegister:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, request : pytest.FixtureRequest):
        # Setup: Start the server
        name = request.node.name

        if os.path.exists(f"{BASE_PATH}/temp/server.db"):
            os.remove(f"{BASE_PATH}/temp/server.db")

        server_process = subprocess.Popen(["mc-srv-manager", "--module-level", "all:TRACE", "-c", CONFIG_FILE, "--log-file", f"{BASE_PATH}/temp/{name}.log:TRACE"])
        
        time.sleep(1)  # Wait for the server to start
        yield
        
        # Teardown: Stop the server
        server_process.terminate()
        server_process.wait()

    def test_register_success(self):
        response = register("testuser", "testpassword")
        assert response.status_code == 201 # Created
        assert "token" in response.json()
        assert response.json()["token"] is not None
        assert response.json()["token"] != ""
        
    @pytest.mark.parametrize(
        "username, password, response_json", [
        ("", "testpassword", {"message": "Missing parameters"}),
        ("testuser", "", {"message": "Missing parameters"}),
        ("", "", {"message": "Missing parameters"}),
    ], ids=["empty_username", "empty_password", "empty_both"])
    def test_register_missing_parameters(self, username, password, response_json):
        response = register(username, password)
        assert response.status_code == 400
        assert response.json() == response_json
        
    @pytest.mark.parametrize(
        "username, password, response_json", [
        ("testuser", "testpassword", {"message": "User already exists"}),
        ("testuser", "testpassword", {"message": "User already exists"}),
        ("testuser", "testpassword", {"message": "User already exists"}),
    ], ids=["duplicate_username_1", "duplicate_username_2", "duplicate_username_3"])
    def test_register_duplicate_user(self, username, password, response_json):
        # First register the user
        response = register(username, password)
        assert response.status_code == 201
        assert "token" in response.json()
        assert response.json()["token"] is not None
        assert response.json()["token"] != ""
        # Now try to register the same user again
        response = register(username, password)
        assert response.status_code == 409  # Conflict
        assert response.json() == response_json



class TestLogin:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, request : pytest.FixtureRequest):
        # Setup: Start the server
        name = request.node.name

        if os.path.exists(f"{BASE_PATH}/temp/server.db"):
            os.remove(f"{BASE_PATH}/temp/server.db")

        server_process = subprocess.Popen(["mc-srv-manager", "--module-level", "all:TRACE", "-c", CONFIG_FILE, "--log-file", f"{BASE_PATH}/temp/{name}.log:TRACE"])
        time.sleep(1)  # Wait for the server to start
        
        # create a test user
        register("testuser", "testpassword")

        yield  # This is where the tests will run

        # Teardown: Stop the server
        server_process.terminate()
        server_process.wait()

    def test_login_success(self):
        response = login("testuser", "testpassword")
        assert response.status_code == 200
        assert "token" in response.json()

    @pytest.mark.parametrize(
        "username, password, response_json", [
        ("", "testpassword", {"message": "Missing parameters"}),
        ("testuser", "", {"message": "Missing parameters"}),
        ("", "", {"message": "Missing parameters"}),
    ], ids=["empty_username", "empty_password", "empty_both"])
    def test_login_missing_parameters(self, username, password, response_json):
        response = login(username, password)
        assert response.status_code == 400
        assert response.json() == response_json

    @pytest.mark.parametrize(
        "username, password, response_json", [
        ("testuser", "invalidpassword", {"message": "Unauthorized"}),
        ("invaliduser", "testpassword", {"message": "Unauthorized"}),
        ("invaliduser", "invalidpassword", {"message": "Unauthorized"}),
    ], ids=["invalid_username", "invalid_password", "invalid_both"])
    def test_login_invalid_credentials(self, username, password, response_json):
        response = login(username, password)
        assert response.status_code == 401
        assert response.json() == response_json



class TestLogout:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, request : pytest.FixtureRequest):
        # Setup: Start the server
        name = request.node.name

        if os.path.exists(f"{BASE_PATH}/temp/server.db"):
            os.remove(f"{BASE_PATH}/temp/server.db")

        server_process = subprocess.Popen(["mc-srv-manager", "--module-level", "all:TRACE", "-c", CONFIG_FILE, "--log-file", f"{BASE_PATH}/temp/{name}.log:TRACE"])
        time.sleep(1)
        # Wait for the server to start
        # create a test user
        register("testuser", "testpassword")
        yield
        
        # Teardown: Stop the server
        server_process.terminate()
        server_process.wait()
        
    def test_logout_success(self):
        # First login to get the token
        response = login("testuser", "testpassword")
        assert response.status_code == 200
        token = response.json()["token"]
        
        # Now logout
        response = logout(token)
        assert response.status_code == 200
        assert response.json() == {"message": "Logged out"}
        
    @pytest.mark.parametrize(
        "token, response_code, response_json", [
        ("", 400, {"message": "Missing parameters"}),
        ("invalidtoken", 401, {"message": "Invalid token"}),
    ], ids=["empty_token", "invalid_token"])
    def test_logout_invalid_token(self, token, response_code, response_json):
        # Now logout
        response = logout(token)
        assert response.status_code == response_code
        assert response.json() == response_json

