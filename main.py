import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import requests
import json
import os

# URL to fetch data from the API
url = "https://api.waktusolat.app/v2/solat/KTN01"

def fetch_and_save_data():
    response = requests.get(url)
    data = response.json()
    with open('prayer_times.json', 'w') as f:
        json.dump(data, f)
    return data

def load_data():
    if not os.path.exists('prayer_times.json'):
        return fetch_and_save_data()

    with open('prayer_times.json', 'r') as f:
        data = json.load(f)

    last_updated = datetime.strptime(data['last_updated'], '%Y-%m-%dT%H:%M:%S.%fZ')
    current_date = datetime.now()

    # Check if a month has passed since the last update
    if current_date.month != last_updated.month or current_date.year != last_updated.year:
        data = fetch_and_save_data()
    
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

# Load data
data = load_data()
current_day_prayers = get_current_day_prayers(data['prayers'], datetime.now().day)

# Set up UI
root = tk.Tk()
root.title("Prayer Times")

current_time = tk.StringVar()
next_prayer = tk.StringVar()

data_label = ttk.Label(root, text=f"Location Zone: {data['zone']}")
data_label.pack()

time_label = ttk.Label(root, textvariable=current_time)
time_label.pack()

next_prayer_label = ttk.Label(root, textvariable=next_prayer)
next_prayer_label.pack()

prayer_times_frame = ttk.Frame(root)
prayer_times_frame.pack()

update_prayer_times()
update_ui()

root.mainloop()