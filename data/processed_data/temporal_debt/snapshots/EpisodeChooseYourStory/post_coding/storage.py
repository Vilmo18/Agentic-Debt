'''

Utility functions to save and load game sessions to JSON files.

'''

import json
from typing import Any, Dict
from tkinter import filedialog, messagebox
import os


def save_game_dialog(data_provider_callable) -> None:
    """
    Open a Save As dialog and save the session JSON provided by data_provider_callable().
    """
    file_path = filedialog.asksaveasfilename(
        title="Save Game",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if not file_path:
        return
    try:
        data = data_provider_callable()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", f"Game saved to:\n{os.path.basename(file_path)}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save game:\n{e}")


def load_game_dialog(loader_callable) -> None:
    """
    Open an Open dialog, read JSON, and pass it to loader_callable(data).
    """
    file_path = filedialog.askopenfilename(
        title="Load Game",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if not file_path:
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
        loader_callable(data)
        messagebox.showinfo("Loaded", f"Game loaded from:\n{os.path.basename(file_path)}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load game:\n{e}")
