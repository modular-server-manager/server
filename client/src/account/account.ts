import ensure_token from "../scripts/ensure_token.js";
import API from "../scripts/api.js";

ensure_token();

// fill the span #name with the username
API.get_user_info().then((response) => {
    if (!response) {
        console.error("No user info found.");
        alert("An error occurred while fetching user information.");
        return;
    }
    console.log("User info response:", response);
    const {username} = response;
    const name = document.getElementById("name") as HTMLSpanElement;
    name.innerText = username;
}).catch((error) => {
    console.error("Error getting user info:", error);
    alert("An error occurred while fetching user information.");
});

document.getElementById("change-password-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();

    const newPassword = (document.getElementById("new-password") as HTMLInputElement).value;
    const confirmPassword = (document.getElementById("confirm-password") as HTMLInputElement).value;

    if (newPassword !== confirmPassword) {
        alert("Passwords do not match!");
        return;
    }

    try {
        const success = await API.change_password(newPassword);
        if (success) {
            alert("Password changed successfully!");
        }
        else {
            alert("Error changing password. Please try again.");
        }
    } catch (error) {
        console.error("Error changing password:", error);
        alert("An error occurred. Please try again.");
    }
    const form = document.getElementById("change-password-form") as HTMLFormElement;
    form.reset();
});

// delete account button
document.getElementById("delete-account")?.addEventListener("click", async (event) => {
    event.preventDefault();

    if (confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
        try {
            const success = await API.delete_account();
            if (success) {
                alert("Account deleted successfully!");
                window.location.reload();
            }
            else {
                alert("Error deleting account. Please try again.");
            }
        } catch (error) {
            console.error("Error deleting account:", error);
            alert("An error occurred. Please try again.");
        }
    }
});
