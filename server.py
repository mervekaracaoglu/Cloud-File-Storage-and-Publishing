import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, Listbox
import os
import socket
import threading

HOST = "0.0.0.0"
file_directory = ""
PORT = 0
clients = {}
clients_lock = threading.Lock()



def notify(owner, downloader, file): #notify the owner client that someone downloaded the file they uploaded
    global clients
    with clients_lock:
        if owner in clients:
            try:
                owner_socket = clients[owner]
                message = f"NOTIF: {downloader} downloaded your file {file}"
                owner_socket.sendall(message.encode("ascii"))
                listbox.insert(tk.END, f"Notified {owner}: {message}")
                listbox.yview(tk.END)

            except Exception as e:
                listbox.insert(tk.END, f"ERROR notifying: {e}")
                listbox.yview(tk.END)

def admin_data(entry):  #write at admin_data.txt the owner clients and the files they uploaded to keep track

    admin_data_path = os.path.join(file_directory, "ADMIN_DATA.txt")
    with clients_lock:
        try:
            if not os.path.exists(admin_data_path):
                with open(admin_data_path, "w") as a:
                    pass

            with open(admin_data_path, "r") as admin_file:
                lines = admin_file.readlines()

            lines.append(entry + "\n")
            lines = sorted(lines, key=lambda x: x.strip().lower())

            with open(admin_data_path, "w") as admin_file:
                admin_file.writelines(lines)

            listbox.insert(tk.END, f"Updated ADMIN_DATA.txt")
            listbox.yview(tk.END)


        except Exception as e:
            listbox.insert(tk.END, f"Error updating ADMIN_DATA.txt: {e}")
            listbox.yview(tk.END)

def start_server():
    threading.Thread(target=server, daemon=True).start()

def upload(client_socket, client_name, file_name, file_size):

    client_socket.sendall("OK".encode("ascii")) #send client OK to let client know they can upload a file

    unique_filename = f"{client_name}_{file_name}" #make a unique file name to distinguish which owner uploaded which file
    file_path = os.path.join(file_directory, unique_filename)
    total_received = 0
    file_exists = os.path.exists(file_path)

    try:
        if file_exists: #if the file is already uploaded
            client_socket.sendall("OVR".encode("ascii")) #let client know the file is being overwritten
            listbox.insert(tk.END, f"File '{unique_filename}' is being overwritten.")
            listbox.yview(tk.END)
        else:
            client_socket.sendall("NEW".encode("ascii")) #let client know it is a new file

        with open(file_path, "w") as f: #read the file
            while total_received < int(file_size): #receive the file contents from client until it reaches the file size
                data = client_socket.recv(1024).decode("ascii")
                f.write(data)
                total_received += len(data)

        if total_received != int(file_size): #if the received size doesn't equal to the file size
            listbox.insert(tk.END, f"File size mismatch: expected {file_size}, received {total_received}")
            listbox.yview(tk.END)
            Exception(f"File size mismatch: expected {file_size}, received {total_received}")

        else: #if the uplaod is succesfull send client SUCCESS
            client_socket.sendall("SUCCESS".encode("ascii"))

            entry = f"{client_name} uploaded {file_name}"
            admin_data(entry) #add the new file and client to admin.txt
            listbox.insert(tk.END, f"File '{file_name}' uploaded successfully by {client_name}.")
            listbox.yview(tk.END)

    except socket.timeout:
        listbox.insert(tk.END, "Timeout occurred while waiting for data.")
        listbox.yview(tk.END)

        client_socket.sendall("ERROR: Timeout occurred.".encode("ascii"))
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        listbox.insert(tk.END, f"Error uploading file '{file_name}' from {client_name}: {e}")
        listbox.yview(tk.END)
        client_socket.sendall("ERROR: Error occurred during upload.".encode("ascii"))

def send_list(client_socket):

    try:
        client_socket.sendall("OK".encode("ascii"))

        admin_path = os.path.join(file_directory, "ADMIN_DATA.txt")

        with clients_lock:
            if not os.path.exists(admin_path):
                client_socket.sendall("ERROR: ADMIN_DATA.txt not found.".encode("ascii"))
                return

            with open(admin_path, "r") as admin_file: #find the size of the file
                data = admin_file.read()
                data_size = str(len(data))
            client_socket.sendall(data_size.encode("ascii"))

            with open(admin_path, "r") as admin_file: #send the file content in 4096 byte chunks
                while chunk := admin_file.read(4096):
                    client_socket.sendall(chunk.encode("ascii"))

            response = client_socket.recv(1024).decode("ascii") #receive from client if the list was sent successfully
            if response == "SUCCESS":
                listbox.insert(tk.END, "List sent successfully.")
                listbox.yview(tk.END)

            else:
                listbox.insert(tk.END, f"ERROR: {response}")
                listbox.yview(tk.END)



    except Exception as e:
        listbox.insert(tk.END, f"Error sending ADMIN_DATA.txt: {e}")
        listbox.yview(tk.END)
        client_socket.sendall(f"ERROR: {e}".encode("ascii"))

def delete(client_socket, client_name, file_name):

    try:
        if not file_name.endswith(".txt"): #if the file is not named .txt, add .txt
            file_name += ".txt"

        client_socket.sendall("OK".encode("ascii"))

        unique_name = f"{client_name}_{file_name}"
        file_path = os.path.join(file_directory, unique_name)

        if not os.path.exists(file_path):
            client_socket.sendall("ERROR: File does not exist.".encode("ascii"))
            listbox.insert(tk.END, f"File {unique_name} does not exist.")
            listbox.yview(tk.END)

            return

        os.remove(file_path)  #remove the file from file path
        listbox.insert(tk.END, f"File '{file_name}' deleted by {client_name}.")
        listbox.yview(tk.END)

        admin_path = os.path.join(file_directory, "ADMIN_DATA.txt")  #delete the file from admin_data.txt, update the admin_data.txt file
        if os.path.exists(admin_path):
            with open(admin_path, "r") as admin_file:
                lines = admin_file.readlines()
            updated_lines = [line for line in lines if f"{client_name} uploaded {file_name}" not in line]
            with open(admin_path, "w") as admin_file:
                admin_file.writelines(updated_lines)

        listbox.insert(tk.END, "ADMIN_DATA.txt updated.")
        listbox.yview(tk.END)

        client_socket.sendall("SUCCESS".encode("ascii")) #send success to client if the delete operation is successful


    except Exception as e:
        listbox.insert(tk.END, f"Error handling delete request: {e}")
        client_socket.sendall(f"ERROR: {e}".encode("ascii"))

def download(client_socket, owner_name, file_name):

    try:
        unique_filename = f"{owner_name}_{file_name}"
        if not unique_filename.endswith(".txt"):
            unique_filename += ".txt"
        file_path = os.path.join(file_directory, unique_filename)

        if not os.path.exists(file_path):
            client_socket.sendall("ERROR: File does not exist.".encode("ascii"))
            listbox.insert(tk.END, f"File {unique_filename} does not exist.")
            listbox.yview(tk.END)

            return

        client_socket.sendall("OK".encode("ascii"))

        with open(file_path, "r") as f: #find the file size of the file client requested
            data = f.read()
            file_size = len(data)

        client_socket.sendall(str(file_size).encode("ascii")) # Send data size to client


        with open(file_path, "r") as file: # Read contents and send in chunks
            while chunk := file.read(4096):
                client_socket.sendall(chunk.encode("ascii"))


        response = client_socket.recv(1024).decode("ascii") #if its succesfully sent get SUCCESS as response
        if response == "SUCCESS":
            listbox.insert(tk.END, "File sent successfully.")
            listbox.yview(tk.END)

        else:
            listbox.insert(tk.END, f"ERROR: {response}")
            listbox.yview(tk.END)


    except Exception as e:
        listbox.insert(tk.END, f"Error handling download request for '{file_name}': {e}")
        listbox.yview(tk.END)
        client_socket.sendall(f"ERROR: {e}".encode("ascii"))

def client_connection(client_socket, addr):
    global clients

    with client_socket:
        client_name = client_socket.recv(1024).decode() #get clients name from client

        with clients_lock:
            if client_name in clients: #if duplicate name
                client_socket.sendall("INVALID_NAME".encode("ascii"))
                client_socket.close()
                listbox.insert(tk.END, f"User with duplicate name trying to connect: {client_name}. Rejected.")
                listbox.yview(tk.END)
                return

            client_socket.sendall("VALID_NAME".encode("ascii"))
            clients[client_name] = client_socket #if valid name add client to clients dictionary
            listbox.insert(tk.END, f"{client_name} Connected by {addr}")
            listbox.yview(tk.END)

        while True:
            command = client_socket.recv(1024).decode("ascii") #receive command from client for requests

            if not command: #if there is no command from client, client disconnected
                listbox.insert(tk.END, f"{client_name} Disconnected.")
                listbox.yview(tk.END)

                break

            if command == "SA": #ping pong effect between server and client to make sure the client and server are connected
                client_socket.sendall("AS".encode("ascii"))
                continue

            elif command.startswith("UPLOAD"): #UPLOAD request from client with file name and file size
                _, filename, file_size = command.split(" ")
                listbox.insert(tk.END, f"{client_name} sent an UPLOAD request for: {filename}")
                listbox.yview(tk.END)

                upload(client_socket, client_name, filename, file_size)

            elif command == "LIST": #LIST request from client (admin_data.txt)
                listbox.insert(tk.END, f"{client_name} sent an LIST request.")
                listbox.yview(tk.END)

                send_list(client_socket)

            elif command == "DISCONNECT": #DISCONNECT request from client
                with clients_lock:
                    del clients[client_name]
                listbox.insert(tk.END, f"User {client_name} ({addr}) disconnected.")
                listbox.yview(tk.END)

                client_socket.close() #close the socket and return
                return

            elif command.startswith("DELETE"): #DELETE request from client with client name and file name
                _, client_name, file_name = command.split(" ")
                listbox.insert(tk.END, f"User {client_name} sent a DELETE request for: {file_name}")
                listbox.yview(tk.END)

                delete(client_socket, client_name, file_name)

            elif command.startswith("DOWNLOAD"): #DOWNLOAD request from client with owner client name and file name
                _, owner, file = command.split(" ")
                listbox.insert(tk.END, f"User {client_name} sent a DOWNLOAD request for: {file}")
                listbox.yview(tk.END)
                download(client_socket, owner, file)

def server():
    global PORT

    PORT = port_entry.get().strip() #enter the port from server gui
    if not PORT:
        listbox.insert(tk.END, "Port can't be empty.")
        listbox.yview(tk.END)
        return
    elif not PORT.isdigit() or not (49152 <= int(PORT) <= 65535):
        listbox.insert(tk.END, "Port must be a number between 49,152 and 65,535.")
        listbox.yview(tk.END)
        return

    if not file_directory:
        listbox.insert(tk.END, "Please select a file directory.")
        listbox.yview(tk.END)
        return

    listbox.insert(tk.END, f"Starting server on port {PORT}...")
    listbox.yview(tk.END)

    try:
        #create the server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, int(PORT)))
        s.listen()
        listbox.insert(tk.END, f"Server is running on port {PORT}")
        browse_button.config(state="disabled")
        port_entry.config(state="disabled")
        start_button.config(state="disabled")
        end_button.config(state="normal")

        admin_path = os.path.join(file_directory, "ADMIN_DATA.txt")
        if not os.path.exists(admin_path):
            with open(admin_path, "a") as file:  #create admin_data.txt to put the clients and file names in
                pass

        def stop_server():
            try:
                #close the server socket
                s.close()
                listbox.insert(tk.END, "Server stopped successfully.")
                listbox.yview(tk.END)

                with clients_lock:
                    for username, client_socket in clients.items():
                        try:
                            client_socket.sendall("SERVER_SHUTDOWN".encode("ascii"))
                            client_socket.close()
                            listbox.insert(tk.END, f"Disconnected client: {username}")
                        except Exception as e:
                            listbox.insert(tk.END, f"Error disconnecting client {username}: {e}")
                    clients.clear()
                # Update UI elements
                browse_button.config(state="normal")
                port_entry.config(state="normal")
                start_button.config(state="normal")
                end_button.config(state="disabled")

            except Exception as e:
                listbox.insert(tk.END, f"Error stopping server: {e}")
                listbox.yview(tk.END)

        #attach the stop_server function to the Stop Server button
        end_button.config(command=stop_server)
        end_button["state"] = "normal"

        #accept clients in a separate thread
        def accept_clients():
            try:
                while True:
                    conn, addr = s.accept()
                    t = threading.Thread(target=client_connection, args=(conn, addr)) #thread for client connection
                    t.start()
            except OSError:
                listbox.insert(tk.END, "Server socket closed. Stopping accept thread.")
                listbox.yview(tk.END)

        threading.Thread(target=accept_clients, daemon=True).start() #thread for accepting clients, daemon thread runs in the background

    except Exception as e:
        listbox.insert(tk.END, f"Error starting server: {e}")
        listbox.yview(tk.END)

def browse_dir(): #browse directories pick a directory for file operations before connecting to server
    global file_directory
    file_directory = filedialog.askdirectory()
    listbox.insert(tk.END, f"File directory set to: {file_directory}")
    listbox.yview(tk.END)


window = tk.Tk()
window.title("Server")
window.rowconfigure(0, minsize=30, weight=1)
window.columnconfigure(0, minsize=15, weight=1)
window.columnconfigure(1, minsize=35, weight=1)

frm_input = tk.Frame(master=window, relief=tk.RIDGE, borderwidth=3)

port_label = tk.Label(master = frm_input, text="Port:")
port_label.grid(row = 1, column = 0, pady = 5)

port_entry = tk.Entry(master = frm_input, width=20)
port_entry.grid(row = 1, column = 1, pady = 5)

listbox = Listbox(master = window, width=100, height=30)
listbox.grid(row = 0, column = 1 , padx = 10, pady = 10)

start_button = tk.Button(master = frm_input, text="Start Server", command= start_server)
start_button.grid(row = 3, column = 1, pady = (10,0), sticky = "e")

end_button = tk.Button(master = frm_input, text="Stop Server")
end_button.grid(row = 4, column =1, pady = (10,0), sticky = "e")
end_button["state"] = "disabled"  # Initially disabled

frm_data = tk.Frame(master=window, relief=tk.RIDGE, borderwidth=3)

browse_button = tk.Button(window, text="Browse Directory", command= browse_dir, width = 15)
browse_button.grid(row = 0, column = 2, pady = 10, padx = 5)

frm_data.grid(row=1, column=1)

frm_input.grid(row=0, column=0, padx=10, pady=15, ipadx=10, ipady=10)

window.mainloop()