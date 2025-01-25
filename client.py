import tkinter as tk
from fileinput import filename
from tkinter import filedialog, messagebox, simpledialog, Listbox
import os
import socket
import threading

socket_timeout = 10

TCP_SOCKET = ""
USERNAME = ""


def server_messages():
    try:
        while True:
            message = TCP_SOCKET.recv(1024).decode("ascii") #receive message from server

            if not message: #if there is no message from server, server close unexpectedly, socket is closed and client disconnects
                listbox.insert(tk.END, "Server closed unexpectedly.")
                listbox.yview(tk.END)
                TCP_SOCKET.close()
                disconnect()
                break

            if message.startswith("NOTIF"):  #if the message starts with NOTIF, there is notification from server
                listbox.insert(tk.END, message.replace("NOTIF", "Notification: "))
                listbox.yview(tk.END)

            elif message == "SERVER_SHUTDOWN": #if the message is SERVER_SHUTDOWN, server has shut down, socket is closed and client disconnects
                listbox.insert(tk.END, "Server has shut down. Disconnecting...")
                listbox.yview(tk.END)
                TCP_SOCKET.close()
                disconnect()
                break
            elif message == "AS": #ping pong effect to make sure server and client are not disconnected
                TCP_SOCKET.sendall("SA".encode("ascii"))

            else: #if the message is none of the above, show the message
                listbox.insert(tk.END, message)

    except Exception as e:
        listbox.insert(tk.END, f"Disconnected from server: {e}")
        disconnect()

def select_file():

    file_path = filedialog.askopenfilename(title="Select a file to upload", filetypes=[("Text Files", "*.txt")]) #select a file

    if file_path:

        if not file_path.isascii(): #check if file name contains ascii characters
            listbox.insert(tk.END, "File name contains non-ASCII characters.")
            listbox.yview(tk.END)

            return
        listbox.insert(tk.END, f"Selected file: {file_path}")
        listbox.yview(tk.END)


        with open(file_path, "r") as file: #read the file
            file_content = file.read()
            if not file_content.isascii(): #check if the file content contains ascii characters
                listbox.insert(tk.END, "File contains non-ASCII characters.")
                listbox.yview(tk.END)

                return

        return file_path

    else:
        listbox.insert(tk.END, "No file selected.")
        listbox.yview(tk.END)

def is_valid_ip(ip): #checking the format of the IP
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or not (0 <= int(part) <= 255):
            return False
    return True

def connect():
    global TCP_SOCKET, USERNAME

    server_ip = server_ip_entry.get().strip()
    port = port_entry.get().strip()
    USERNAME = username_entry.get().strip()
    errors = []

    if not server_ip:
        errors.append("Server IP cannot be empty.")

    elif not is_valid_ip(server_ip):
        errors.append("Invalid Server IP format. Must be a valid IPv4 address.")

    if not port:
        errors.append("Port cannot be empty.")

    elif not port.isdigit() or not (49152 <= int(port) <= 65535):
        errors.append("Invalid port number. It must be a number between 49,152 and 65,535.")

    if not USERNAME:
        errors.append("Username cannot be empty.")

    elif not USERNAME.isalnum():
        errors.append("Username must be alphanumeric.")

        # This is because having user named admin could mess up our admin_data.txt file
    elif USERNAME == "ADMIN" or USERNAME =="admin":
        errors.append("The use of ADMIN username is forbidden.")

    if errors:
        text = "  ".join(errors)
        listbox.insert(tk.END, text)
        listbox.yview(tk.END)

        return

    listbox.insert(tk.END, "Attempting to connect.")

    try:
        TCP_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        TCP_SOCKET.settimeout(10)
        TCP_SOCKET.connect((server_ip, int(port)))
        TCP_SOCKET.sendall(USERNAME.encode())
        response = TCP_SOCKET.recv(1024).decode()

        if response == "VALID_NAME":
            listbox.insert(tk.END,f"Connected to server at {server_ip}:{port}")

        elif response == "INVALID_NAME":
            listbox.insert(tk.END,"Username is already in use. Please choose another.")
            return
        listbox.yview(tk.END)

        # GUI widgets get enabled here because without establishing connection first, use of these buttons cause problems
        upload_button["state"] = "normal"
        request_list_button["state"] = "normal"
        disconnect_button["state"] = "normal"
        download_button["state"] = "normal"
        delete_button["state"] = "normal"
        select_directory_button["state"] = "normal"

        connect_button["state"] = "disabled"
        username_entry["state"] = "disabled"
        port_entry["state"] = "disabled"
        server_ip_entry["state"] = "disabled"


    except ConnectionRefusedError:
        listbox.insert(tk.END,"Connection refused. Is the server running?")
        listbox.yview(tk.END)


    except Exception as e:
        listbox.insert(tk.END,f"Connection failed: {e}")
        listbox.yview(tk.END)


def upload():
    try:
        file_path = select_file()

        file_name = os.path.basename(file_path) #find the file name

        with open(file_path, "r") as file: #find the file size
            content = file.read()
            file_size = len(content)

        TCP_SOCKET.sendall(f"UPLOAD {file_name} {file_size}".encode("ascii")) #send UPLOAD command to server
        response = TCP_SOCKET.recv(2).decode("ascii") #receive response from server to check if it is OK to upload file
        if response == "OK":
            response1 = TCP_SOCKET.recv(3).decode( "ascii")  # receive response from server to check if it is a new file or a file will be overwritten

            if response1 == "OVR":
                listbox.insert(tk.END, f"Warning: File '{file_name}' will overwrite an existing file on the server.")
            elif response1 == "NEW":
                listbox.insert(tk.END, f"Uploading new file: '{file_name}'.")

            with open(file_path, "r") as file: #send the file in 4096 byte chunks
                while chunk := file.read(4096):
                    TCP_SOCKET.sendall(chunk.encode("ascii"))

            response2 = TCP_SOCKET.recv(1024).decode("ascii") #receive response from server to check if the file has been uploaded

            if response2 == "SUCCESS": #if file upload is successful the response is SUCCESS
                listbox.insert(tk.END, "File uploaded successfully.")
            else:
                listbox.insert(tk.END, f"ERROR: {response}")

            listbox.yview(tk.END)

    except Exception as e:
        listbox.insert(tk.END, f"Error uploading file: {e}")
        listbox.yview(tk.END)

def select_directory(): #selecting a directory to store files in
    directory = filedialog.askdirectory()
    if directory:
        listbox.insert(tk.END, f"Selected directory: {directory}")
        return directory
    else:
        listbox.insert(tk.END, "No directory selected.")

def request_list(): #requests the admin.txt file which contains all the files uploaded to server and their owners
    try:
        listbox.insert(tk.END, "Requesting file list")
        TCP_SOCKET.sendall("LIST".encode("ascii")) #send LIST request
        received = 0
        buffer = ""
        response = TCP_SOCKET.recv(1024).decode("ascii")
        if response == "OK": #if the response is OK
            file_size = TCP_SOCKET.recv(1024).decode("ascii") #get the file size from server
            while received < int(file_size): #receive the file contents from the server until it reaches the file size
                data = TCP_SOCKET.recv(1024).decode("ascii")
                received += len(data) #the size of the file
                buffer += data #the content of the file

            if received != int(file_size): #if the file size doesn't match the received size
                listbox.insert(tk.END, f"File size mismatch: expected {file_size}, received {received}")
                Exception(f"File size mismatch: expected {file_size}, received {received}")
            else:
                TCP_SOCKET.sendall("SUCCESS".encode("ascii")) #the whole file is received
                listbox.insert(tk.END, "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
                for line in buffer.splitlines(): #show the list in listbox
                    listbox.insert(tk.END, line)
                listbox.insert(tk.END, "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        else:
           listbox.insert(tk.END, f"ERROR: {response}")
    except socket_timeout:
        listbox.insert(tk.END, "Timeout occurred while waiting for data.")
        TCP_SOCKET.sendall("ERROR".encode("ascii"))
    except Exception as e:
        listbox.insert(tk.END, f"Error {e}")
        TCP_SOCKET.sendall("ERROR".encode("ascii"))

def disconnect():
    try:
        if TCP_SOCKET:
            #notify the server about the disconnection
            TCP_SOCKET.sendall("DISCONNECT".encode("ascii"))
            TCP_SOCKET.close()


        #disable button when disconnected
        listbox.insert(tk.END, "Disconnected from server.")
        upload_button["state"] = "disabled"
        request_list_button["state"] = "disabled"
        disconnect_button["state"] = "disabled"
        delete_button["state"] = "disabled"
        download_button["state"] = "disabled"
        delete_button["state"] = "disabled"
        select_directory_button["state"] = "disabled"

        #normal state to establish a new connection
        connect_button["state"] = "normal"
        username_entry["state"] = "normal"
        port_entry["state"] = "normal"
        server_ip_entry["state"] = "normal"

    except Exception as e:
        listbox.insert(tk.END, f"Error during disconnection: {e}")

def delete():

    def confirm_delete():
        file_name = file_name_entry.get().strip() #get the file name to be deleted from the gui

        if not file_name:
            listbox.insert(tk.END, "Error: File name cannot be empty.")
            popup.focus_force() #shift focus to the popup window
            return
        popup.destroy()  #close the pop-up window

        try:

            TCP_SOCKET.sendall(f"DELETE {USERNAME} {file_name}".encode("ascii"))  #send a DELETE request
            response = TCP_SOCKET.recv(1024).decode("ascii")
            if response == "OK": #if the response is OK for DELETE request
                response = TCP_SOCKET.recv(1024).decode("ascii")

                if response == "SUCCESS": #if the file is deleted successfully the response from the server is SUCCESS
                    listbox.insert(tk.END, f"File '{file_name}' deleted successfully.")
                elif response.startswith("ERROR:"):
                    listbox.insert(tk.END, response)
                else:
                    listbox.insert(tk.END, f"ERROR deleting file '{file_name}': {response}")
                listbox.yview(tk.END)


        except Exception as e:
            listbox.insert(tk.END, f"ERROR sending delete request: {e}")
            listbox.yview(tk.END)

    def cancel_delete(): #if delete is cancelled, close the pop up
        popup.destroy()
        return

    #create pop-up window for delete
    popup = tk.Toplevel(window)
    popup.title("Delete File")
    popup.geometry("300x150")
    popup.transient(window)  #keep the pop-up on top of the main window
    popup.grab_set()  # block interactions with the main window

    tk.Label(popup, text="Enter the file name to delete:").pack(pady=10)
    file_name_entry = tk.Entry(popup, width=30)
    file_name_entry.pack(pady=5)

    btn_frame = tk.Frame(popup)
    btn_frame.pack(pady=10)

    delete_button2 = tk.Button(btn_frame, text="Delete", command=confirm_delete)
    delete_button2.pack(side="left", padx=10)

    cancel_button = tk.Button(btn_frame, text="Cancel", command=cancel_delete)
    cancel_button.pack(side="right", padx=10)

    popup.mainloop()

def download():
    file_directory = select_directory() #select a directory to put the file after download

    if not file_directory:
        listbox.insert(tk.END, "Can't proceed with download request when no directory is selected.")
        return

    def confirm_download():
        owner_name = owner_name_entry.get().strip() #get the name of the owner client of the file to be downloaded from gui
        file_name = file_name_entry.get().strip()  #get the name of the file to be downloaded from gui

        if not owner_name or not file_name:
            listbox.insert(tk.END, "Error: Both file name and owner name are required.")
            popup.focus_force()
            return

        elif not owner_name.isalnum() or not file_name.isalnum():
            listbox.insert(tk.END, "Error: Both file name and owner name are must be alphanumeric.")
            popup.focus_force()
            return

        popup.destroy()  #close the pop-up window after getting the valid inputs

        try:
            TCP_SOCKET.sendall(f"DOWNLOAD {owner_name} {file_name}".encode("ascii")) #send DOWNLOAD command to the server

            response = TCP_SOCKET.recv(1024).decode("ascii")
            if response == "OK": #if the server responds OK

                file_size = int(TCP_SOCKET.recv(1024).decode("ascii")) #get the file size from server

                total_received = 0
                path = os.path.join(file_directory, f"{owner_name}_{file_name}.txt")

                with open(path, "w") as f: #receive the file by chunks from server and write the file into the directory client specified
                    while total_received < file_size:
                        chunk = TCP_SOCKET.recv(1024).decode("ascii")
                        f.write(chunk)
                        total_received += len(chunk)


                if total_received != file_size: #if the received file doesn't match the file size
                    listbox.insert(tk.END, f"Error: File size mismatch. Expected {file_size}, received {total_received}.")
                    Exception(f"File size mismatch: expected {file_size}, received {total_received}")
                    return
                else: #the download is successful
                    TCP_SOCKET.sendall("SUCCESS".encode("ascii"))
                    listbox.insert(tk.END, f"Download of file '{file_name}' completed successfully.")

            elif response.startswith("ERROR:"):
                listbox.insert(tk.END, response)
            else:
                listbox.insert(tk.END, f"Unknown server response: {response}")
            listbox.yview(tk.END)


        except Exception as e:
            listbox.insert(tk.END, f"Error during file download: {e}")

        listbox.yview(tk.END)


    def cancel_download():
        popup.destroy()

    #create a pop-up window for input
    popup = tk.Toplevel(window)
    popup.title("Download File")
    popup.geometry("350x200")
    popup.transient(window)
    popup.grab_set()

    tk.Label(popup, text="Enter the uploader's username:").pack(pady=5)
    owner_name_entry = tk.Entry(popup, width=30)
    owner_name_entry.pack(pady=5)

    tk.Label(popup, text="Enter the file name:").pack(pady=5)
    file_name_entry = tk.Entry(popup, width=30)
    file_name_entry.pack(pady=5)

    btn_frame = tk.Frame(popup)
    btn_frame.pack(pady=10)

    proceed_button = tk.Button(btn_frame, text="Proceed", command=confirm_download)
    proceed_button.pack(side="left", padx=10)

    cancel_button = tk.Button(btn_frame, text="Cancel", command=cancel_download)
    cancel_button.pack(side="right", padx=10)

    popup.mainloop()


window = tk.Tk()
window.title("Client Storage System")
window.geometry("600x600")

username_label = tk.Label(window, text="Username:")
username_label.grid(row=0, column=0, padx=5, pady=5)
username_entry = tk.Entry(window)
username_entry.grid(row=0, column=1, padx=5, pady=5)

port_label = tk.Label(window, text="Port:")
port_label.grid(row=1, column=0, padx=5, pady=5)
port_entry = tk.Entry(window)
port_entry.grid(row=1, column=1, padx=5, pady=5)

server_ip_label = tk.Label(window, text="Server IP:")
server_ip_label.grid(row=2, column=0, padx=5, pady=5)
server_ip_entry = tk.Entry(window)
server_ip_entry.grid(row=2, column=1, padx=5, pady=5)

connect_button = tk.Button(window, text="Connect", command=connect)
connect_button.grid(row=0, column=2, padx=5, pady=5)

disconnect_button = tk.Button(window, text="Disconnect", command=disconnect)
disconnect_button.grid(row=0, column=3, padx=5, pady=5)

select_directory_button = tk.Button(window, text="Select Directory", command=select_directory)
select_directory_button.grid(row=2, column=2, padx=5, pady=5)

upload_button = tk.Button(window, text="Upload", command=upload)
upload_button.grid(row=1, column=2, padx=5, pady=5)

delete_button = tk.Button(window, text="Delete", command=delete)
delete_button.grid(row=1, column=3, padx=5, pady=5)

request_list_button = tk.Button(window, text="Request List", command=request_list)
request_list_button.grid(row=3, column=2, padx=5, pady=5)

download_button = tk.Button(window, text="Download", command=download)
download_button.grid(row=2, column=3, columnspan=3, padx=5, pady=5)

listbox = Listbox(window, width=90, height=23)
listbox.grid(row=5, column=0, columnspan=4, rowspan=4, padx=10, pady=(10, 5), sticky="ew")

upload_button["state"] = "disabled"
request_list_button["state"] = "disabled"
disconnect_button["state"] = "disabled"
download_button["state"] = "disabled"
delete_button["state"] = "disabled"
select_directory_button["state"] = "disabled"

window.mainloop()