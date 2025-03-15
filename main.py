#!/opt/anaconda3/envs/cyan-client/bin/python
# cyanblog client
# Config:
#   - .env:
#       - PULL_KEY: X-API-KEY header field for viewing locked docs.
#       - PUSH_KEY: X-API-KEY header field for publishing/updating locked docs.
#       - DELETE_KEY: X-API-KEY header field for deleting docs from server.
#
# PromptCraft, 2025. All rights reserved.

import platform
import random
import os
import re
import json
import zipfile
import subprocess
import shutil
import time
import threading
import requests
import datetime
if platform.system() == "Windows":
    import pyreadline3 as readline
else:
    import readline
from dotenv import load_dotenv
from rich import print
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# Specify absolute path
dotenv_path = "/Users/makabaka1880/Documents/2025/dev/cyan-client/.env"
NODE_SERVER_URL = "http://localhost:8001/"
downloads_dir = "downloads"
docs_dir = "/Users/makabaka1880/Documents/2025/dev/cyan-client/docs/"  # Replace with your own path

# Load the .env file
load_dotenv(dotenv_path=dotenv_path)

# API URLs
POST_API_URL = os.getenv("API_URL") + "/post-entry"
UPDATE_API_URL = os.getenv("API_URL") + "/update-entry"
PULL_API_URL = os.getenv("API_URL") + "/req-entry"
UPLOAD_API_URL = os.getenv("API_URL") + "/upload-assets"
DOWNLOAD_API_URL = os.getenv("API_URL") + "/download-assets"
DELETE_API_URL = os.getenv("API_URL") + "/delete-entry"
LIST_API_URL = os.getenv("API_URL") + "/latest-entries"
PUSH_API_KEY = os.getenv("PUSH_KEY")
PULL_API_KEY = os.getenv("PULL_KEY")
DELETE_API_KEY = os.getenv("DELETE_KEY")

readline.set_history_length(1000)
readline.parse_and_bind('tab: complete')

# Observable pointer class to track the current diary entry
class ObservablePointer:
    def __init__(self, initial_value):
        self._value = initial_value
        self._callbacks = []
        
    def add_callback(self, callback):
        self._callbacks.append(callback)

    @property
    def value(self):
        return self._value
        
    @value.setter
    def value(self, new_value):
        self._value = new_value
        for callback in self._callbacks:
            callback(new_value)

# Create observable pointer with initial value as today's date.
pointer = ObservablePointer(datetime.datetime.today().strftime('%Y-%m-%d'))

def on_pointer_change(new_value):
    register_filename()
    
pointer.add_callback(on_pointer_change)

def send_heartbeat():
    response = requests.post(f"{NODE_SERVER_URL}/heartbeat")
    if response.status_code != 200:
        print(f"Failed to send heartbeat: {response.text}")
            
def heartbeat_daemon():
    while True:
        try:
            send_heartbeat()
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with server: {e}")
        time.sleep(10)

# MARK: File watching

class FileEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        register_filename()
        if event.is_directory:
            return
        watched_file = os.path.join(docs_dir, pointer.value, 'entry.md')
        if event.src_path == watched_file:
            print(f"[yellow]File modified: {event.src_path}[/yellow]")

def start_watcher():
    event_handler = FileEventHandler()
    observer = Observer()
    watched_file = os.path.join(docs_dir, pointer.value, 'entry.md')
    observer.schedule(event_handler, watched_file, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def register_filename():
    """Periodically send the current pointer to the Node.js server."""
    try:
        response = requests.post(f"{NODE_SERVER_URL}/register-filename", json={"filename": pointer.value})
        if response.status_code != 200:
            print(f"Failed to register pointer: {response.text}")
    except requests.exceptions.RequestException as e:
        if e.contains("refused"):
            print("[red]Error: Node.js server not running. Please start the server first.[/red]")
        else:
            print(f"Error communicating with server: {e}")

def add_asset(path):
    """Add an asset to the current entry."""
    path = path.replace('\\ ', ' ')
    if not pointer.value:
        print("[red]Error: Pointer not set. Use 'set' command to set the pointer.[/red]")
        return
    if not os.path.exists(path):
        print(f"[red]Error: Asset not found at '{path}'[/red]")
        return
    
    ext = os.path.splitext(path)[-1]
    name = datetime.datetime.today().strftime("%y%m%d") + ''.join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=4))
    unique_filename = f"{name}{ext}"
    dest = os.path.join(docs_dir, pointer.value, 'assets', unique_filename)
    shutil.copyfile(path, dest)
    print(f"[green]Asset '{path}' added successfully to '{pointer.value}'[/green]")
    print(f"[blue]Markdown usage: !\[{path.split('/')[-1]}](/docs/{pointer.value}/assets/{unique_filename})[/blue]")
    
def resolve_file(file):
    """
    If file is None or empty, return pointer.value.
    Otherwise, if file starts with $NOW:
      - If of the form "$NOW-<number>", subtract that many days from today.
      - If of the form "$NOW+'<suffix>'" or "$NOW+\"<suffix>\"", append the suffix.
      - Otherwise, if exactly "$NOW", return today's date.
    Else, return file unchanged.
    """
    if not file:
        return pointer.value
    if file.startswith("$NOW"):
        # Pattern: $NOW-<number> (e.g. "$NOW-1" for yesterday)
        m = re.match(r'^\$NOW-(\d+)$', file)
        if m:
            days = int(m.group(1))
            new_date = datetime.datetime.today() - datetime.timedelta(days=days)
            return new_date.strftime('%Y-%m-%d')
        # Pattern: $NOW+'<suffix>' or $NOW+"<suffix>"
        m = re.match(r"^\$NOW\+\s*'([^']+)'$", file)
        if m:
            suffix = m.group(1)
            return datetime.datetime.today().strftime('%Y-%m-%d') + suffix
        m = re.match(r'^\$NOW\+\s*"([^"]+)"$', file)
        if m:
            suffix = m.group(1)
            return datetime.datetime.today().strftime('%Y-%m-%d') + suffix
        # If file is exactly "$NOW"
        if file == "$NOW":
            return datetime.datetime.today().strftime('%Y-%m-%d')
    return file

def register_filename():
    """Periodically send the current pointer to the Node.js server."""
    try:
        response = requests.post(f"{NODE_SERVER_URL}/register-filename", json={"filename": pointer.value})
        if response.status_code != 200:
            print(f"Failed to register pointer: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with server: {e}")

def send_event(event):
    """Send an event to the Node.js server."""
    try:
        response = requests.post(f"{NODE_SERVER_URL}/client-event", json={"event": event})
        if response.status_code != 200:
            print(f"Failed to send event: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with server: {e}")

# MARK: REPL Commands

def submit_entry(file=None):
    file = resolve_file(file)
    try:
        with open(os.path.join(docs_dir, file, 'entry.md'), "r", encoding='utf-8') as f:
            contents = f.read()
        payload = {
            "filename": file,
            "contents": contents
        }
        headers = {"x-api-key": PUSH_API_KEY}
        response = requests.post(POST_API_URL, json=payload, headers=headers)
        if response.status_code == 201:
            print(f"[green]Entry '{file}' submitted successfully![/green]")
        else:
            print(f"[red]Failed to submit entry ({response.status_code}): {response.text}[/red]")
    except Exception as e:
        print(f"[red]Error submitting entry: {str(e)}[/red]")

def list_entries(limit=None):
    req = LIST_API_URL + "?limit=" + str(limit if limit else 10)
    response = requests.get(req)
    print(response.json())
    
def delete_entry(file):
    file = resolve_file(file)
    response = requests.post(DELETE_API_URL, json={"f": file}, headers={"x-api-key": DELETE_API_KEY})
    if response.status_code == 200:
        print(f"[green]Entry '{file}' deleted successfully![/green]")
    else:
        print(f"[red]Failed to delete entry ({response.status_code}): {response.text}[/red]")
    
def update_entry(file=None):
    file = resolve_file(file)
    try:
        with open(os.path.join(docs_dir, file, 'entry.md'), "r", encoding="utf-8") as f:
            contents = f.read()
        payload = {"filename": file, "contents": contents}
        headers = {"x-api-key": PUSH_API_KEY}
        response = requests.post(UPDATE_API_URL, json=payload, headers=headers)
        if response.status_code == 201:
            print(f"[yellow]Entry '{file}' updated successfully![/yellow]")
        else:
            print(f"[red]Failed to update entry ({response.status_code}): {response.text}[/red]")
    except Exception as e:
        print(f"[red]Error updating entry: {str(e)}[/red]")

def pull_entry(file=None):
    file = resolve_file(file)
    try:
        response = requests.get(PULL_API_URL, params={"d": file}, headers={"x-api-key": PULL_API_KEY})
        if response.status_code == 200:
            data = response.json()
            raw_data = data['data']
            entry_path = os.path.join(docs_dir, file, 'entry.md')
            directory = os.path.dirname(entry_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"[blue]Created directory: {directory}[/blue]")
            with open(entry_path, "w", encoding='utf-8') as f:
                f.write(raw_data)
            print(f"[blue]Entry saved as {file}.md in 'docs' directory[/blue]")
        else:
            print(f"[red]Failed to fetch entry ({response.status_code}): {response.text}[/red]")
    except Exception as e:
        print(f"[red]Error fetching entry: {str(e)}[/red]")

def edit_entry(file=None):
    file = resolve_file(file)
    try:
        print(f"[blue]Opening {file}.md in vim editor...[/blue]")
        subprocess.run(["vim", os.path.join(docs_dir, file, 'entry.md')])
    except FileNotFoundError:
        print("[red]Error: vim is not installed or not found.[/red]")
    except Exception as e:
        print(f"[red]Error opening editor: {str(e)}[/red]")

def set_pointer(new_pointer):
    global pointer
    # Resolve the new pointer value (supporting $NOW variants)
    pointer.value = resolve_file(new_pointer)
    entry_path = os.path.join(docs_dir, pointer.value, 'entry.md')
    if not os.path.exists(entry_path):
        print(f"[red]Warning: '{entry_path}' does not exist! You may want to create or pull the entry.[/red]")
    else:
        print(f"[cyan]Pointer set to {pointer.value}.[/cyan]")

def upload_assets(file=None):
    file = resolve_file(file)
    assets_dir = os.path.join(docs_dir, file, 'assets')
    if not os.path.exists(assets_dir):
        print(f"[red]Assets directory for '{file}' does not exist.[/red]")
        return
    zip_filename = f"{assets_dir}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(assets_dir):
            for fname in files:
                file_path = os.path.join(root, fname)
                zipf.write(file_path, os.path.relpath(file_path, assets_dir))
    with open(zip_filename, 'rb') as zipf:
        files_payload = {'zipfile': ('assets.zip', zipf, 'application/zip')}
        headers = {'x-api-key': PUSH_API_KEY}
        try:
            response = requests.post(f"{UPLOAD_API_URL}/{file}", files=files_payload, headers=headers)
            if response.status_code == 200:
                print(f"[green]Assets successfully uploaded to '{file}'[/green]")
            else:
                print(f"[red]Failed to upload assets: {response.status_code}, {response.text}[/red]")
        except Exception as e:
            print(f"[red]Error uploading zip file: {str(e)}[/red]")
    os.remove(zip_filename)

def download_assets(file=None):
    file = resolve_file(file)
    zip_filename = os.path.join(downloads_dir, 'assets.zip')
    download_url = f"{DOWNLOAD_API_URL}?d={file}"
    try:
        response = requests.get(download_url, headers={'x-api-key': PULL_API_KEY})
        if response.status_code == 200:
            with open(zip_filename, 'wb') as f:
                f.write(response.content)
            print(f"[green]Assets successfully downloaded as '{zip_filename}'[/green]")
            assets_dir = os.path.join(docs_dir, file, 'assets')
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir)
                print(f"[green]Created assets directory at '{assets_dir}'[/green]")
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall(assets_dir)
                print(f"[green]Assets successfully unarchived into '{assets_dir}'[/green]")
            os.remove(zip_filename)
            print(f"[green]Removed the zip file '{zip_filename}' after extraction.[/green]")
        else:
            print(f"[red]Failed to download assets: {response.status_code}, {response.text}[/red]")
    except Exception as e:
        print(f"[red]Error downloading assets: {str(e)}[/red]")

def create_entry(name):
    name = resolve_file(name)
    entry_path = os.path.join(docs_dir, name, 'entry.md')
    if os.path.exists(entry_path):
        print(f"[red]Entry '{name}' already exists![/red]")
    else:
        if not os.path.exists(os.path.dirname(entry_path)):
            os.makedirs(os.path.dirname(entry_path))
            os.makedirs(os.path.join(os.path.dirname(entry_path), 'assets'))
            print(f"[blue]Created directory: {os.path.dirname(entry_path)}[/blue]")
        with open(entry_path, "w", encoding='utf-8') as f:
            f.write(f"""---
title: "{name}"
dateline: {datetime.datetime.today().strftime('%Y-%m-%d')}
locked: true
password: "B3stP@ssw0rd"
---""")
        print(f"[blue]Entry '{name}' created successfully![/blue]")
        print(f"[blue]You can now edit the entry using the 'edit' command.[/blue]")

def refresh():
    send_heartbeat()
    register_filename()
    requests.post(f"{NODE_SERVER_URL}/refresh")

# MARK: Handle REPL commands

def handle_command(user_input):
    register_filename()
    parts = user_input.strip().split(" ", 1)
    command = parts[0].lower()
    file_arg = parts[1].strip() if len(parts) > 1 else None
    if command == "exit":
        print("[yellow]Exiting...[/yellow]")
        quit()
    elif command == "add":
        add_asset(file_arg)
    elif command == "submit":
        submit_entry(file=file_arg)
        refresh()
    elif command == "update":
        update_entry(file=file_arg)
        refresh()
    elif command == "pull":
        pull_entry(file=file_arg)
        refresh()
    elif command == "edit":
        edit_entry(file=file_arg)
        refresh()
    elif command == "ls":
        if platform.system() == 'windows':
            os.system(f"dir {docs_dir}")
        else:
            os.system(f"ls {docs_dir}")
    elif command == "file":
        if file_arg:
            set_pointer(file_arg)
        else:
            print("[red]Usage: file <filename>[/red]")
        refresh()
    elif command == "rm":
        target = resolve_file(file_arg) if file_arg else pointer.value
        os.system(f"rm -rf {docs_dir}{target}")
        print(f"[red]Removed directory: {docs_dir}{target}[/red]")
        refresh()
    elif command == "del":
        target = resolve_file(file_arg) if file_arg else pointer.value
        delete_entry(target)
        refresh()
    elif command == "new":
        if file_arg:
            create_entry(file_arg)
            pointer.value = resolve_file(file_arg)
        else:
            print("[red]Usage: new <filename>[/red]")
        refresh()
    elif command == "list":
        if file_arg:
            list_entries(file_arg)
        else:
            list_entries()
    elif command == "refresh":
        refresh()
    elif command == "upload":
        upload_assets(file=file_arg)
        refresh()
    elif command == "download":
        download_assets(file=file_arg)
        refresh()
    elif command == "help":
        print("[cyan]Commands: submit, update, pull, edit, ls, file, rm, del, new, list, refresh, upload, download, help, exit[/cyan]")
    elif command == "":
        pass
    else:
        print(f"[red]Unknown command: {user_input}[/red]")
    register_filename()

def repl():
    watcher_thread = threading.Thread(target=start_watcher, daemon=True)
    watcher_thread.start()
    while True:
        try:
            user_input = input(f"cyanblog ({pointer.value}) +++> ")
            commands = [i.strip() for i in user_input.split(";")]
            for cmd in commands:
                handle_command(cmd)
        except KeyboardInterrupt:
            print("[yellow]Use 'exit' command to quit.[/yellow]")
        except EOFError:
            print("[yellow]Use 'exit' command to quit.[/yellow]")
        except Exception as e:
            print(f"[red]Error: {str(e)}[/red]")

# MARK: App entrance

if __name__ == "__main__":
    heartbeat_daemon = threading.Thread(target=heartbeat_daemon, daemon=True)
    heartbeat_daemon.start()
    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)
        print(f"[green]Created directory: {downloads_dir}[/green]")
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        print(f"[green]Created directory: {docs_dir}[/green]")
    repl()