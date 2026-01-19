import tkinter as tk
from typing import Callable, Tuple

from gamuLogger import Logger

Logger.set_module("User Interface.Debug Tkinter")


class DebugTk(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Debug Tkinter")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        Logger.debug("Debug Tkinter window initialized")

    def on_close(self):
        self.close()

    def close(self):
        Logger.debug("Closing Debug Tkinter window")
        self.quit()
        self.destroy()

    def add_button(self, text: str, command: Callable[[], None]):
        button = tk.Button(self, text=text, command=command)
        button.pack(pady=5)

    def add_input(self, label: str, default: str = "", on_change: Callable[[str], None] = None):
        frame = tk.Frame(self)
        frame.pack(pady=5)
        label = tk.Label(frame, text=label)
        label.pack(side=tk.LEFT)
        entry = tk.Entry(frame)
        entry.insert(0, default)
        entry.pack(side=tk.LEFT)
        if on_change:
            entry.bind("<Return>", lambda event: on_change(entry.get()))
        return entry

    def add_terminal(self, on_message : Callable[[], str]) -> Tuple[Callable[[str], None], Callable[[], None]]: # write to terminal, clear terminal
        # contain a large not-editable textbox (the console), a small one-line textbox (the input), and a scrollbar
        frame = tk.Frame(self)
        frame.pack(pady=5)
        text = tk.Text(frame, wrap=tk.WORD, state=tk.DISABLED, height=20)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(frame, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.config(yscrollcommand=scrollbar.set)
        input_frame = tk.Frame(self)
        input_frame.pack(pady=5)
        input_text = tk.Text(input_frame, height=1)
        input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def on_key_press(event):
            Logger.trace(f"Key pressed: {event.keysym}")
            if event.keysym == "Return":
                message = input_text.get("1.0", tk.END).strip()
                Logger.debug(f"Message entered: {message}")
                input_text.delete("1.0", tk.END)
                if message:
                    on_message(message)
                return "break"
        input_text.bind("<KeyPress>", on_key_press)


        def write_to_terminal(message: str):
            text.config(state=tk.NORMAL)
            text.insert(tk.END, message + "\n")
            text.see(tk.END)
            text.config(state=tk.DISABLED)

        def clear_terminal():
            text.config(state=tk.NORMAL)
            text.delete("1.0", tk.END)
            text.config(state=tk.DISABLED)

        return write_to_terminal, clear_terminal

    def mainloop(self, n = 0):
        Logger.debug("Starting Debug Tkinter mainloop")
        return super().mainloop(n)

def ask_for_choice(title: str, message: str, choices: list[str]) -> str:
    """
    Ask the user for a choice from a list of options.
    :param title: Title of the dialog.
    :param message: Message to display.
    :param choices: List of choices.
    :return: The choice selected by the user.
    """
    root = tk.Tk()
    root.title(title)
    root.geometry("300x200")
    value = tk.StringVar()
    value.set(choices[0])
    label = tk.Label(root, text=message)
    label.pack(pady=10)
    # use a combobox to select the choice
    combo = tk.OptionMenu(root, value, *choices)
    combo.pack(pady=10)
    button = tk.Button(root, text="OK", command=root.destroy)
    button.pack(pady=10)
    root.mainloop()
    return value.get()
