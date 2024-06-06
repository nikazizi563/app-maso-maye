import tkinter as tk
import requests
import json
import os
import logging
import pickle
import threading
import random
import pystray
import winsound
from tkinter import ttk, messagebox, StringVar, Tk, OptionMenu
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from plyer import notification
from pystray import MenuItem as item

# Locations data
def load_locations(filename):
    with open(filename, 'r') as f:
        return json.load(f)

# Load locations from the JSON file
locations = load_locations('locations.json')

# Define function to fetch data from API with the given zone
def fetch_and_save_data(zone):
    url = f"https://api.waktusolat.app/v2/solat/{zone}"
    response = requests.get(url)
    data = response.json()
    with open('prayer_times.json', 'w') as f:
        json.dump(data, f)
    return data

def load_data(zone):
    if not os.path.exists('prayer_times.json'):
        return fetch_and_save_data(zone)

    with open('prayer_times.json', 'r') as f:
        data = json.load(f)

    if 'last_updated' not in data or 'prayers' not in data:
        return fetch_and_save_data(zone)

    last_updated = datetime.strptime(data['last_updated'], '%Y-%m-%dT%H:%M:%S.%fZ')
    current_date = datetime.now()

    # Check if a month has passed since the last update
    if current_date.month != last_updated.month or current_date.year != last_updated.year:
        data = fetch_and_save_data(zone)
    
    return data

def get_current_day_prayers(prayers, current_day):
    for prayer in prayers:
        if prayer['day'] == current_day:
            return prayer
    return None

def get_next_prayer_time(prayers):
    now = datetime.now().timestamp()
    upcoming_prayers = {name: time for name, time in prayers.items() if name in ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha'] and time > now}
    
    if upcoming_prayers:
        next_prayer_name = min(upcoming_prayers, key=upcoming_prayers.get)
        return next_prayer_name.capitalize(), datetime.fromtimestamp(upcoming_prayers[next_prayer_name])
    return None, None

def update_ui():
    current_time.set(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    prayer_name, next_prayer_time = get_next_prayer_time(current_day_prayers)
    if next_prayer_time:
        countdown = next_prayer_time - datetime.now()
        countdown_str = str(countdown).split('.')[0]  # Remove microseconds
        next_prayer.set(f"{prayer_name} in {countdown_str}")
    else:
        next_prayer.set("No more prayers for today")
        check_for_next_day_update()

    root.after(1000, update_ui)

def update_prayer_times():
    global current_day_prayers

    now = datetime.now().timestamp()
    isha_time = current_day_prayers['isha']

    if now > isha_time:
        current_day = datetime.now().day
        next_day_prayers = None

        for prayer in data['prayers']:
            if prayer['day'] == current_day + 1:
                next_day_prayers = prayer
                break

        if next_day_prayers:
            current_day_prayers = next_day_prayers
            for widget in prayer_times_frame.winfo_children():
                widget.destroy()

            day_label = ttk.Label(prayer_times_frame, text=f"Prayer Times for Tomorrow:")
            day_label.pack()

            for name in ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']:
                time_str = datetime.fromtimestamp(current_day_prayers[name]).strftime('%H:%M:%S')
                prayer_time_label = ttk.Label(prayer_times_frame, text=f"{name.capitalize()}: {time_str}")
                prayer_time_label.pack()

            # Immediately update the UI to show the next prayer
            update_ui()
        else:
            for widget in prayer_times_frame.winfo_children():
                widget.destroy()
            
            no_prayer_label = ttk.Label(prayer_times_frame, text="No prayer times available for tomorrow.")
            no_prayer_label.pack()
    else:
        for widget in prayer_times_frame.winfo_children():
            widget.destroy()

        day_label = ttk.Label(prayer_times_frame, text=f"Prayer Times for Today:")
        day_label.pack()

        for name in ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']:
            time_str = datetime.fromtimestamp(current_day_prayers[name]).strftime('%H:%M:%S')
            prayer_time_label = ttk.Label(prayer_times_frame, text=f"{name.capitalize()}: {time_str}")
            prayer_time_label.pack()

def check_for_next_day_update():
    now = datetime.now().timestamp()
    isha_time = current_day_prayers['isha']

    if now > isha_time:
        update_prayer_times()

notifications_muted = False
# Global variable to store the settings window instance
settings_window = None  
change_location_window = None
about_window = None  

# Settings function
def open_settings_window():
    global settings_window
    
    if settings_window is None or not settings_window.winfo_exists():  # Check if settings window is not already open or has been closed
        settings_window = tk.Toplevel(root)
        settings_window.title("Settings")
        settings_window.resizable(0, 0) # Disable resizing
        settings_window.attributes("-topmost", True)  # Ensure stays on top
        settings_window.attributes('-toolwindow', 1)  # Windows-specific attribute to remove minimize and maximize buttons
        
        # Title for location settings
        tk.Label(settings_window, text="Location Settings", font=("Helvetica", 12)).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        # Display current selected location
        tk.Label(settings_window, text="Selected Location:", font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        selected_location_display = tk.Label(settings_window, textvariable=selected_zone, font=("Helvetica", 10)) # why does it show PY_VAR0
        selected_location_display.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Change location button
        change_location_button = tk.Button(settings_window, text="Change Location", command=lambda: open_change_location_window(settings_window))
        change_location_button.grid(row=2, column=0, columnspan=2, padx=10, pady=5)

        # Notifications settings title
        tk.Label(settings_window, text="Notifications Settings", font=("Helvetica", 12)).grid(row=3, column=0, columnspan=2, padx=10, pady=5)
        tk.Label(settings_window, text="Notifications:", font=("Helvetica", 10)).grid(row=4, column=0, sticky="w", padx=10, pady=5)
        
        notification_status_label = tk.Label(settings_window, text="Muted" if notifications_muted else "Active", font=("Helvetica", 10))
        notification_status_label.grid(row=4, column=1, sticky="w", padx=10, pady=5)

        def toggle_notifications():
            global notifications_muted
            notifications_muted = not notifications_muted
            notification_status_label.config(text="Muted" if notifications_muted else "Active")

        notification_toggle_button = tk.Button(settings_window, text="Toggle Notifications", command=toggle_notifications)
        notification_toggle_button.grid(row=5, column=0, columnspan=2, padx=10, pady=5)

    else:
        settings_window.lift()  
def open_change_location_window(settings_window):
    global change_location_window

    if change_location_window is None or not change_location_window.winfo_exists():  # Check if settings window is not already open or has been closed
        settings_window.destroy()
        change_location_window = tk.Toplevel(root)
        change_location_window.title("Change Location")
        change_location_window.resizable(0, 0)  # Disable resizing
        change_location_window.attributes("-topmost", True)  # Ensure stays on top
        change_location_window.attributes('-toolwindow', 1)  # Windows-specific attribute to remove minimize and maximize buttons

        # Title for location settings
        tk.Label(change_location_window, text="Update Location", font=("Helvetica", 12)).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        # Labels for state and district selection (using Arial font)
        tk.Label(change_location_window, text="Select State:", font=("Arial", 10)).grid(row=1, column=0, padx=10, pady=10)
        tk.Label(change_location_window, text="Select District:", font=("Arial", 10)).grid(row=2, column=0, padx=10, pady=10)

        # State combobox (using Arial font)
        state_var = tk.StringVar()
        state_combobox = ttk.Combobox(change_location_window, textvariable=state_var)
        state_combobox.grid(row=1, column=1, padx=10, pady=10)

        # District combobox (using Arial font)
        district_var = tk.StringVar()
        district_combobox = ttk.Combobox(change_location_window, textvariable=district_var)
        district_combobox.grid(row=2, column=1, padx=10, pady=10)

        # Populate state values
        states = sorted(set(loc["negeri"] for loc in locations))
        state_combobox['values'] = states

        def update_district_combobox(event):
            district_var.set("")
            district_combobox.set("")
            selected_state = state_var.get()
            districts = [loc['daerah'] for loc in locations if loc['negeri'] == selected_state]
            district_combobox['values'] = districts

        state_combobox.bind("<<ComboboxSelected>>", update_district_combobox)

        def change_location(*args):
            selected_state = state_var.get()
            selected_district = district_var.get()
            global data, current_day_prayers
            if selected_state and selected_district:
                zone = next((loc['jakimCode'] for loc in locations if loc['negeri'] == selected_state and loc['daerah'] == selected_district), None)
                if zone:
                    data = fetch_and_save_data(zone)
                    current_day_prayers = get_current_day_prayers(data['prayers'], datetime.now().day)
                    update_prayer_times()
                    selected_zone.set(load_saved_zone())
                    change_location_window.destroy()
                else:
                    messagebox.showerror("Error", "Invalid state or district selection.")
            else:
                messagebox.showerror("Error", "Please select state and district.")

        # Save button
        save_button = tk.Button(change_location_window, text="Save", command=change_location)
        save_button.grid(row=3, column=0, columnspan=2, padx=10, pady=5)
    else:
        change_location_window.lift()

# UI extra function
def on_closing():
    if messagebox.askokcancel("Exit Confirmation", "Do you want to quit?"):
        root.quit()
def show_main_window(icon, item):
    icon.stop()
    root.after(0, root.deiconify)
def quit_application(icon, item):
    icon.stop()
    if messagebox.askokcancel("Exit Confirmation", "Do you want to quit?"):
        root.quit()

# Function to update the tray icon menu
def update_tray_icon_menu(icon):
    icon.menu = pystray.Menu(
        item('Show App', show_main_window),
        item(f'Notifications {"Off" if notifications_muted else "On"}', toggle_notifications),
        item('Exit App', quit_application)
    )

# Function to toggle notifications and update the menu
def toggle_notifications(icon, item):
    global notifications_muted
    notifications_muted = not notifications_muted
    update_tray_icon_menu(icon)

# Function to create a system tray icon for the prayer app
def create_system_tray_icon():
    # Create an image for the icon
    image = Image.new('RGB', (64, 64), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 48, 48), outline=(0, 0, 0), fill=(255, 255, 255))

    # Create the icon with a menu
    icon = pystray.Icon("prayer_app", image, "Prayer App", menu=None)
    update_tray_icon_menu(icon)

    # Run the icon
    icon.run()

def hide_main_window():
    root.withdraw()
    global settings_window
    global change_location_window
    global about_window
    if settings_window:
        settings_window.destroy()
    if change_location_window:
        change_location_window.destroy()
    if about_window:
        about_window.destroy()
    create_system_tray_icon()

def exit_application():
    root.quit()

def open_about_window():
    global about_window
    
    if about_window is None or not about_window.winfo_exists():  # Check if settings window is not already open or has been closed
        about_window = tk.Toplevel(root)
        about_window.title("About")
        about_window.resizable(0, 0) # Disable resizing
        about_window.attributes("-topmost", True)  # Ensure stays on top
        about_window.attributes('-toolwindow', 1)  # Windows-specific attribute to remove minimize and maximize buttons

        # Create labels
        tk.Label(about_window, text="Maso Maye", font=("Helvetica", 14)).pack(padx=10, pady=10)
        tk.Label(about_window, text="Prayer Times Notifications", font=("Helvetica", 10)).pack(padx=10, pady=10)
        tk.Label(about_window, text="Version 1.0", font=("Helvetica", 10)).pack(padx=10, pady=5)
        tk.Label(about_window, text="Created by nikajiji", font=("Helvetica", 10)).pack(padx=10, pady=5)

        # Create a close button
        close_button = tk.Button(about_window, text="Close", command=about_window.destroy)
        close_button.pack(pady=10)
        
    else:
        about_window.lift()  

def load_saved_zone():
    if os.path.exists('prayer_times.json'):
        with open('prayer_times.json', 'r') as f:
            data = json.load(f)
            return data.get('zone', 'KTN01') # Why does it written KTN01
    return 'KTN01'

# Initialize Tkinter
root = tk.Tk()
root.title("Prayer Times")

# Variable to store the selected zone
selected_zone = StringVar(root)
selected_zone.set(load_saved_zone()) 

# Variables to store current time and next prayer time
current_time = StringVar()
next_prayer = StringVar()

# Labels to display current time and next prayer time
time_label = ttk.Label(root, textvariable=current_time)
time_label.pack()

next_prayer_label = ttk.Label(root, textvariable=next_prayer)
next_prayer_label.pack()

# Frame to display prayer times
prayer_times_frame = ttk.Frame(root)
prayer_times_frame.pack()

# Load data and update UI
data = load_data(selected_zone.get())
current_day_prayers = get_current_day_prayers(data['prayers'], datetime.now().day)
update_prayer_times()
update_ui()

menu = tk.Menu(root)
root.config(menu=menu)

settings_menu = tk.Menu(menu, tearoff=False)
menu.add_cascade(label="Menu", menu=settings_menu)
settings_menu.add_command(label="Open Settings", command=open_settings_window)
settings_menu.add_command(label="Close to Tray", command=hide_main_window)
settings_menu.add_command(label="Exit", command=exit_application)

help_menu = tk.Menu(menu, tearoff=False)
menu.add_cascade(label="Help", menu=help_menu)
help_menu.add_command(label="Report Issue", command=open_about_window, state="disabled")
help_menu.add_command(label="Check for updates", command=open_about_window, state="disabled")
help_menu.add_command(label="About", command=open_about_window)

root.protocol("WM_DELETE_WINDOW", hide_main_window)

# Start Tkinter main loop
root.mainloop()