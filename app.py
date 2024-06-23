import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import psutil
import json
import sys
#import ctypes
import pythoncom
import pywintypes
import win32com.client
from tkinterdnd2 import DND_FILES, TkinterDnD
import winreg

version = "1.3"
base_title = "ForceBindIP GUI"

def get_build_details():
    build_details_path = resource_path("build_details.txt")
    if os.path.exists(build_details_path):
        with open(build_details_path, "r") as file:
            lines = file.readlines()
            if len(lines) >= 2:
                build_date = lines[0].strip()
                sha_commit = lines[1].strip()
                return build_date, sha_commit
    return "N/A", "N/A"

def set_title(window, base_title, version):
    full_title = f"{base_title} (v{version})"
    window.title(full_title)

#def minimize_console():
#    user32 = ctypes.WinDLL('user32')
#    kernel32 = ctypes.WinDLL('kernel32')
#    hWnd = kernel32.GetConsoleWindow()
#    user32.ShowWindow(hWnd, 6)

#minimize_console()

# Check for Visual Studio 2015 Runtimes
def is_runtime_installed():
    def check_registry_key(hive, key, value):
        try:
            registry_key = winreg.OpenKey(hive, key, 0, winreg.KEY_READ)
            installed, _ = winreg.QueryValueEx(registry_key, value)
            winreg.CloseKey(registry_key)
            return installed == 1
        except WindowsError:
            return False

    x86_key = r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x86"
    x64_key = r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
    value = "Installed"

    x86_installed = check_registry_key(winreg.HKEY_LOCAL_MACHINE, x86_key, value)
    x64_installed = check_registry_key(winreg.HKEY_LOCAL_MACHINE, x64_key, value)

    return x86_installed and x64_installed

def check_runtimes_and_launch():
    if not is_runtime_installed():
        root = tk.Tk()
        root.withdraw()
        response = messagebox.askyesnocancel(
            "Visual Studio 2015 Runtimes Required",
            "This program requires Visual Studio 2015 Runtimes (x86 and x64) installed in order to function properly. Do you want to download it now?",
            icon=messagebox.WARNING,
            type=messagebox.YESNOCANCEL
        )
        if response is None:  # Skip
            root.quit()
            return
        elif response:  # Yes
            os.system("start https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170")
            root.quit()
            sys.exit(1)
        else:  # No
            root.quit()
            sys.exit(1)

check_runtimes_and_launch()

# Use the user's home directory to store the config file
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "forcebindgui_config.json")
MAX_RECENT_PROGRAMS = 10

last_added_program = None  # Track the last added program

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

forcebindip_exe = resource_path("assets/ForceBindIP.exe")
forcebindip64_exe = resource_path("assets/ForceBindIP64.exe")
dll1_path = resource_path("assets/Bind.dll")
dll2_path = resource_path("assets/Bind64.dll")
icon_path = resource_path("assets/FBI.ico")

class ToolTip:
    def __init__(self, widget, text_func):
        self.widget = widget
        self.text_func = text_func
        self.tipwindow = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        if self.tipwindow or not self.text_func:
            return
        text = self.text_func()
        if not text:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def update_tooltip(tooltip, text_func):
    tooltip.text_func = text_func

def update_tooltip_with_interface(tooltip, widget):
    selected_interface = widget.get()
    update_tooltip(tooltip, lambda: f"{selected_interface}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {"recent_programs": [], "close_after_running": True}

def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

def list_network_interfaces():
    interfaces = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2:  # AF_INET (IPv4)
                interfaces.append((interface, addr.address))
                print(f"Found interface: {interface} with IP: {addr.address}")
                break
    return interfaces

def browse_file():
    global last_added_program
    save_current_program_state()  # Save the current state before browsing a new program

    current_path = entry_program_path.get()
    initial_dir = os.path.dirname(current_path) if os.path.isfile(current_path) else os.getcwd()
    filename = filedialog.askopenfilename(title="Select a Program", initialdir=initial_dir)
    if filename:
        entry_program_path.delete(0, tk.END)
        entry_program_path.insert(0, filename)
        entry_launch_args.delete(0, tk.END)
        combo_architecture.set("x86")
        update_recent_programs_dropdown(filename)
        last_added_program = filename  # Track the last added program

        # Reset the interface to the default (first) interface
        if combo_interfaces['values']:
            combo_interfaces.current(0)
            update_ip_label()

def run_forcebindip():
    global last_added_program
    program_path = os.path.normpath(entry_program_path.get())  # Normalize the path
    selected_interface = combo_interfaces.get()
    selected_architecture = combo_architecture.get()
    launch_args = entry_launch_args.get()

    if not program_path or not os.path.isfile(program_path):
        messagebox.showerror("Error", "Please select a valid program.")
        return

    if not selected_interface:
        messagebox.showerror("Error", "Please select a network interface.")
        return

    interface_ip = interface_dict.get(selected_interface)
    if not interface_ip:
        messagebox.showerror("Error", "Unable to find the IP address for the selected interface.")
        return

    # Use the appropriate ForceBindIP executable based on the selected architecture
    forcebindip_exe = "ForceBindIP64.exe" if selected_architecture == "x64" else "ForceBindIP.exe"
    forcebindip_path = os.path.join(sys._MEIPASS, forcebindip_exe) if hasattr(sys, "_MEIPASS") else forcebindip_exe

    # Ensure the DLL is in the same directory as the executable
    if hasattr(sys, "_MEIPASS"):
        os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

    command = f'"{forcebindip_path}" {interface_ip} "{program_path}" {launch_args}'
    program_dir = os.path.dirname(program_path)
    print(f"Running command: {command} in directory: {program_dir}")
    try:
        subprocess.run(command, check=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, cwd=program_dir)
        config = load_config()
        recent_programs = config.get("recent_programs", [])
        new_entry = {
            "program_path": program_path,
            "interface": selected_interface,
            "architecture": selected_architecture,
            "launch_args": launch_args
        }
        for i, entry in enumerate(recent_programs):
            if os.path.normpath(entry["program_path"]) == program_path:
                recent_programs.pop(i)  # Remove existing entry
                break
        recent_programs.insert(0, new_entry)  # Add new entry at the top

        recent_programs = recent_programs[:MAX_RECENT_PROGRAMS]
        config["recent_programs"] = recent_programs
        config["close_after_running"] = var_close_after_running.get()
        save_config(config)
        update_recent_programs()
        combo_recent_programs.set(os.path.basename(program_path))
        last_added_program = None  # Reset last added program after running
        if var_close_after_running.get():
            app.quit()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to run ForceBindIP.\n{str(e)}")

def update_recent_programs():
    config = load_config()
    recent_programs = config.get("recent_programs", [])
    recent_programs_list = [os.path.basename(os.path.normpath(entry["program_path"])) for entry in recent_programs]
    combo_recent_programs['values'] = recent_programs_list
    if recent_programs_list:
        combo_recent_programs.set(recent_programs_list[0])  # Set the last used program as the default selected value
    else:
        combo_recent_programs.set("")  # Clear the recent programs selection if the list is empty

def save_current_program_state():
    current_program = entry_program_path.get()
    if not current_program:
        return
    
    config = load_config()
    recent_programs = config.get("recent_programs", [])
    new_entry = {
        "program_path": current_program,
        "interface": combo_interfaces.get(),
        "architecture": combo_architecture.get(),
        "launch_args": entry_launch_args.get()
    }

    for i, entry in enumerate(recent_programs):
        if os.path.normpath(entry["program_path"]) == os.path.normpath(current_program):
            recent_programs[i] = new_entry  # Update existing entry
            break
    else:
        recent_programs.insert(0, new_entry)  # Add new entry if not found

    recent_programs = recent_programs[:MAX_RECENT_PROGRAMS]
    config["recent_programs"] = recent_programs
    save_config(config)

def on_recent_program_select(event=None):
    global last_added_program
    save_current_program_state()  # Save the current state before switching

    selected_program = combo_recent_programs.get()
    config = load_config()
    recent_programs = config.get("recent_programs", [])
    for entry in recent_programs:
        if os.path.basename(os.path.normpath(entry["program_path"])) == selected_program:
            entry_program_path.delete(0, tk.END)
            entry_program_path.insert(0, entry["program_path"])
            combo_interfaces.set(entry["interface"])
            combo_architecture.set(entry["architecture"])
            entry_launch_args.delete(0, tk.END)
            entry_launch_args.insert(0, entry.get("launch_args", ""))
            update_ip_label()
            break

    # Remove the last added program if it wasn't run
    if last_added_program and os.path.normpath(last_added_program) not in [os.path.normpath(entry["program_path"]) for entry in recent_programs]:
        recent_programs = [entry for entry in recent_programs if os.path.normpath(entry["program_path"]) != os.path.normpath(last_added_program)]
        config["recent_programs"] = recent_programs
        save_config(config)
        update_recent_programs()
        last_added_program = None  # Reset the last added program tracker

    # Set the combo box to the selected program
    combo_recent_programs.set(selected_program)

def clear_recent_programs():
    if messagebox.askyesno("Confirm", "Are you sure? This will clear your Recent Programs list"):
        config = load_config()
        config["recent_programs"] = []
        save_config(config)
        update_recent_programs()
        entry_program_path.delete(0, tk.END)
        entry_launch_args.delete(0, tk.END)
        combo_architecture.set("x86")

        # Reset the interface to the default (first) interface
        if combo_interfaces['values']:
            combo_interfaces.current(0)
            update_ip_label()

def resolve_lnk(filepath):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(filepath)
    return shortcut.Targetpath, shortcut.Arguments

def drop(event):
    global last_added_program
    save_current_program_state()  # Save the current state before dropping a new program

    filepath = event.data.strip('{}')
    if filepath.endswith('.lnk'):
        filepath, arguments = resolve_lnk(filepath)
    else:
        arguments = ""
    if filepath:
        entry_program_path.delete(0, tk.END)
        entry_program_path.insert(0, filepath)
        entry_launch_args.delete(0, tk.END)
        entry_launch_args.insert(0, arguments)
        combo_architecture.set("x86")  # Reset architecture
        update_recent_programs_dropdown(filepath, arguments)
        last_added_program = filepath  # Track the last added program

        # Reset the interface to the default (first) interface
        if combo_interfaces['values']:
            combo_interfaces.current(0)
            update_ip_label()

def update_recent_programs_dropdown(filepath, arguments=""):
    filepath = os.path.normpath(filepath)  # Normalize the path
    config = load_config()
    recent_programs = config.get("recent_programs", [])

    updated = False
    for entry in recent_programs:
        if os.path.normpath(entry["program_path"]) == filepath:
            entry["launch_args"] = arguments  # Update launch arguments
            updated = True
            break

    if not updated:
        new_entry = {
            "program_path": filepath,
            "launch_args": arguments,
            "interface": combo_interfaces.get(),
            "architecture": combo_architecture.get()
        }
        recent_programs.insert(0, new_entry)
        recent_programs = recent_programs[:MAX_RECENT_PROGRAMS]
        config["recent_programs"] = recent_programs
        save_config(config)

    recent_programs_list = [os.path.basename(os.path.normpath(entry["program_path"])) for entry in recent_programs]
    combo_recent_programs['values'] = recent_programs_list
    combo_recent_programs.set(os.path.basename(filepath))

def on_interface_select(event=None):
    update_ip_label()

def update_ip_label():
    selected_interface = combo_interfaces.get()
    interface_ip = interface_dict.get(selected_interface, "")
    label_ip.config(text=f"IP: {interface_ip}")

def show_help():
    build_date, sha_commit = get_build_details()
    commit_url = f"https://github.com/mistercalvin/forcebindip-gui/commit/{sha_commit}"  # Adjust with your actual repository details

    about_window = tk.Toplevel(app)
    about_window.withdraw()  # Hide the window until it's fully set up
    about_window.title("About")
    about_window.geometry("300x150")
    about_window.resizable(False, False)

    # Center the about window relative to the main application window
    app.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() // 2) - (300 // 2)
    y = app.winfo_y() + (app.winfo_height() // 2) - (150 // 2)
    about_window.geometry(f"+{x}+{y}")

    # Disable minimize button
    about_window.attributes("-toolwindow", 1)

    label = tk.Label(about_window, text=f"ForceBindIP GUI v{version} created by", pady=10)
    label.pack()

    # Add GitHub logo and link
    github_logo_path = resource_path("github_logo.png")
    github_logo = tk.PhotoImage(file=github_logo_path)

    frame = tk.Frame(about_window)
    frame.pack()

    logo_label = tk.Label(frame, image=github_logo)
    logo_label.image = github_logo  # Keep a reference to avoid garbage collection
    logo_label.pack(side=tk.LEFT)

    link = tk.Label(frame, text="MisterCalvin", fg="blue", cursor="hand2")
    link.pack(side=tk.LEFT, padx=5)

    def open_link(event):
        os.system("start https://github.com/mistercalvin")
        about_window.destroy()

    link.bind("<Button-1>", open_link)
    tooltip_github_link = ToolTip(link, lambda: "https://github.com/mistercalvin")

    # Print build details only if they exist
    if build_date != "N/A" and sha_commit != "N/A":
        build_details_frame = tk.Frame(about_window)
        build_details_frame.pack()

        build_date_label = tk.Label(build_details_frame, text=f"Compiled: {build_date}")
        build_date_label.pack()

        sha_label = tk.Label(build_details_frame, text=f"Commit sha1: {sha_commit}", fg="blue", cursor="hand2")
        tooltip_sha_link = ToolTip(sha_label, lambda: commit_url)
        sha_label.pack()

        def open_commit_link(event):
            os.system(f"start {commit_url}")
            about_window.destroy()

        sha_label.bind("<Button-1>", open_commit_link)
        tooltip_sha = ToolTip(sha_label, lambda: commit_url)

    button = tk.Button(about_window, text="Close", command=about_window.destroy)
    button.pack(pady=5)

    closing_about_window = False

    def on_focus_out(event):
        # Delay checking the focus to avoid flash
        about_window.after(1, lambda: close_if_lost_focus(event))

    def close_if_lost_focus(event):
        nonlocal closing_about_window
        if not about_window.focus_get():
            closing_about_window = True
            about_window.destroy()

    def close_about_window(event):
        nonlocal closing_about_window
        if not closing_about_window and about_window.winfo_exists():
            closing_about_window = True
            about_window.destroy()

    about_window.bind("<FocusOut>", on_focus_out)
    app.bind_all("<Button-1>", close_about_window)  # Bind to all widgets to catch clicks anywhere
    app.bind("<FocusIn>", close_about_window)  # Bind focus to catch title bar clicks

    about_window.deiconify()  # Show the window after it's fully set up
    about_window.grab_set()
    about_window.focus_force()

    def on_close():
        nonlocal closing_about_window
        closing_about_window = True
        about_window.destroy()

    about_window.protocol("WM_DELETE_WINDOW", on_close)

def focus_main_window():
    app.update_idletasks()
    app.attributes('-topmost', True)
    app.after(100, lambda: app.attributes('-topmost', False))
    app.focus_set()

app = TkinterDnD.Tk()
set_title(app, base_title, version)
app.geometry("435x215")
app.resizable(False, False)

# Bring the window to the top and focus it
focus_main_window()

app.drop_target_register(DND_FILES)
app.dnd_bind('<<Drop>>', drop)

frame = tk.Frame(app, padx=10, pady=10)
frame.pack(fill=tk.BOTH, expand=True)

label_recent_programs = tk.Label(frame, text="Recent Programs:")
label_recent_programs.grid(row=0, column=0, sticky=tk.W)

combo_recent_programs = ttk.Combobox(frame)
combo_recent_programs.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
combo_recent_programs.bind("<<ComboboxSelected>>", on_recent_program_select)
tooltip_recent_programs = ToolTip(combo_recent_programs, lambda: f"{combo_recent_programs.get()}" if combo_recent_programs.get() else "")

label_program_path = tk.Label(frame, text="Program:")
label_program_path.grid(row=1, column=0, sticky=tk.W)
tooltip_program_path_label = ToolTip(label_program_path, lambda: "Path to the program you want to run")

entry_program_path = tk.Entry(frame, width=40)
entry_program_path.grid(row=1, column=1, padx=5, pady=5)
tooltip_program_path = ToolTip(entry_program_path, lambda: entry_program_path.get() if entry_program_path.get() else "")

help_icon = tk.PhotoImage(file=resource_path("help_icon.png")).subsample(2, 2)

help_button = tk.Button(frame, image=help_icon, command=show_help, relief=tk.FLAT, borderwidth=0)
help_button.image = help_icon  # Keep a reference to the image to prevent garbage collection
help_button.place(relx=1.0, rely=0.0, anchor="ne")
tooltip_help_button = ToolTip(help_button, lambda: "About ForceBindIP GUI")

button_browse = tk.Button(frame, text="Browse", command=browse_file)
button_browse.grid(row=1, column=2, padx=5, pady=5)

label_launch_args = tk.Label(frame, text="Launch args:")
label_launch_args.grid(row=2, column=0, sticky=tk.W)
tooltip_launch_args_label = ToolTip(label_launch_args, lambda: "Additional arguments for the program being ran")

entry_launch_args = tk.Entry(frame, width=40)
entry_launch_args.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)
tooltip_launch_args = ToolTip(entry_launch_args, lambda: entry_launch_args.get() if entry_launch_args.get() else "")

label_interface = tk.Label(frame, text="Network Interface:")
label_interface.grid(row=3, column=0, sticky=tk.W)
tooltip_interface_label = ToolTip(label_interface, lambda: "The interface you want to bind to")

combo_interfaces = ttk.Combobox(frame, width=15)
combo_interfaces.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
combo_interfaces.bind("<<ComboboxSelected>>", on_interface_select)

tooltip_interface = ToolTip(combo_interfaces, lambda: f"{combo_interfaces.get()}" if combo_interfaces.get() else "")
combo_interfaces.bind("<Enter>", lambda e: tooltip_interface.enter(e))
combo_interfaces.bind("<Leave>", lambda e: tooltip_interface.leave(e))
combo_interfaces.bind("<<ComboboxSelected>>", lambda e: update_tooltip_with_interface(tooltip_interface, combo_interfaces))

label_ip = tk.Label(frame, text="", width=15, anchor="w", justify="left")
label_ip.grid(row=3, column=1, padx=(120, 0), pady=5, sticky=tk.W)

label_architecture = tk.Label(frame, width=10, text="Architecture:")
label_architecture.grid(row=4, column=0, sticky=tk.W)
tooltip_label_architecture = ToolTip(label_architecture, lambda: "Architecture to run ForceBindIP as")

combo_architecture = ttk.Combobox(frame, width=5, values=["x86", "x64"])
combo_architecture.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
combo_architecture.set("x86")

button_run = tk.Button(frame, text="Run ForceBindIP", command=run_forcebindip)
button_run.grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)

var_close_after_running = tk.BooleanVar()
check_close_after_running = tk.Checkbutton(frame, text="Close after running", variable=var_close_after_running)
check_close_after_running.grid(row=5, column=1, padx=5, pady=5, sticky=tk.W)
tooltip_check_close_after_running = ToolTip(check_close_after_running, lambda: "Close ForceBindIP GUI after program has run")

button_clear = tk.Button(frame, text="Clear", command=clear_recent_programs)
button_clear.grid(row=5, column=2, padx=5, pady=5, sticky=tk.W)
tooltip_clear_button = ToolTip(button_clear, lambda: "Clear configuration file")

interfaces = list_network_interfaces()
interface_dict = {name: ip for name, ip in interfaces}
combo_interfaces['values'] = list(interface_dict.keys())

# Set the default interface to the first one if available
if combo_interfaces['values']:
    combo_interfaces.current(0)
    update_ip_label()
    combo_interfaces.bind("<<ComboboxSelected>>", on_interface_select)

# Load configuration if it exists
config = load_config()
if "last_program" in config:
    entry_program_path.insert(0, config["last_program"])
if "last_interface" in config and config["last_interface"] in interface_dict:
    combo_interfaces.set(config["last_interface"])
    update_ip_label()
    update_tooltip_with_interface(tooltip_interface, combo_interfaces)  # Update tooltip text based on the initial interface
if "last_architecture" in config:
    combo_architecture.set(config["last_architecture"])
if "last_launch_args" in config:
    entry_launch_args.insert(0, config["last_launch_args"])
if "close_after_running" in config:
    var_close_after_running.set(config["close_after_running"])

update_recent_programs()

# Autofill the fields based on the last selected recent program
on_recent_program_select()

def on_close():
    save_current_program_state()  # Save the current state on close
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_close)

app.mainloop()