import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import queue
import time
import webbrowser
from datetime import datetime
from Backend import fetch_skins, tracked_skins, saved_skins
from playwright_sniper import snipe_skin as playwright_snipe
from snipe_auto import snipe_auto as auto_snipe
import os

class ModernButton(ttk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        
    def on_enter(self, e):
        self.state(['pressed'])
        
    def on_leave(self, e):
        self.state(['!pressed'])

class ModernListbox(tk.Listbox):
    def __init__(self, master=None, **kwargs):
        kwargs['selectmode'] = 'single'
        kwargs['activestyle'] = 'none'
        super().__init__(master, **kwargs)
        self.configure(
            font=('Segoe UI', 11),
            borderwidth=0,
            highlightthickness=0,
            background='#2b2b2b',  # Dark background
            foreground='#e0e0e0',  # Light text
            selectbackground='#404040',  # Darker selection
            selectforeground='#ffffff'  # White text for selected items
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        
    def on_enter(self, event):
        self.configure(cursor='hand2')
        
    def on_leave(self, event):
        self.configure(cursor='')

class SkinTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Skin Tracker")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Load interface settings
        self.load_window_settings()
        
        # Set theme colors
        self.colors = {
            'bg': '#2b2b2b',          # Dark background
            'fg': '#e0e0e0',          # Light text
            'accent': '#7289da',       # Discord-like blue
            'hover': '#404040',        # Darker hover
            'button': '#363636',       # Button background
            'button_hover': '#404040', # Button hover
            'highlight': '#bb86fc',    # Purple highlight
            'status_active': '#4CAF50',# Green for active status
            'status_inactive': '#f44336'# Red for inactive status
        }
        
        # Initialize state variables
        self.msg_queue = queue.Queue()
        self.is_tracking = False
        self.is_high_discount_tracking = False
        self.tracked_skins = {}
        self.saved_skins = []
        self.current_skin_data = {}
        self.auto_sniped_skins = set()  # Initialize as a set, not a list
        
        # Load Steam username for auto-buy
        self.steam_username = "zreik.blanc"  # Default
        self.load_steam_username()
        
        # Set up styles and tabs
        self.setup_styles()
        
        # Initialize data storage
        self.tracked_skins = {}
        self.saved_skins = []
        self.auto_sniped_skins = set()  # Initialize as a set, not a list
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure root window
        self.root.configure(bg=self.colors['bg'])
        
        # Dictionary to store current skin data with timestamps
        self.current_skin_data = {}
        self.max_cache_size = 1000  # Maximum number of skins to keep in memory
        self.cache_cleanup_interval = 300  # Cleanup every 5 minutes
        self.last_cleanup_time = time.time()
        
        self.knives_only = tk.BooleanVar(value=False)
        self.knives_max_price_var = tk.StringVar(value="0")
        self.knives_autosnipe = tk.BooleanVar(value=False)
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        
        # Create tabs
        self.tracking_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.high_discount_tab = ttk.Frame(self.notebook, style='Card.TFrame')  # New tab for high discount
        self.tracked_skins_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.saved_skins_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        
        self.notebook.add(self.tracking_tab, text="Live Tracking")
        self.notebook.add(self.high_discount_tab, text="High Discount")
        self.notebook.add(self.tracked_skins_tab, text="Tracking Skins")
        self.notebook.add(self.saved_skins_tab, text="Saved Skins")
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Initialize tracking state
        self.is_tracking = False
        # New high discount tracking state
        self.is_high_discount_tracking = False
        self.high_discount_thread = None
        
        self.update_queue = queue.Queue()
        
        # Setup tabs
        self.setup_tracking_tab()
        self.setup_high_discount_tab()  # Setup the new tab
        self.setup_tracked_skins_tab()
        self.setup_saved_skins_tab()
        
        # Configure text tags for hyperlinks
        self.setup_hyperlink_tags()
        
        # Start queue processing
        self.process_queue()
        
        # Load existing data
        self.load_data()

    def setup_styles(self):
        style = ttk.Style()
        
        # Configure notebook style
        style.configure('TNotebook', background=self.colors['bg'])
        style.configure('TNotebook.Tab',
                       padding=[10, 5],
                       font=('Segoe UI', 11),
                       background=self.colors['button'],
                       foreground=self.colors['fg'])
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['bg'])],
                 foreground=[('selected', self.colors['highlight'])])
        
        # Configure frame style
        style.configure('Card.TFrame', background=self.colors['bg'])
        
        # Configure button style
        style.configure('Modern.TButton',
                       font=('Segoe UI', 11),
                       background=self.colors['button'],
                       foreground=self.colors['fg'])
        style.map('Modern.TButton',
                 background=[('pressed', self.colors['accent']),
                           ('active', self.colors['button_hover'])],
                 foreground=[('pressed', '#ffffff')])
        
        # Configure radiobutton style
        style.configure('Modern.TRadiobutton',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'],
                       font=('Segoe UI', 11))
        
        # Configure label style
        style.configure('Modern.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'],
                       font=('Segoe UI', 11))
                       
        # Configure status label style
        style.configure('Status.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['status_inactive'])

    def setup_tracking_tab(self):
        # Control frame
        control_frame = ttk.Frame(self.tracking_tab, style='Card.TFrame')
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # Left side controls
        left_frame = ttk.Frame(control_frame, style='Card.TFrame')
        left_frame.pack(side='left')
        
        self.track_mode = tk.StringVar(value="all")
        ttk.Radiobutton(left_frame, text="Track All Discounted",
                       variable=self.track_mode, value="all",
                       style='Modern.TRadiobutton').pack(side='left', padx=5)
        ttk.Radiobutton(left_frame, text="Track Specific Only",
                       variable=self.track_mode, value="specific",
                       style='Modern.TRadiobutton').pack(side='left', padx=5)
        
        self.start_button = ModernButton(left_frame, text="Start Tracking",
                                     command=self.toggle_tracking,
                                     style='Modern.TButton')
        self.start_button.pack(side='left', padx=5)
        
        # --- New fetch limit combobox added here ---
        lbl_limit = ttk.Label(left_frame, text="Fetch Limit:", style='Modern.TLabel')
        lbl_limit.pack(side='left', padx=5)
        self.fetch_limit_var = tk.StringVar(value="50")
        limit_combo = ttk.Combobox(
            left_frame,
            textvariable=self.fetch_limit_var,
            values=["50", "100", "250", "500", "1000"],
            width=5,
            state="readonly"
        )
        limit_combo.pack(side='left', padx=5)
        self.knives_button = ModernButton(left_frame, text="Configs", command=self.open_knives_config_dialog, style='Modern.TButton')
        self.knives_button.pack(side='left', padx=5)
        # --- End new widget ---
        
        # Right side status
        status_frame = ttk.Frame(control_frame, style='Card.TFrame')
        status_frame.pack(side='right', padx=10)
        
        # Create status indicator
        self.status_label = ttk.Label(
            status_frame,
            text="●",
            font=('Segoe UI', 14),
            style='Status.TLabel'
        )
        self.status_label.pack(side='left', padx=2)

        # Output area with custom font and colors
        self.output_text = scrolledtext.ScrolledText(
            self.tracking_tab,
            height=20,
            font=('Segoe UI', 11),
            background=self.colors['bg'],
            foreground=self.colors['fg'],
            insertbackground=self.colors['fg']  # Cursor color
        )
        self.output_text.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_high_discount_tab(self):
        # Control frame with input and button
        control_frame = ttk.Frame(self.high_discount_tab, style='Card.TFrame')
        control_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(control_frame, text="Minimum Discount (%)", style='Modern.TLabel').pack(side='left', padx=5)
        self.high_discount_entry = ttk.Entry(control_frame, font=('Segoe UI', 11), width=5)
        self.high_discount_entry.pack(side='left', padx=5)
        self.high_discount_entry.insert(0, "50")  # default value
        
        self.high_discount_button = ModernButton(control_frame, text="Start High Discount Tracking",
                                                 command=self.toggle_high_discount_tracking,
                                                 style='Modern.TButton')
        self.high_discount_button.pack(side='left', padx=5)
        
        # ScrolledText widget to display high discount skins
        self.high_discount_output = scrolledtext.ScrolledText(
            self.high_discount_tab,
            height=20,
            font=('Segoe UI', 11),
            background=self.colors['bg'],
            foreground=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.high_discount_output.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_tracked_skins_tab(self):
        # Control buttons
        button_frame = ttk.Frame(self.tracked_skins_tab, style='Card.TFrame')
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ModernButton(button_frame, text="Add New Skin",
                  command=self.show_add_skin_dialog,
                  style='Modern.TButton').pack(side='left', padx=5)
        ModernButton(button_frame, text="Remove Selected",
                  command=self.remove_tracked_skin,
                  style='Modern.TButton').pack(side='left', padx=5)
        ModernButton(button_frame, text="Auto Buy",
                     command=self.autobuy_tracked_skin,
                     style='Modern.TButton').pack(side='left', padx=5)
        ModernButton(button_frame, text="Remove Auto Buy",
                     command=self.remove_autobuy_tracked_skin,
                     style='Modern.TButton').pack(side='left', padx=5)
        
        # Tracked skins list with modern styling
        self.tracked_listbox = ModernListbox(self.tracked_skins_tab, height=15)
        self.tracked_listbox.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_saved_skins_tab(self):
        # Saved skins list with modern styling
        self.saved_listbox = ModernListbox(self.saved_skins_tab, height=15)
        self.saved_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        ModernButton(self.saved_skins_tab, text="Remove Selected",
                  command=self.remove_saved_skin,
                  style='Modern.TButton').pack(pady=5)
        
        # Details text with modern styling
        self.details_text = scrolledtext.ScrolledText(
            self.saved_skins_tab,
            height=8,
            font=('Segoe UI', 11),
            background=self.colors['bg'],
            foreground=self.colors['fg'],
            insertbackground=self.colors['fg']  # Cursor color
        )
        self.details_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.saved_listbox.bind('<<ListboxSelect>>', self.show_saved_skin_details)

    def setup_hyperlink_tags(self):
        # Configure hyperlink style for tracking output with smooth transition
        self.output_text.tag_configure("hyperlink",
                                     foreground=self.colors['highlight'],
                                     font=('Segoe UI', 11, 'underline'))
        self.output_text.tag_bind("hyperlink", "<Enter>",
                                lambda e: self.output_text.configure(cursor="hand2"))
        self.output_text.tag_bind("hyperlink", "<Leave>",
                                lambda e: self.output_text.configure(cursor=""))
        
        # Configure hyperlink style for saved skins details
        self.details_text.tag_configure("hyperlink",
                                      foreground=self.colors['highlight'],
                                      font=('Segoe UI', 11, 'underline'))
        self.details_text.tag_bind("hyperlink", "<Enter>",
                                 lambda e: self.details_text.configure(cursor="hand2"))
        self.details_text.tag_bind("hyperlink", "<Leave>",
                                 lambda e: self.details_text.configure(cursor=""))

    def load_data(self):
        # Load tracked skins
        try:
            with open('tracked_skins.json', 'r') as f:
                self.tracked_skins = json.load(f)
                global tracked_skins
                tracked_skins.clear()  # Clear existing data
                tracked_skins.update(self.tracked_skins)  # Update with loaded data
            self.update_tracked_skins_list()
        except FileNotFoundError:
            self.tracked_skins = {}
            tracked_skins.clear()
        except Exception as e:
            print(f"Error loading tracked skins: {e}")
            self.tracked_skins = {}
            tracked_skins.clear()
        
        # Load saved skins
        try:
            with open('saved_skins.json', 'r') as f:
                self.saved_skins = json.load(f)
                global saved_skins
                saved_skins.clear()  # Clear existing data
                saved_skins.extend(self.saved_skins)  # Update with loaded data
            self.update_saved_skins_list()
        except FileNotFoundError:
            self.saved_skins = []
            saved_skins.clear()
        except Exception as e:
            print(f"Error loading saved skins: {e}")
            self.saved_skins = []
            saved_skins.clear()

    def update_tracked_skins_list(self):
        self.tracked_listbox.delete(0, tk.END)
        for skin, info in self.tracked_skins.items():
            threshold = info["threshold"]
            track_type = info["type"]
            display = f"{skin} ({track_type.capitalize()}: {threshold}{'%' if track_type == 'discount' else 'TL'})"
            if info.get("AutoBuy", 0) == 1:
                quantity = info.get("Quantity")
                if quantity is not None:
                    display += f" [Auto Buy Enabled, Remaining: {quantity}]"
                else:
                    display += " [Auto Buy Enabled]"
            self.tracked_listbox.insert(tk.END, display)

    def update_saved_skins_list(self):
        self.saved_listbox.delete(0, tk.END)
        for skin in self.saved_skins:
            self.saved_listbox.insert(tk.END, skin['name'])

    def show_saved_skin_details(self, event):
        selection = self.saved_listbox.curselection()
        if selection:
            skin = self.saved_skins[selection[0]]
            self.details_text.delete(1.0, tk.END)
            
            # Add regular details
            self.details_text.insert(tk.END, f"Name: {skin['name']}\n")
            self.details_text.insert(tk.END, f"Float: {skin['float']}\n")
            self.details_text.insert(tk.END, f"Price: {skin['price']} TL\n")
            self.details_text.insert(tk.END, f"Steam Price: {skin['steam_price']}$\n")
            self.details_text.insert(tk.END, f"Discount: {skin['discount']}%\n")
            self.details_text.insert(tk.END, "Link: ")
            
            # Add clickable link
            link_start = self.details_text.index("end-1c")
            self.details_text.insert(tk.END, "Click Here", "hyperlink")
            link_end = self.details_text.index("end-1c")
            self.details_text.tag_add("hyperlink", link_start, link_end)
            
            # Bind click event for this specific link
            self.details_text.tag_bind("hyperlink", "<Button-1>",
                                     lambda e, url=skin['link']: webbrowser.open(url))
            
            self.details_text.insert(tk.END, f"\nSaved on: {skin['saved_time']}")

    def show_add_skin_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Skin")
        dialog.geometry("400x550")
        
        ttk.Label(dialog, text="Weapon Name (e.g., AK-47):", style='Modern.TLabel').pack(pady=5)
        weapon_entry = ttk.Entry(dialog, font=('Segoe UI', 11))
        weapon_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Skin Name (e.g., Asiimov):", style='Modern.TLabel').pack(pady=5)
        skin_entry = ttk.Entry(dialog, font=('Segoe UI', 11))
        skin_entry.pack(pady=5)
        
        track_type = tk.StringVar(value="discount")
        ttk.Radiobutton(dialog, text="Track by Discount",
                       variable=track_type, value="discount",
                       style='Modern.TRadiobutton').pack(pady=5)
        ttk.Radiobutton(dialog, text="Track by Price",
                       variable=track_type, value="price",
                       style='Modern.TRadiobutton').pack(pady=5)
        
        ttk.Label(dialog, text="Threshold (% or TL):", style='Modern.TLabel').pack(pady=5)
        threshold_entry = ttk.Entry(dialog, font=('Segoe UI', 11))
        threshold_entry.pack(pady=5)
        
        # Wear condition
        ttk.Label(dialog, text="Wear Condition:").pack(pady=5)
        wear_var = tk.StringVar(value="all")
        conditions = [
            ("All Conditions", "all"),
            ("Factory New", "Factory New"),
            ("Minimal Wear", "Minimal Wear"),
            ("Field-Tested", "Field-Tested"),
            ("Well-Worn", "Well-Worn"),
            ("Battle-Scarred", "Battle-Scarred")
        ]
        
        for text, value in conditions:
            ttk.Radiobutton(dialog, text=text, variable=wear_var, value=value).pack()

        def add_skin():
            weapon = weapon_entry.get().strip()
            skin = skin_entry.get().strip()
            try:
                threshold = float(threshold_entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number for threshold")
                return
            
            if not weapon or not skin:
                messagebox.showerror("Error", "Please fill in all fields")
                return
            
            wear_choice = wear_var.get()
            if wear_choice == "all":
                wear_conditions = [
                    "(Factory New)",
                    "(Minimal Wear)",
                    "(Field-Tested)",
                    "(Well-Worn)",
                    "(Battle-Scarred)"
                ]
            else:
                wear_conditions = [f"({wear_choice})"]
            
            try:
                # Add new skins
                for condition in wear_conditions:
                    full_name = f"{weapon} | {skin} {condition}"
                    skin_data = {
                        "type": track_type.get(),
                        "threshold": threshold,
                        "AutoBuy": 0
                    }
                    self.tracked_skins[full_name] = skin_data
                
                # Save to file
                self.save_tracked_skins()
                self.update_tracked_skins_list()
                dialog.destroy()
                messagebox.showinfo("Success", "Skin(s) added successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add skin(s): {str(e)}")
                self.load_data()

        ttk.Button(dialog, text="Add Skin", command=add_skin).pack(pady=20)

    def remove_tracked_skin(self):
        selection = self.tracked_listbox.curselection()
        if selection:
            skin_name = list(self.tracked_skins.keys())[selection[0]]
            if skin_name in self.tracked_skins:  # Verify the key exists
                # Store the skin data in case we need to restore it
                old_data = self.tracked_skins[skin_name]
                del self.tracked_skins[skin_name]
                
                try:
                    self.save_tracked_skins()
                    self.update_tracked_skins_list()
                    messagebox.showinfo("Success", "Skin removed from tracking")
                except Exception as e:
                    # Restore the skin if saving failed
                    self.tracked_skins[skin_name] = old_data
                    self.update_tracked_skins_list()
                    messagebox.showerror("Error", f"Failed to remove skin: {str(e)}")

    def show_autobuy_quantity_dialog(self, skin_name):
        dialog = tk.Toplevel(self.root)
        dialog.title("Auto Buy Quantity")
        dialog.geometry("300x120")
        ttk.Label(dialog, text=f"Enter quantity to purchase for {skin_name}:").pack(pady=10)
        quantity_entry = ttk.Entry(dialog, font=('Segoe UI', 11))
        quantity_entry.pack(pady=5)
        result = {"quantity": None}

        def on_ok():
            try:
                q = int(quantity_entry.get())
                result["quantity"] = q
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number.")
                return
            dialog.destroy()

        ok_button = ttk.Button(dialog, text="OK", command=on_ok, style='Modern.TButton')
        ok_button.pack(pady=10)
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result["quantity"]

    def autobuy_tracked_skin(self):
        selection = self.tracked_listbox.curselection()
        if selection:
            skin_name = list(self.tracked_skins.keys())[selection[0]]
            if skin_name in self.tracked_skins:
                quantity = self.show_autobuy_quantity_dialog(skin_name)
                if quantity is None:
                    return
                self.tracked_skins[skin_name]["AutoBuy"] = 1
                self.tracked_skins[skin_name]["Quantity"] = quantity
                try:
                    self.save_tracked_skins()
                    self.update_tracked_skins_list()
                    messagebox.showinfo("Success", f"Auto Buy enabled for {skin_name} (Quantity: {quantity})!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update skin: {str(e)}")
            else:
                messagebox.showerror("Error", "Selected skin not found.")
        else:
            messagebox.showwarning("Warning", "Please select a skin to enable Auto Buy.")

    def remove_autobuy_tracked_skin(self):
        selection = self.tracked_listbox.curselection()
        if selection:
            skin_name = list(self.tracked_skins.keys())[selection[0]]
            if skin_name in self.tracked_skins:
                self.tracked_skins[skin_name]["AutoBuy"] = 0
                try:
                    self.save_tracked_skins()
                    self.update_tracked_skins_list()
                    messagebox.showinfo("Success", f"Auto Buy disabled for {skin_name}!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update skin: {str(e)}")
            else:
                messagebox.showerror("Error", "Selected skin not found.")
        else:
            messagebox.showwarning("Warning", "Please select a skin to disable Auto Buy.")

    def remove_saved_skin(self):
        selection = self.saved_listbox.curselection()
        if selection:
            try:
                # Store the removed skin in case we need to restore it
                removed_skin = self.saved_skins.pop(selection[0])
                
                try:
                    self.save_saved_skins()
                    self.update_saved_skins_list()
                    self.details_text.delete(1.0, tk.END)
                    messagebox.showinfo("Success", "Skin removed from saved list")
                except Exception as e:
                    # Restore the skin if saving failed
                    self.saved_skins.insert(selection[0], removed_skin)
                    self.update_saved_skins_list()
                    messagebox.showerror("Error", f"Failed to remove skin: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove skin: {str(e)}")
                self.load_data()

    def toggle_tracking(self):
        if not self.is_tracking:
            self.is_tracking = True
            self.start_button.configure(text="Stop Tracking")
            self.status_label.configure(foreground=self.colors['status_active'])
            self.tracking_thread = threading.Thread(target=self.track_skins, daemon=True)
            self.tracking_thread.start()
        else:
            self.is_tracking = False
            self.start_button.configure(text="Start Tracking")
            self.status_label.configure(foreground=self.colors['status_inactive'])

    def toggle_high_discount_tracking(self):
        if not self.is_high_discount_tracking:
            try:
                threshold = float(self.high_discount_entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid discount percentage")
                return
            self.high_discount_threshold = threshold
            self.is_high_discount_tracking = True
            self.high_discount_button.configure(text="Stop High Discount Tracking")
            self.high_discount_thread = threading.Thread(target=self.track_high_discount, daemon=True)
            self.high_discount_thread.start()
        else:
            self.is_high_discount_tracking = False
            self.high_discount_button.configure(text="Start High Discount Tracking")

    def cleanup_skin_cache(self, force=False):
        """Clean up old entries from the skin cache"""
        current_time = time.time()
        
        # Only cleanup if forced or enough time has passed since last cleanup
        if not force and (current_time - self.last_cleanup_time < self.cache_cleanup_interval):
            return
            
        # If cache size exceeds limit, remove oldest entries
        if len(self.current_skin_data) > self.max_cache_size:
            # Sort entries by timestamp
            sorted_entries = sorted(
                self.current_skin_data.items(),
                key=lambda x: x[1].get('timestamp', 0)
            )
            
            # Remove oldest entries until we're under the limit
            entries_to_remove = len(sorted_entries) - self.max_cache_size
            for listing_no, _ in sorted_entries[:entries_to_remove]:
                del self.current_skin_data[listing_no]
        
        self.last_cleanup_time = current_time

    def track_skins(self):
        while self.is_tracking:
            try:
                # Use the selected fetch limit from the combobox
                skins = fetch_skins(limit=int(self.fetch_limit_var.get()))
                # Clear previous skins from the output area in the UI thread
                self.root.after(0, lambda: self.output_text.delete('1.0', tk.END))
                
                # Run cache cleanup
                self.cleanup_skin_cache()
                
                for skin in skins:
                    if not self.is_tracking:
                        break
                        
                    try:
                        discount = float(skin.get("discountRate", 0))
                        listing_no = skin.get("listingNo")
                        skin_name = skin.get("name", "Unknown Skin")
                        float_value = skin.get('info', {}).get('float', "N/A")
                        category = skin.get('info', {}).get('category', "N/A")
                        slug = skin.get("slug", "N/A")
                        buy_link = f"https://www.bynogame.com/en/games/cs2-skin/{slug}?id={listing_no}"
                        status = skin.get("status", "N/A")
                        
                        if status == 2 or status == 3:  # Skip sold items
                            continue
                            
                        if self.knives_only.get():
                            if category != "Knives":
                                continue
                            try:
                                price = float(skin.get("price"))
                            except (ValueError, TypeError):
                                # Skip if price is invalid
                                continue
                            
                            try:
                                max_price = float(self.knives_max_price_var.get())
                            except Exception:
                                max_price = 0
                                
                            if max_price > 0 and price > max_price:
                                continue
                                
                            if self.knives_autosnipe.get():
                                if listing_no not in self.auto_sniped_skins:
                                    self.auto_sniped_skins.add(listing_no)
                                    success, auto_msg = auto_snipe(buy_link, listing_no, target_option=self.steam_username, quantity=None)
                                    print(f"[DEBUG] Knives Auto sniping executed for {listing_no}: {auto_msg}")
                                    self.auto_sniped_skins.discard(listing_no)
                                continue
                        else:
                            try:
                                price = float(skin.get("price"))
                            except (ValueError, TypeError):
                                price = 0
                        steam_price = skin.get("listingPriceUsd", "N/A")
                        
                        if self.track_mode.get() == "specific":
                            matched_tracker = None
                            matched_key = None
                            for tracked_skin, track_info in self.tracked_skins.items():
                                if tracked_skin.lower() in skin_name.lower():
                                    if (track_info["type"] == "discount" and discount >= track_info["threshold"]) or (track_info["type"] == "price" and price <= track_info["threshold"]):
                                        matched_tracker = track_info
                                        matched_key = tracked_skin
                                        break
                            if matched_tracker is None:
                                continue
                        else:
                            if discount <= 0:
                                continue
                        
                        if self.track_mode.get() == "specific" and matched_tracker.get("AutoBuy", 0) == 1:
                            if listing_no not in self.auto_sniped_skins:
                                self.auto_sniped_skins.add(listing_no)
                                current_quantity = matched_tracker.get("Quantity", 0)
                                success, auto_msg = auto_snipe(buy_link, listing_no, target_option=self.steam_username, quantity=current_quantity)
                                print(f"[DEBUG] Auto sniping executed for {listing_no}: {auto_msg}")
                                if success:
                                    new_quantity = current_quantity - 1
                                    if new_quantity <= 0:
                                        del self.tracked_skins[matched_key]
                                    else:
                                        matched_tracker["Quantity"] = new_quantity
                                    self.save_tracked_skins()
                                    self.update_tracked_skins_list()
                                    # Remove the listing from auto_sniped_skins so it can be retried if quantity remains
                                    self.auto_sniped_skins.discard(listing_no)
                        
                        # Store the skin data with timestamp
                        self.current_skin_data[listing_no] = {
                            "name": skin_name,
                            "float": float_value,
                            "price": price,
                            "steam_price": steam_price,
                            "discount": discount,
                            "link": buy_link,
                            "timestamp": time.time()  # Add timestamp for cache management
                        }
                        
                        # Create message with clickable link and quick save button
                        message_parts = {
                            "header": f"\n{datetime.now().strftime('%H:%M:%S')} - {'Match Found' if self.track_mode.get() == 'specific' else 'Discount'}\n",
                            "details": f"{skin_name}\nFloat: {float_value}\nPrice: {price:.2f}TL\nSteam Price: {steam_price}$\nDiscount: {discount}%\nID: {listing_no}\nLink: ",
                            "link": ("Click Here", buy_link),
                            "save_button": ("Quick Save", listing_no)  # New save button
                        }
                        
                        self.update_queue.put(("message", message_parts))
                        
                    except Exception as e:
                        print(f"Error processing skin: {e}")
                        continue
                
                time.sleep(5)  # refresh rate
                
            except Exception as e:
                print(f"Error fetching skins: {e}")
                time.sleep(5)

    def track_high_discount(self):
        while self.is_high_discount_tracking:
            try:
                # Use the selected fetch limit from the combobox
                skins = fetch_skins(limit=int(self.fetch_limit_var.get()))
                # Clear output for high discount tab in the UI thread
                self.root.after(0, lambda: self.high_discount_output.delete('1.0', tk.END))
                for skin in skins:
                    try:
                        discount = float(skin.get("discountRate", 0))
                        if discount < self.high_discount_threshold:
                            continue
                        listing_no = skin.get("listingNo")
                        skin_name = skin.get("name", "Unknown Skin")
                        float_value = skin.get('info', {}).get('float', "N/A")
                        price = skin.get("price", 0)
                        steam_price = skin.get("listingPriceUsd", "N/A")
                        slug = skin.get("slug", "N/A")
                        buy_link = f"https://www.bynogame.com/en/games/cs2-skin/{slug}?id={listing_no}"
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        
                        # Save skin data so quick save can work
                        self.current_skin_data[listing_no] = {
                            "name": skin_name,
                            "float": float_value,
                            "price": price,
                            "steam_price": steam_price,
                            "discount": discount,
                            "link": buy_link,
                            "timestamp": time.time()  # Add timestamp for cache management
                        }
                        
                        message_parts = {
                            "header": f"\n{timestamp} - High Discount Skin\n",
                            "details": f"{skin_name}\nFloat: {float_value}\nPrice: {price:.2f}TL\nSteam Price: {steam_price}$\nDiscount: {discount}%\nID: {listing_no}\nLink: ",
                            "link": ("Click Here", buy_link),
                            "save_button": ("Quick Save", listing_no)
                        }
                        self.update_queue.put(("high_discount", message_parts))
                        
                    except Exception as e:
                        print(f"Error processing high discount skin: {e}")
                        continue
                time.sleep(5)
            except Exception as e:
                print(f"Error fetching high discount skins: {e}")
                time.sleep(5)

    def process_queue(self):
        try:
            while True:
                message_type, content = self.update_queue.get_nowait()
                
                if message_type == "message":
                    # Normal tracking output
                    self.output_text.insert(tk.END, content["header"])
                    self.output_text.insert(tk.END, content["details"])
                    
                    # Update link handling
                    link_text, url = content["link"]
                    link_start = self.output_text.index("end-1c")
                    self.output_text.insert(tk.END, link_text, "hyperlink")
                    link_end = self.output_text.index("end-1c")
                    tag_name = f"link_{link_start}"
                    self.output_text.tag_add(tag_name, link_start, link_end)
                    self.output_text.tag_configure(tag_name,
                                                foreground=self.colors['highlight'],
                                                underline=1)
                    self.output_text.tag_bind(tag_name, "<Button-1>",
                                           lambda e, url=url: webbrowser.open(url))
                    
                    # Update buttons with corrected selectors
                    self.output_text.insert(tk.END, " | ")
                    
                    # Quick Save button
                    save_text, listing_no = content["save_button"]
                    save_start = self.output_text.index("end-1c")
                    self.output_text.insert(tk.END, save_text, "save_button")
                    save_end = self.output_text.index("end-1c")
                    save_tag = f"save_{save_start}"
                    self.output_text.tag_add(save_tag, save_start, save_end)
                    self.output_text.tag_configure(save_tag,
                                                foreground=self.colors['accent'],
                                                underline=1)
                    self.output_text.tag_bind(save_tag, "<Button-1>",
                                           lambda e, id=listing_no: self.quick_save_skin(id))
                    
                    # Snipe button with updated handling
                    self.output_text.insert(tk.END, " | ")
                    snipe_start = self.output_text.index("end-1c")
                    self.output_text.insert(tk.END, "Snipe!", "snipe_button")
                    snipe_end = self.output_text.index("end-1c")
                    snipe_tag = f"snipe_{snipe_start}"
                    self.output_text.tag_add(snipe_tag, snipe_start, snipe_end)
                    self.output_text.tag_configure(snipe_tag,
                                                foreground='#ff4444',
                                                underline=1)
                    
                    # Update snipe button binding with correct URL handling
                    def create_snipe_callback(id, data):
                        return lambda e: self.snipe_skin(id)
                        
                    self.output_text.tag_bind(snipe_tag, "<Button-1>",
                                           create_snipe_callback(listing_no, self.current_skin_data[listing_no]))
                    
                    # Hover effects
                    for tag in [save_tag, snipe_tag]:
                        self.output_text.tag_bind(tag, "<Enter>",
                                               lambda e: self.output_text.configure(cursor="hand2"))
                        self.output_text.tag_bind(tag, "<Leave>",
                                               lambda e: self.output_text.configure(cursor=""))
                    
                    self.output_text.insert(tk.END, "\n")
                    self.output_text.see(tk.END)
                    
                elif message_type == "high_discount":
                    widget = self.high_discount_output
                    widget.insert(tk.END, content["header"])
                    widget.insert(tk.END, content["details"])
                    link_text, url = content["link"]
                    link_start = widget.index("end-1c")
                    widget.insert(tk.END, link_text, "hyperlink")
                    link_end = widget.index("end-1c")
                    tag_name = f"hd_link_{link_start}"
                    widget.tag_add(tag_name, link_start, link_end)
                    widget.tag_configure(tag_name,
                                         foreground=self.colors['highlight'],
                                         underline=1)
                    widget.tag_bind(tag_name, "<Button-1>",
                                    lambda e, url=url: webbrowser.open(url))
                    widget.insert(tk.END, " | ")
                    save_text, listing_no = content["save_button"]
                    save_start = widget.index("end-1c")
                    widget.insert(tk.END, save_text, "save_button")
                    save_end = widget.index("end-1c")
                    save_tag = f"hd_save_{save_start}"
                    widget.tag_add(save_tag, save_start, save_end)
                    widget.tag_configure(save_tag,
                                         foreground=self.colors['accent'],
                                         underline=1)
                    widget.tag_bind(save_tag, "<Button-1>",
                                    lambda e, id=listing_no: self.quick_save_skin(id))
                    widget.insert(tk.END, " | ")
                    snipe_start = widget.index("end-1c")
                    widget.insert(tk.END, "Snipe!", "snipe_button")
                    snipe_end = widget.index("end-1c")
                    snipe_tag = f"hd_snipe_{snipe_start}"
                    widget.tag_add(snipe_tag, snipe_start, snipe_end)
                    widget.tag_configure(snipe_tag,
                                         foreground='#ff4444',
                                         underline=1)
                    widget.tag_bind(snipe_tag, "<Button-1>",
                                    lambda e, id=listing_no: self.snipe_skin(id))
                    # Hover effects for high discount buttons
                    for tag in [save_tag, snipe_tag]:
                        widget.tag_bind(tag, "<Enter>",
                                        lambda e: widget.configure(cursor="hand2"))
                        widget.tag_bind(tag, "<Leave>",
                                        lambda e: widget.configure(cursor=""))
                    widget.insert(tk.END, "\n")
                    widget.see(tk.END)
                    
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def quick_save_skin(self, listing_no):
        """Quick save a skin using its listing number"""
        if listing_no in self.current_skin_data:
            skin_data = self.current_skin_data[listing_no]
            
            try:
                # Create new skin entry
                new_skin = {
                    "name": skin_data["name"],
                    "float": skin_data["float"],
                    "price": str(skin_data["price"]),
                    "steam_price": str(skin_data["steam_price"]),
                    "discount": str(skin_data["discount"]),
                    "link": skin_data["link"],
                    "saved_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Add to saved skins
                self.saved_skins.append(new_skin)
                
                # Save to file
                self.save_saved_skins()
                self.update_saved_skins_list()
                messagebox.showinfo("Success", f"Saved {skin_data['name']} to saved skins!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save skin: {str(e)}")
                self.load_data()

    def snipe_skin(self, listing_no):
        """Attempt to quickly purchase a skin"""
        if listing_no in self.current_skin_data:
            skin_data = self.current_skin_data[listing_no]
            try:
                # Get the correct URL from the skin data
                product_url = skin_data["link"]
                
                # Use Playwright to handle the purchase
                success, message = playwright_snipe(product_url, listing_no)
                
                if success:
                    messagebox.showinfo("Success", f"Added {skin_data['name']} to cart!\nPlease check your cart.")
                else:
                    messagebox.showerror("Error", f"Failed to add item: {message}")
                    
            except Exception as e:
                print(f"Full error: {str(e)}")
                messagebox.showerror("Error", f"Unexpected error while sniping skin: {str(e)}")

    def save_tracked_skins(self):
        try:
            with open('tracked_skins.json', 'w') as f:
                json.dump(self.tracked_skins, f, indent=4)
            global tracked_skins
            tracked_skins.clear()
            tracked_skins.update(self.tracked_skins)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save tracked skins: {str(e)}")

    def save_saved_skins(self):
        try:
            with open('saved_skins.json', 'w') as f:
                json.dump(self.saved_skins, f, indent=4)
            global saved_skins
            saved_skins.clear()
            saved_skins.extend(self.saved_skins)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save saved skins: {str(e)}")

    def open_knives_config_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Configuration Settings")
        dialog.geometry("400x350")
        
        # Enable/Disable Knives Only
        ttk.Label(dialog, text="Knives Only:", style='Modern.TLabel').pack(pady=5)
        knives_enabled = ttk.Checkbutton(dialog, text="Enable Knives Only", variable=self.knives_only)
        knives_enabled.pack(pady=5)
        
        ttk.Label(dialog, text="Maximum Price:", style='Modern.TLabel').pack(pady=5)
        self.knives_max_price_var = tk.StringVar(value="0")
        max_price_entry = ttk.Entry(dialog, textvariable=self.knives_max_price_var, font=('Segoe UI', 11))
        max_price_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Auto Snipe:", style='Modern.TLabel').pack(pady=5)
        self.knives_autosnipe = tk.BooleanVar(value=False)
        autosnipe_check = ttk.Checkbutton(dialog, text="Enable Auto Snipe", variable=self.knives_autosnipe)
        autosnipe_check.pack(pady=5)

        # Add Steam Username section
        ttk.Separator(dialog, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(dialog, text=f"Current Steam Username: {self.steam_username}", style='Modern.TLabel').pack(pady=5)
        username_button = ModernButton(dialog, text="Set Steam Username", 
                                     command=self.show_steam_username_dialog)
        username_button.pack(pady=5)

        def apply_knives_config():
            try:
                max_price = float(self.knives_max_price_var.get())
                self.knives_max_price_var.set(str(max_price))
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number for maximum price")

        ttk.Button(dialog, text="Apply", command=apply_knives_config).pack(pady=20)

    def save_window_settings(self):
        """Save the current window geometry to a config file"""
        settings = {
            'geometry': self.root.geometry()
        }
        try:
            with open('window_settings.json', 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Error saving window settings: {e}")

    def load_window_settings(self):
        """Load and apply saved window geometry"""
        try:
            with open('window_settings.json', 'r') as f:
                settings = json.load(f)
                geometry = settings.get('geometry', '800x600')
                
                # Validate the geometry string
                try:
                    # Parse the geometry string
                    parts = geometry.replace('+', 'x').split('x')
                    width, height = int(parts[0]), int(parts[1])
                    
                    # Get screen dimensions
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    
                    # Ensure window is not larger than screen
                    width = min(width, screen_width)
                    height = min(height, screen_height)
                    
                    # If there are position coordinates, ensure they're on screen
                    if len(parts) == 4:
                        x, y = int(parts[2]), int(parts[3])
                        x = max(0, min(x, screen_width - width))
                        y = max(0, min(y, screen_height - height))
                        geometry = f"{width}x{height}+{x}+{y}"
                    else:
                        geometry = f"{width}x{height}"
                    
                    self.root.geometry(geometry)
                except (ValueError, IndexError):
                    self.root.geometry('800x600')  # Fallback to default
        except FileNotFoundError:
            self.root.geometry('800x600')  # Default size for first run
        except Exception as e:
            print(f"Error loading window settings: {e}")
            self.root.geometry('800x600')  # Fallback to default

    def on_closing(self):
        """Handle window closing event"""
        self.save_window_settings()
        self.is_tracking = False  # Stop tracking threads
        self.is_high_discount_tracking = False
        # Force cleanup before closing
        self.cleanup_skin_cache(force=True)
        self.root.destroy()

    def load_steam_username(self):
        """Load the saved Steam username for auto-buy functionality"""
        steam_username_file = "steam_username.txt"
        if os.path.exists(steam_username_file):
            try:
                with open(steam_username_file, 'r') as f:
                    saved_username = f.read().strip()
                    if saved_username:
                        self.steam_username = saved_username
                        print(f"Loaded saved Steam username: {self.steam_username}")
            except Exception as e:
                print(f"Could not load saved Steam username: {e}")
    
    def save_steam_username(self, username):
        """Save the Steam username to a config file for future use"""
        try:
            with open("steam_username.txt", 'w') as f:
                f.write(username)
            self.steam_username = username
            print(f"Saved Steam username: {username}")
            return True
        except Exception as e:
            print(f"Could not save Steam username: {e}")
            return False
                
    def show_steam_username_dialog(self):
        """Dialog to set the Steam username for auto-buy"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Set Steam Username")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="Enter Steam username to select in Seçiniz menu:").pack(pady=10)
        username_entry = ttk.Entry(dialog, font=('Segoe UI', 11))
        username_entry.insert(0, self.steam_username)  # Pre-fill with current username
        username_entry.pack(pady=5)
        
        def on_ok():
            username = username_entry.get().strip()
            if username:
                self.save_steam_username(username)
                messagebox.showinfo("Success", f"Steam username set to: {username}")
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10, fill='x')
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel, style='Modern.TButton')
        cancel_button.pack(side='left', padx=10, expand=True)
        
        ok_button = ttk.Button(button_frame, text="OK", command=on_ok, style='Modern.TButton')
        ok_button.pack(side='right', padx=10, expand=True)
        
        dialog.grab_set()
        self.root.wait_window(dialog)

def main():
    from playwright_sniper import start_arc_browser
    arc_started = start_arc_browser()
    if not arc_started:
        print("[DEBUG] Arc Browser remote debugging not started. Please ensure it's running with remote debugging enabled.")
    root = tk.Tk()
    app = SkinTrackerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()


