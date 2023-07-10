import customtkinter
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import sqlite3
import re
from tkinter import ttk
from tkinter import *


# Connect to the SQLite database
conn = sqlite3.connect('parking2.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS Space (
    Space_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Space_type TEXT,
    Initial_ParkingCharge REAL,
    Extended_ParkingCharge REAL,
    Extended_ParkingTime INTEGER
);''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Ticket (
    Ticket_ID INTEGER PRIMARY KEY AUTOINCREMENT ,
    Space_ID INTEGER,
    FOREIGN KEY (Space_ID) REFERENCES Space(Space_ID)
);''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Vehicle (
    Vehicle_ID TEXT PRIMARY KEY,
    Vehicle_Type TEXT
);''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Pays (
    Ticket_ID INTEGER,
    Vehicle_ID TEXT,
    Amount_Paid REAL,
    Payment_Status TEXT,
    Exit_Time TEXT,
    PRIMARY KEY (Ticket_ID, Vehicle_ID),
    FOREIGN KEY (Ticket_ID) REFERENCES Ticket(Ticket_ID),
    FOREIGN KEY (Vehicle_ID) REFERENCES Vehicle(Vehicle_ID)
);''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Avails (
    Ticket_ID INTEGER,
    Vehicle_ID TEXT,
    Entry_Time TEXT,
    PRIMARY KEY (Ticket_ID, Vehicle_ID),
    FOREIGN KEY (Ticket_ID) REFERENCES Ticket(Ticket_ID),
    FOREIGN KEY (Vehicle_ID) REFERENCES Vehicle(Vehicle_ID)
);''')
 

# Create the main Tkinter window
window = customtkinter.CTk()
window.geometry("450x430+0+0")
window.title("Parking Management System")
customtkinter.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

plate_pattern = re.compile(r'^[A-Z]{3}-\d{3}$')


# Function to record vehicle entry
def vehicletab():
    
    def record_entry():
        
        add_vehicle_window = tk.Toplevel(window, bg = "#3a3a40")
        add_vehicle_window.title("Park Vehicle")

        label_vehicle_id = tk.Label(add_vehicle_window, text="Vehicle ID:" )
        label_vehicle_id.grid(row=1, column=0,padx=2, pady=2)

        entry_vehicle_id = tk.Entry(add_vehicle_window)
        entry_vehicle_id.grid(row=1, column=1,padx=2, pady=2)

        label_vehicle_type = tk.Label(add_vehicle_window, text="Vehicle Type:")
        label_vehicle_type.grid(row=2, column=0, padx=2, pady=2)

        vehicle_types = ["2 Wheeler", "4 Wheeler"]
        entry_vehicle_type = tk.StringVar()
        entry_vehicle_type.set(vehicle_types[0])

        dropdown_vehicle_type = tk.OptionMenu(add_vehicle_window, entry_vehicle_type, *vehicle_types)
        dropdown_vehicle_type.grid(row=2, column=1, padx=2, pady=2)

        def confirm():

            vehicle_id = entry_vehicle_id.get()

            if not vehicle_id:
                messagebox.showerror("Invalid", "Please fill the field.")
                return
            
            if not plate_pattern.match(vehicle_id):
                messagebox.showerror("Invalid", "Vehicle ID is invalid. Please enter a valid ID in the format 'ABC-123'.")
                # Clear the entry field
                entry_vehicle_id.delete(0, tk.END)
                return

            entry_time = datetime.now().strftime("%Y-%d-%m %H:%M:%S")  # Get current local time

            # Retrieve the selected vehicle type
            vehicle_type = entry_vehicle_type.get()


            # Check if the vehicle already exists in the database
            cursor.execute('''
                SELECT Vehicle_ID FROM Vehicle WHERE Vehicle_ID = ?
            ''', (vehicle_id,))
            existing_vehicle = cursor.fetchone()

            if not existing_vehicle:
                # Insert the vehicle into the database if it doesn't exist
                cursor.execute('''
                    INSERT INTO vehicle (Vehicle_ID, Vehicle_Type) VALUES (?, ?)
                ''', (vehicle_id, vehicle_type))
                conn.commit()

            # Check if the vehicle is already parked
            cursor.execute('''
                SELECT Avails.Ticket_ID, Avails.Entry_Time, Ticket.Space_ID
                FROM Avails
                JOIN Ticket ON Avails.Ticket_ID = Ticket.Ticket_ID
                WHERE Avails.Vehicle_ID = ? AND Ticket.Space_ID is NOT NULL
                ORDER BY Avails.Entry_Time DESC
                LIMIT 1
            ''', (vehicle_id,))
            last_parked_vehicle = cursor.fetchone()

            if last_parked_vehicle:
                ticket_id = last_parked_vehicle[0]
                entry_time = last_parked_vehicle[1]
                space_id = last_parked_vehicle[2]

                messagebox.showinfo("Already Parked", f"The vehicle with ID '{vehicle_id}' is already parked.\nTicket ID: {ticket_id}\nEntry Time: {entry_time}\nSpace ID: {space_id}")
            else:
                # Check if there is an available space for the vehicle type
                cursor.execute('''
                    SELECT Space_ID FROM Space
                    WHERE Space_Type = ? AND Space_ID NOT IN (
                        SELECT Space_ID FROM ticket
                    ) 
                    LIMIT 1
                ''', (vehicle_type,))
                available_space = cursor.fetchone() 
                
                if available_space:
                    space_id = available_space[0]

                    cursor.execute('''
                        INSERT INTO Ticket (Space_ID) VALUES (?)
                    ''', (space_id,))
                    ticket_id = cursor.lastrowid

                    cursor.execute('''
                        INSERT INTO Avails (Ticket_ID, Vehicle_ID, Entry_Time) VALUES (?, ?, ?)
                    ''', (ticket_id, vehicle_id, entry_time))

                    cursor.execute('''
                        INSERT INTO Pays (Ticket_ID, Vehicle_ID, Payment_Status) VALUES (?, ?, ?)
                    ''', (ticket_id, vehicle_id, "Unpaid"))
                    
                    cursor.execute('''
                        SELECT Space_Type FROM Space WHERE Space_ID = ?
                     ''', (space_id,))
                    type = cursor.fetchone()

                    if type == "2 Wheeler":
                        cursor.execute('''
                            INSERT INTO Space (Initial_ParkingCharge) VALUES (?)
                        ''', ("50.0"))  
                        messagebox.showinfo("Success", f"Vehicle entry recorded successfully.\nTicket ID: ")
                        
                    elif type == "4 Wheeler":
                        cursor.execute('''
                        INSERT INTO Space (Initial_ParkingCharge) VALUES (?)
                        ''', ("100.0"))  
                        messagebox.showinfo("no", f"Vehicle entry recorded successfully.\nTicket ID: ")
                    
                    cursor.execute('''
                        SELECT Initial_ParkingCharge FROM Space WHERE Space_ID = ?
                     ''', (space_id,))
                    initial_charge = cursor.fetchone()[0]

                    cursor.execute('''
                        UPDATE Pays SET Amount_Paid = ?
                        WHERE Ticket_ID = ? AND Vehicle_ID = ?
                    ''', (initial_charge, ticket_id, vehicle_id))


                    messagebox.showinfo("Success", f"Vehicle entry recorded successfully.\nTicket ID: {ticket_id}")
                else:
                    messagebox.showwarning("No Space", "No available space for the specified vehicle type.")
            conn.commit()
            add_vehicle_window.destroy()

        # Create the confirm button
        button_confirm = tk.Button(add_vehicle_window, text="Confirm", command=confirm)
        button_confirm.grid(row=3, columnspan=2, pady=10)

    def record_exit():
        remove_vehicle_window = tk.Toplevel(window, bg = "#3a3a40")
        remove_vehicle_window.title("Unpark Vehicle")

        label_ticket_id = tk.Label(remove_vehicle_window, text="Ticket ID:")
        label_ticket_id.grid(row=0, column=0)
        entry_ticket_id = tk.Entry(remove_vehicle_window)
        entry_ticket_id.grid(row=0, column=1)

        def confirm2():

            if not entry_ticket_id.get():
                messagebox.showerror("Invalid", "Please fill the field.")
                return
            
            ticket_id = int(entry_ticket_id.get())
            
            cursor.execute("SELECT Vehicle_ID FROM Avails WHERE Ticket_ID = ?", (ticket_id,))
            result = cursor.fetchone()
            if result:
                vehicle_id = result[0]
                exit_time = datetime.now().strftime("%Y-%d-%m %H:%M:%S") # Get current local time
                exittime = datetime.now()

                cursor.execute("SELECT Entry_Time FROM Avails WHERE Vehicle_ID = ? AND Ticket_ID = ?", (vehicle_id,ticket_id))
                result = cursor.fetchone()
                entry_time = datetime.strptime(result[0], '%Y-%d-%m %H:%M:%S')

                duration = exittime - entry_time
                open_time = timedelta(hours=1)# 1 hour(initial hour rate)

                extend = duration - open_time
                hours = int(extend.total_seconds() / 3600)

                cursor.execute('''
                    SELECT Initial_ParkingCharge
                    FROM Space
                    WHERE Space_ID IN (
                    SELECT Space_ID
                    FROM Ticket
                        WHERE Ticket_ID = ?
                    )
                    ''', (ticket_id,))
                
                result1 = cursor.fetchone()

                if result1:
                    initial = result1[0]
                    succeeding = (50 * hours)
                    amount_paid = initial + succeeding

                    # Check if the ticket ID exists in the avails table
                    cursor.execute('''
                        SELECT * FROM Avails JOIN Pays ON Avails.Ticket_ID = Pays.Ticket_ID WHERE Avails.Ticket_ID = ? AND Avails.Vehicle_ID = ? AND Pays.Payment_Status = "Unpaid"
                    ''', (ticket_id,vehicle_id))
                    ticket_exists = cursor.fetchone()
                    
                    if ticket_exists:
                        # Prompt for payment confirmation
                        payment_confirmed = messagebox.askyesno("Payment", f"Total Payment: {amount_paid:.2f}. Confirm payment?")
                        
                        if payment_confirmed:
                            # Update pays table with exit time and ticket details
                            cursor.execute('''
                                UPDATE Pays SET Exit_Time = ?, Amount_Paid = ?, Payment_Status = "Paid"
                                WHERE Ticket_ID = ? AND Vehicle_ID = ?
                            ''', (exit_time, amount_paid, ticket_id, vehicle_id))

                            cursor.execute('''
                                UPDATE Space 
                                SET Extended_ParkingCharge = NULL, Extended_ParkingTime = NULL
                                WHERE Space.Space_ID IN (
                                SELECT Ticket.Space_ID
                                FROM Ticket
                                JOIN Avails ON Ticket.Ticket_ID = Avails.Ticket_ID
                                WHERE Ticket.Ticket_ID = ? AND Avails.Vehicle_ID = ?
                                )
                            ''', (ticket_id, vehicle_id))

                            cursor.execute('''
                                DELETE FROM Ticket
                                WHERE Ticket_ID = ? 
                            ''', (ticket_id,))


                            messagebox.showinfo("Success", "Vehicle exit recorded successfully.")
                        else:
                            cursor.execute('''
                                UPDATE Pays SET Amount_Paid = ?
                                WHERE Ticket_ID = ? AND Vehicle_ID = ?
                            ''', (amount_paid, ticket_id, vehicle_id))

                            cursor.execute('''
                                UPDATE Space 
                                SET Extended_ParkingCharge = ?, Extended_ParkingTime = ?
                                WHERE Space.Space_ID IN (
                                SELECT Ticket.Space_ID
                                FROM Ticket
                                JOIN Avails ON Ticket.Ticket_ID = Avails.Ticket_ID
                                WHERE Ticket.Ticket_ID = ? AND Avails.Vehicle_ID = ?
                                )
                            ''', (succeeding, hours, ticket_id, vehicle_id))

                    else: 
                        messagebox.showinfo("Error", "Ticket does not exist.")
            else:
                messagebox.showinfo("Error", "Ticket does not exist.")
            
            conn.commit()
            remove_vehicle_window.destroy()

        button_confirm = tk.Button(remove_vehicle_window, text="Confirm", command=confirm2)
        button_confirm.grid(row=1, columnspan=2, pady=10)

    def update_vehicle():

        update_vehicle_window = tk.Toplevel(window, bg = "#3a3a40")
        update_vehicle_window.title("Unpark Vehicle")

        label_ticket_id = tk.Label(update_vehicle_window, text="Ticket ID:")
        label_ticket_id.grid(row=0, column=0)
        entry_ticket_id = tk.Entry(update_vehicle_window)
        entry_ticket_id.grid(row=0, column=1)

        def confirm3():
            if not entry_ticket_id.get():
                messagebox.showerror("Invalid", "Please fill the field.")
                return
            
            ticket_id = int(entry_ticket_id.get())
            
            
            cursor.execute('''
                SELECT Ticket_ID FROM Ticket WHERE Ticket_ID = ?
            ''', (ticket_id,))
            existing_id = cursor.fetchone()

            if not existing_id:
                messagebox.showerror("Invalid", "Ticket ID is not found.")
                entry_ticket_id.delete(0, tk.END)
                return
            
            def confirm4(ticket_id):   

                new_vehicle_id = entry_vehicle_id.get()

                if not plate_pattern.match(new_vehicle_id):
                    messagebox.showerror("Invalid", "Vehicle ID is invalid. Please enter a valid ID in the format 'ABC-123'.")
                    # Clear the entry field
                    entry_vehicle_id.delete(0, tk.END)
                    return

                # Retrieve the selected vehicle type
                vehicle_type = entry_vehicle_type.get()

                # Check if the vehicle is already parked
                cursor.execute('''
                    SELECT Avails.Ticket_ID, Avails.Entry_Time, Ticket.Space_ID
                    FROM Avails
                    JOIN Ticket ON Avails.Ticket_ID = Ticket.Ticket_ID
                    WHERE Avails.Vehicle_ID = ? AND Ticket.Space_ID is NOT NULL AND NOT Ticket.Ticket_ID = ?
                    ORDER BY Avails.Entry_Time DESC
                    LIMIT 1
                ''', (new_vehicle_id,ticket_id))
                last_parked_vehicle = cursor.fetchone()

                if last_parked_vehicle:
                    ticket_id = last_parked_vehicle[0]
                    entry_time = last_parked_vehicle[1]
                    space_id = last_parked_vehicle[2]

                    messagebox.showinfo("Already Parked", f"The vehicle with ID '{new_vehicle_id}' is already parked.\nTicket ID: {ticket_id}\nEntry Time: {entry_time}\nSpace ID: {space_id}")
                else:
                    # Check if there is an available space for the vehicle type
                    cursor.execute('''
                        SELECT Space_ID FROM Space
                        WHERE Space_Type = ? AND Space_ID NOT IN (
                            SELECT Space_ID FROM ticket
                        ) 
                        LIMIT 1
                    ''', (vehicle_type,))
                    available_space = cursor.fetchone() 
                    
                    if available_space:
                        space_id = available_space[0]

                        cursor.execute('''
                            UPDATE Ticket SET Space_ID = ?
                            WHERE Ticket_ID = ?
                        ''', (space_id,ticket_id))

                        cursor.execute('''
                        UPDATE Vehicle SET Vehicle_ID = ?, Vehicle_Type = ?
                        WHERE Vehicle_ID IN (
                        SELECT Avails.Vehicle_ID
                        FROM Avails
                        WHERE Avails.Ticket_ID = ?
                        )
                        ''', (new_vehicle_id, vehicle_type, ticket_id))

                        cursor.execute('''
                        UPDATE Avails SET Vehicle_ID = ?
                        WHERE Avails.Ticket_ID = ?
                        
                        ''', (new_vehicle_id, ticket_id))

                        cursor.execute('''
                        UPDATE Pays SET Vehicle_ID = ?
                        WHERE Pays.Ticket_ID = ?
                        
                        ''', (new_vehicle_id, ticket_id))
                
                        exittime = datetime.now()

                        cursor.execute("SELECT Entry_Time FROM Avails WHERE Vehicle_ID = ?", (new_vehicle_id,))
                        result = cursor.fetchone()
                        entry_time = datetime.strptime(result[0], '%Y-%d-%m %H:%M:%S')
                        cursor.execute('''
                        SELECT Initial_ParkingCharge
                        FROM Space
                        WHERE Space_ID IN (
                        SELECT Space_ID
                        FROM Ticket
                            WHERE Ticket_ID = ?
                        )
                        ''', (ticket_id,))
                        result2 = cursor.fetchone()
                        if result2:
                            duration = exittime - entry_time
                            open_time = timedelta(hours=1)# 1 hour(initial hour rate)

                            extend = duration - open_time
                            hours = int(extend.total_seconds() / 3600)
                            initial = result2[0]
                            succeeding = (50 * hours)
                            amount_paid = initial + succeeding

                            cursor.execute('''
                                UPDATE Pays SET Amount_Paid = ?
                                WHERE Ticket_ID = ?
                            ''', (amount_paid, ticket_id))

                        conn.commit()

                        messagebox.showinfo("Success", "Vehicle details updated successfully.")

                    else:
                        messagebox.showwarning("No Space", "No available space for the specified vehicle type.")
                conn.commit()

            add_vehicle_window = tk.Toplevel(window, bg = "#3a3a40")
            add_vehicle_window.title("Edit Vehicle")

            label_vehicle_id = tk.Label(add_vehicle_window, text="Vehicle ID:")
            label_vehicle_id.grid(row=1, column=0,padx=2, pady=2)

            entry_vehicle_id = tk.Entry(add_vehicle_window)
            entry_vehicle_id.grid(row=1, column=1,padx=2, pady=2)

            label_vehicle_type = tk.Label(add_vehicle_window, text="Vehicle Type:")
            label_vehicle_type.grid(row=2, column=0, padx=2, pady=2)

            vehicle_types = ["2 Wheeler", "4 Wheeler"]
            entry_vehicle_type = tk.StringVar()
            entry_vehicle_type.set(vehicle_types[0])

            dropdown_vehicle_type = tk.OptionMenu(add_vehicle_window, entry_vehicle_type, *vehicle_types)
            dropdown_vehicle_type.grid(row=2, column=1, padx=2, pady=2)

            button_confirm = tk.Button(add_vehicle_window, text="Confirm", command=lambda ticket=ticket_id: confirm4(ticket))
            button_confirm.grid(row=3, columnspan=2, pady=10)  

        button_confirm = tk.Button(update_vehicle_window, text="Confirm", command=confirm3)
        button_confirm.grid(row=1, columnspan=2, pady=10)        

    def search_vehicle():

        search_vehicle_window = tk.Toplevel(window, bg = "#3a3a40")
        search_vehicle_window.title("Search Vehicle")

        label_ticket_id = tk.Label(search_vehicle_window, text="Ticket ID:")
        label_ticket_id.grid(row=0, column=0)
        entry_ticket_id = tk.Entry(search_vehicle_window)
        entry_ticket_id.grid(row=0, column=1)
        

        def confirm5():
            if not entry_ticket_id.get():
                messagebox.showerror("Invalid", "Please fill the field.")
                return
            
            ticket_id = int(entry_ticket_id.get())

            cursor.execute('''
                SELECT Ticket_ID FROM Ticket WHERE Ticket_ID = ?
            ''', (ticket_id,))
            existing_id = cursor.fetchone()

            if not existing_id:
                messagebox.showerror("Invalid", "Ticket ID is not found.")
                entry_ticket_id.delete(0, tk.END)
                return
            
            cursor.execute('''
                        SELECT Avails.Vehicle_ID, Avails.Entry_Time, Space.*
                        FROM Avails
                        JOIN Ticket ON Avails.Ticket_ID = Ticket.Ticket_ID
                        JOIN Space ON Ticket.Space_ID = Space.Space_ID
                        WHERE Avails.Ticket_ID = ? AND Ticket.Space_ID IS NOT NULL
                        ORDER BY Avails.Entry_Time DESC
                        LIMIT 1
                    ''', (ticket_id,))
            last_parked_vehicle = cursor.fetchone()
            if last_parked_vehicle:
                exittime = datetime.now()

                cursor.execute("SELECT Entry_Time FROM Avails WHERE Ticket_ID = ?", (ticket_id,))
                result = cursor.fetchone()
                entry_time = datetime.strptime(result[0], '%Y-%d-%m %H:%M:%S')

                duration = exittime - entry_time
                open_time = timedelta(hours=1)# 1 hour(initial hour rate)

                extend = duration - open_time
                space_etime = int(extend.total_seconds() / 3600)
                space_echarge = (50 * space_etime)

                vehicle_id = last_parked_vehicle[0]
                entry_time = last_parked_vehicle[1]
                space_id = last_parked_vehicle[2]
                space_type = last_parked_vehicle[3]
                space_icharge = last_parked_vehicle[4]

                cursor.execute('''
                        UPDATE Space SET Extended_ParkingCharge = ?, Extended_ParkingTime = ?
                        WHERE Space_ID = ?
                        ''', (space_echarge, space_etime, space_id))
                conn.commit()

                messagebox.showinfo("Found Vehicle!", f"The vehicle with ID '{vehicle_id}' is parked at Space ID: {space_id}.\nEntry Time: {entry_time}\nSpace Type: {space_type}\nInitial Charge: {space_icharge}\nExtended Charge: {space_echarge}\nExtended Time: {space_etime}\n")

        button_confirm = tk.Button(search_vehicle_window, text="Confirm", command= confirm5)
        button_confirm.grid(row=3, columnspan=2, pady=10)        

    # Function to check parking space availability
    def check_space_availability():
        # Query the space table to count available spaces for each vehicle type
        cursor.execute('''
            SELECT Space_Type, COUNT(*) AS Available_Spaces
            FROM space
            LEFT JOIN ticket ON space.Space_ID = ticket.Space_ID
            WHERE ticket.Space_ID IS NULL
            GROUP BY Space_Type
        ''')
        
        availability = cursor.fetchall()
        
        if availability:
            availability_message = "Space Availability:\n"
            for space_type, count in availability:
                availability_message += f"{space_type}: {count}\n"
        else:
            availability_message = "No spaces available."
        
        messagebox.showinfo("Availability", availability_message)

    # Create the entry form
    vehicle_tab = ttk.Frame(tab_control)
    tab_control.add(vehicle_tab, text="User")

    frame_entry = tk.LabelFrame(vehicle_tab, text="USER", fg="#39bfa9", font=("Arial", 20), bd=12, relief=tk.GROOVE, bg="#3a3a40")
    frame_entry.place(x=30, y=10, width=420, height=420)

    button_entry = tk.Button(frame_entry, text="Record Entry",  fg= "#FFFFFE", command=record_entry, bg="#39bfa9", width=16, height=4) 
    button_entry.grid(row=4, column=0, pady=20, padx=40)

    button_update = tk.Button(frame_entry, text="Update Vehicle", command=update_vehicle, bg="#39bfa9", width=16, height=4)
    button_update.grid(row=6, column=0, pady=20, padx=40)

    button_exit = tk.Button(frame_entry, text="Record Exit",  fg= "#D7F2ED",  command=record_exit, bg="#BF394F", width=16, height=4) 
    button_exit.grid(row=4, column=1, pady=20, padx=40)

    button_search = tk.Button(frame_entry, text="Search Vehicle", command=search_vehicle, bg="#39bfa9", width=16, height=4) 
    button_search.grid(row=6, column=1, pady=20, padx=40)

    # Create the availability check button
    button_check_availability = tk.Button(frame_entry, text="Check Space Availability", command=check_space_availability, bg="#39bfa9", width=40, height=4)  
    button_check_availability.grid(row=5, columnspan=5, pady=20)


def spacetab():

        def add_2space():
            

            cursor.execute ( '''INSERT INTO Space (Space_Type, Initial_ParkingCharge, Extended_ParkingCharge, Extended_ParkingTime)
                      VALUES (?, ?, ?, ?)''' , ("2 Wheeler","50.0","0","0"))
             
            conn.commit()
            messagebox.showinfo("Success", "Parking Space has been created.")

        def add_4space():
            

            cursor.execute ( '''INSERT INTO Space (Space_Type, Initial_ParkingCharge, Extended_ParkingCharge, Extended_ParkingTime)
                      VALUES (?, ?, ?, ?)''' , ("4 Wheeler","100.0","0","0"))
             
            conn.commit()
            messagebox.showinfo("Success", "Parking Space has been created.")

        def remove_2space():
            cursor.execute('''
            SELECT Space_Type, COUNT(*) AS Available_Spaces
            FROM space
            LEFT JOIN ticket ON space.Space_ID = ticket.Space_ID
            WHERE ticket.Space_ID IS NULL AND Space_Type = "2 Wheeler"
            GROUP BY Space_Type
            ''')
            
            availability = cursor.fetchall()
        
            if availability:

                cursor.execute('''
                    DELETE FROM Space
                    WHERE Space_ID = (
                        SELECT Space_ID
                        FROM Space
                        WHERE Space_ID NOT IN (
                            SELECT Space_ID FROM Ticket
                        ) AND Space_Type = "2 Wheeler"
                        LIMIT 1
                    )
                    ''')
                
                conn.commit()
                messagebox.showinfo("Success", "Parking Space has been removed.")
            else:
                messagebox.showinfo("Error", "There are no more empty spaces.")
        def remove_4space():
            cursor.execute('''
            SELECT Space_Type, COUNT(*) AS Available_Spaces
            FROM space
            LEFT JOIN ticket ON space.Space_ID = ticket.Space_ID
            WHERE ticket.Space_ID IS NULL AND Space_Type = "4 Wheeler"
            GROUP BY Space_Type
            ''')
            
            availability = cursor.fetchall()
        
            if availability:

                cursor.execute('''
                    DELETE FROM Space
                    WHERE Space_ID = (
                        SELECT Space_ID
                        FROM Space
                        WHERE Space_ID NOT IN (
                            SELECT Space_ID FROM Ticket
                        ) AND Space_Type = "4 Wheeler"
                        LIMIT 1
                    )
                    ''')
                
                conn.commit()
                messagebox.showinfo("Success", "Parking Space has been removed.")
            else:
                messagebox.showinfo("Error", "There are no more empty spaces.")

        def parked():
            parked_window = tk.Toplevel(window, bg="#3a3a40")
            parked_window.geometry("890x625+0+0")
            parked_window.title("Parked Vehicles")

            data_frame = tk.Frame(parked_window, bd=12, relief=tk.GROOVE, bg="#3a3a40")
            data_frame.place(x=10, y=10, width=890, height=575)

            frame_entry = tk.Frame(data_frame, bd=11, relief=tk.GROOVE, bg="#3a3a40")
            frame_entry.pack(fill=tk.BOTH, expand=True)

            frame_top = tk.Frame(parked_window, bg="#3a3a40")
            frame_top.pack(side=tk.TOP)

            entry_search = tk.Entry(frame_top)
            entry_search.pack(side=tk.LEFT, padx=10)

            y_scroll = tk.Scrollbar(frame_entry, orient=tk.VERTICAL, bg="#3a3a40")
            x_scroll = tk.Scrollbar(frame_entry, orient=tk.HORIZONTAL, bg="#3a3a40")


            def updatedata():

                cursor.execute('''
                SELECT Avails.Entry_Time, Space.Space_ID
                FROM Avails
                JOIN Ticket ON Avails.Ticket_ID = Ticket.Ticket_ID
                JOIN Space ON Ticket.Space_ID = Space.Space_ID
                WHERE Ticket.Space_ID IS NOT NULL
                ORDER BY Avails.Entry_Time
            ''')
                exittime = datetime.now()
                result = cursor.fetchall()
                for row in result:
                    entry_time = datetime.strptime(row[0], '%Y-%d-%m %H:%M:%S')
                    space_id = row[1]

                    duration = exittime - entry_time
                    open_time = timedelta(hours=1)  # 1 hour (initial hour rate)

                    extend = duration - open_time
                    space_etime = int(extend.total_seconds() / 3600)
                    space_echarge = (50 * space_etime)

                    cursor.execute('''
                        UPDATE Space SET Extended_ParkingCharge = ?, Extended_ParkingTime = ?
                        WHERE Space_ID = ?
                    ''', (space_echarge, space_etime, space_id))

                conn.commit()

            def fetchdata():

                cursor.execute('''
                    SELECT Avails.*, Space.*
                    FROM Avails
                    JOIN Ticket ON Avails.Ticket_ID = Ticket.Ticket_ID
                    JOIN Space ON Ticket.Space_ID = Space.Space_ID
                    WHERE Ticket.Space_ID IS NOT NULL
                    ORDER BY Avails.Entry_Time
                ''')

                result = cursor.fetchall()

                for row in result:
                    ticket_id = row[0]
                    vehicle_id = row[1]
                    entry_time = row[2]
                    space_id = row[3]
                    space_type = row[4]
                    initial_charge = row[5]
                    extended_charge = row[6]
                    extended_time = row[7]

                    table.insert("", "end", values=(ticket_id, vehicle_id, entry_time, space_id, space_type,
                                                    initial_charge, extended_charge, extended_time))

            def search_records():

                search_value = entry_search.get()
                table.delete(*table.get_children())  # Clear the Treeview

                if not search_value:
                    fetchdata()

                cursor.execute('''
                    SELECT Avails.Ticket_ID, Avails.Vehicle_ID, Avails.Entry_Time, Space.Space_ID, Space.Space_Type,
                        Space.Initial_ParkingCharge, Space.Extended_ParkingCharge, Space.Extended_ParkingTime
                    FROM Avails
                    JOIN Ticket ON Avails.Ticket_ID = Ticket.Ticket_ID
                    JOIN Space ON Ticket.Space_ID = Space.Space_ID
                    WHERE Ticket.Space_ID IS NOT NULL
                        AND (Avails.Ticket_ID = ? OR Avails.Vehicle_ID = ? OR Avails.Entry_Time = ?
                            OR Space.Space_ID = ? OR Space.Space_Type = ?)
                    ORDER BY Avails.Entry_Time
                    ''', (search_value, search_value, search_value, search_value, search_value))

                search_result = cursor.fetchall()

                for row in search_result:
                    ticket_id = row[0]
                    vehicle_id = row[1]
                    entry_time = row[2]
                    space_id = row[3]
                    space_type = row[4]
                    initial_charge = row[5]
                    extended_charge = row[6]
                    extended_time = row[7]

                    table.insert("", "end", values=(ticket_id, vehicle_id, entry_time, space_id, space_type,
                                                    initial_charge, extended_charge, extended_time))
            def refresh():
                table.delete(*table.get_children())
                updatedata()
                fetchdata()
                    
            button_entry = tk.Button(frame_top, text="Search", command=search_records)
            button_entry.pack(side=tk.LEFT)
            button_entry = tk.Button(frame_top, text="Refresh", command=refresh)
            button_entry.pack(side=tk.LEFT)

            table = ttk.Treeview(frame_entry, columns=(
            "Ticket ID", "Vehicle ID", "Entry time", "Space ID", "Space Type", "Initial Charge", "Extended Charge", "Extended Time"),
                                        yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
            y_scroll.config(command=table.yview)
            
            x_scroll.config(command=table.xview)

            y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

            table.heading("Ticket ID", text="Ticket ID")
            table.heading("Vehicle ID", text="Vehicle ID")
            table.heading("Entry time", text="Entry time")
            table.heading("Space ID", text="Space ID")
            table.heading("Space Type", text="Space Type")
            table.heading("Initial Charge", text="Initial Charge")
            table.heading("Extended Charge", text="Extended Charge")
            table.heading("Extended Time", text="Extended Time(hr)")

            table['show'] = 'headings'

            table.column("Ticket ID", width=50)
            table.column("Vehicle ID", width=100)
            table.column("Entry time", width=150)
            table.column("Space ID", width=50)
            table.column("Space Type", width=100)
            table.column("Initial Charge", width=100)
            table.column("Extended Charge", width=100)
            table.column("Extended Time", width=100)

            table.pack(fill=tk.BOTH, expand=True)
            table.tag_configure("custom", background="#39bfa9", foreground="#39bfa9")

            refresh()

        def pays():
            pays_window = tk.Toplevel(window, bg="#3a3a40")
            pays_window.geometry("890x625+0+0")
            pays_window.title("Vehicle Tickets")

            data_frame = tk.Frame(pays_window, bd=12, relief=tk.GROOVE, bg="#3a3a40")
            data_frame.place(x=10, y=10, width=890, height=575)

            frame_entry = tk.Frame(data_frame, bd=11, relief=tk.GROOVE, bg="#3a3a40")
            frame_entry.pack(fill=tk.BOTH, expand=True)

            frame_top = tk.Frame(pays_window, bg="#3a3a40")
            frame_top.pack(side=tk.TOP)

            entry_search = tk.Entry(frame_top)
            entry_search.pack(side=tk.LEFT, padx=10)

            y_scroll = tk.Scrollbar(frame_entry, orient=tk.VERTICAL, bg="#3a3a40")
            x_scroll = tk.Scrollbar(frame_entry, orient=tk.HORIZONTAL, bg="#3a3a40")


            def updatedata():

                exittime = datetime.now()
                
                cursor.execute('''
                SELECT Entry_Time, Ticket_ID
                FROM Avails
                ''')
                
                result = cursor.fetchall()
                for row in result:
                    entry_time = datetime.strptime(row[0], '%Y-%d-%m %H:%M:%S')
                    ticket_id = row[1]

                    duration = exittime - entry_time
                    open_time = timedelta(hours=1)# 1 hour(initial hour rate)

                    extend = duration - open_time
                    hours = int(extend.total_seconds() / 3600)

                    cursor.execute('''
                    SELECT Initial_ParkingCharge
                    FROM Space
                    WHERE Space_ID IN (
                    SELECT Space_ID
                    FROM Ticket
                        WHERE Ticket_ID = ?
                    )
                    ''', (ticket_id,))
                    result2 = cursor.fetchone()
                    if result2:
                        initial = result2[0]
                        succeeding = (50 * hours)
                        amount_paid = initial + succeeding

                        cursor.execute('''
                            UPDATE Pays SET Amount_Paid = ?
                            WHERE Ticket_ID = ?
                        ''', (amount_paid, ticket_id))

                    conn.commit()

            def fetchdata():

                cursor.execute('''
                    SELECT Pays.Ticket_ID, Pays.Vehicle_ID, Avails.Entry_Time, Pays.Exit_Time, Pays.Amount_Paid, Pays.Payment_Status
                    FROM Pays 
                    JOIN Avails ON Pays.Ticket_ID = Avails.Ticket_ID AND Pays.Vehicle_ID = Avails.Vehicle_ID
                ''')

                result = cursor.fetchall()

                for row in result:
                    ticket_id = row[0]
                    vehicle_id = row[1]
                    entry_time = row[2]
                    exit_time = row[3]
                    amount_paid = row[4]
                    payment_status = row[5]
        

                    table.insert("", "end", values=(ticket_id, vehicle_id, entry_time, exit_time, amount_paid,
                                                    payment_status))

            def search_records():
                search_value = entry_search.get()
                table.delete(*table.get_children())  # Clear the Treeview

                if not search_value:
                    fetchdata()

                cursor.execute('''
                    SELECT Pays.Ticket_ID, Pays.Vehicle_ID, Avails.Entry_Time, Pays.Exit_Time, Pays.Amount_Paid, Pays.Payment_Status
                    FROM Pays 
                    JOIN Avails ON Pays.Ticket_ID = Avails.Ticket_ID AND Pays.Vehicle_ID = Avails.Vehicle_ID
                    WHERE Pays.Ticket_ID = ? OR Pays.Vehicle_ID = ? OR Avails.Entry_Time = ? OR Pays.Exit_Time = ?
                        OR Pays.Amount_Paid = ? OR Pays.Payment_Status = ?
                    ORDER BY Avails.Entry_Time
                ''', (search_value, search_value, search_value, search_value, search_value, search_value))

                search_result = cursor.fetchall()

                for row in search_result:
                    ticket_id = row[0]
                    vehicle_id = row[1]
                    entry_time = row[2]
                    exit_time = row[3]
                    amount_paid = row[4]
                    payment_status = row[5]

                    table.insert("", "end", values=(ticket_id, vehicle_id, entry_time, exit_time, amount_paid, payment_status))
            def refresh():
                table.delete(*table.get_children())
                updatedata()
                fetchdata()  
            button_entry = tk.Button(frame_top, text="Search", command=search_records)
            button_entry.pack(side=tk.LEFT)
            button_entry = tk.Button(frame_top, text="Refresh", command=refresh)
            button_entry.pack(side=tk.LEFT)           

            table = ttk.Treeview(frame_entry, columns=(
            "Ticket ID", "Vehicle ID", "Entry time", "Exit time", "Amount Paid", "Payment Status"),
                                        yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
            y_scroll.config(command=table.yview)
            
            x_scroll.config(command=table.xview)

            y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

            table.heading("Ticket ID", text="Ticket ID")
            table.heading("Vehicle ID", text="Vehicle ID")
            table.heading("Entry time", text="Entry time")
            table.heading("Exit time", text="Exit time")
            table.heading("Amount Paid", text="Amount Paid")
            table.heading("Payment Status", text="Payment Status")

            table['show'] = 'headings'

            table.column("Ticket ID", width=50)
            table.column("Vehicle ID", width=100)
            table.column("Entry time", width=150)
            table.column("Exit time", width=150)
            table.column("Amount Paid", width=100)
            table.column("Payment Status", width=100)


            table.pack(fill=tk.BOTH, expand=True)

            refresh()

        space_tab = ttk.Frame(tab_control)
        tab_control.add(space_tab, text="Admin")

        frame_entry = tk.LabelFrame(space_tab, text="ADMIN", fg="#39bfa9", font=("Arial", 20), bd=12, relief=tk.GROOVE, bg="#3a3a40")
        frame_entry.place(x=30, y=10, width=420, height=420)

        button_add1 = tk.Button(frame_entry, text="Add 2 Wheeler Space", command=add_2space, bg="#39bfa9", width=20, height=4)
        button_add1.grid(row=3, column=1, pady=10, padx=16)

        button_add2 = tk.Button(frame_entry, text="Add 4 Wheeler Space", command=add_4space, bg="#39bfa9", width=20, height=4)
        button_add2.grid(row=3, column=2, pady=20, padx=16)

        button_add3 = tk.Button(frame_entry, text="Remove 2 Wheeler Space", fg= "#D7F2ED", command=remove_2space, bg="#BF394F", width=20, height=4)
        button_add3.grid(row=4, column=1, pady=20, padx=16)

        button_add4 = tk.Button(frame_entry, text="Remove 4 Wheeler Space", fg= "#D7F2ED",  command=remove_4space, bg="#BF394F", width=20, height=4)
        button_add4.grid(row=4, column=2, pady=20, padx=16)

        button_add5 = tk.Button(frame_entry, text="Show Parked Vehicles", command=parked, bg="#39bfa9", width=20, height=4)
        button_add5.grid(row=5, column=1, pady=20, padx=16)

        button_add6 = tk.Button(frame_entry, text="Show Tickets", command=pays, bg="#39bfa9", width=20, height=4)
        button_add6.grid(row=5, column=2, pady=20, padx=16)


def switch_to_vehicle_tab():
    tab_control.select(0)  # Index 0 corresponds to the Vehicle tab
    tab_control.hide(1)
def switch_to_space_tab():
    tab_control.select(1) 
    tab_control.hide(0)

tab_control = ttk.Notebook(window)
tab_control.pack(fill='both', expand=True)

vehicletab()
spacetab()


# Run the Tkinter event loop
window.mainloop()

# Close the database connection
conn.close()