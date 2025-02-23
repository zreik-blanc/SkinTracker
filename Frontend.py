import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import queue
import time
import webbrowser
from datetime import datetime
from Backend import fetch_skins, tracked_skins, saved_skins, save_tracked_skins, save_saved_skins
import requests
import re
from urllib.parse import unquote

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
        self.root.geometry("800x600")
        
        # Initialize data storage
        self.tracked_skins = {}
        self.saved_skins = []
        
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
        
        # Configure root window
        self.root.configure(bg=self.colors['bg'])
        
        # Dictionary to store current skin data
        self.current_skin_data = {}
        
        # Configure style
        self.setup_styles()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.tracking_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.tracked_skins_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.saved_skins_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        
        self.notebook.add(self.tracking_tab, text="Live Tracking")
        self.notebook.add(self.tracked_skins_tab, text="Tracking Skins")
        self.notebook.add(self.saved_skins_tab, text="Saved Skins")
        
        # Initialize tracking state
        self.is_tracking = False
        self.tracking_thread = None
        self.update_queue = queue.Queue()
        
        # Setup tabs
        self.setup_tracking_tab()
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
        
        # Create status text
        self.status_text = ttk.Label(
            status_frame,
            text="Tracking Inactive",
            style='Modern.TLabel'
        )
        self.status_text.pack(side='left', padx=2)
        
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
                        "threshold": threshold
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
            self.status_text.configure(text="Tracking Active")
            self.tracking_thread = threading.Thread(target=self.track_skins, daemon=True)
            self.tracking_thread.start()
        else:
            self.is_tracking = False
            self.start_button.configure(text="Start Tracking")
            self.status_label.configure(foreground=self.colors['status_inactive'])
            self.status_text.configure(text="Tracking Inactive")

    def track_skins(self):
        while self.is_tracking:
            try:
                skins = fetch_skins()
                track_specific = (self.track_mode.get() == "specific")
                
                # Clear current skin data at the start of each fetch
                self.current_skin_data = {}
                
                for skin in skins:
                    if not self.is_tracking:
                        break
                        
                    try:
                        discount = float(skin.get("discountRate", 0))
                        listing_no = skin.get("listingNo")
                        skin_name = skin.get("name", "Unknown Skin")
                        float_value = skin.get('info', {}).get('float', "N/A")
                        price = skin.get("price", 0)
                        steam_price = skin.get("listingPriceUsd", "N/A")
                        status = skin.get("status", "N/A")
                        slug = skin.get("slug", "N/A")
                        buy_link = f"https://www.bynogame.com/en/games/cs2-skin/{slug}?id={listing_no}"
                        
                        if status == 2:  # Skip sold items
                            continue
                            
                        if track_specific:
                            found_match = False
                            for tracked_skin, track_info in self.tracked_skins.items():
                                if tracked_skin.lower() in skin_name.lower():
                                    track_type = track_info["type"]
                                    threshold = track_info["threshold"]
                                    
                                    if track_type == "discount" and discount >= threshold:
                                        found_match = True
                                        break
                                    elif track_type == "price" and price <= threshold:
                                        found_match = True
                                        break
                            if not found_match:
                                continue
                        elif discount <= 0:  # Skip non-discounted items in all-tracking mode
                            continue
                        
                        # Store the skin data
                        self.current_skin_data[listing_no] = {
                            "name": skin_name,
                            "float": float_value,
                            "price": price,
                            "steam_price": steam_price,
                            "discount": discount,
                            "link": buy_link
                        }
                        
                        # Create message with clickable link and quick save button
                        message_parts = {
                            "header": f"\n{datetime.now().strftime('%H:%M:%S')} - {'Match Found' if track_specific else 'Discount'}\n",
                            "details": f"{skin_name}\nFloat: {float_value}\nPrice: {price:.2f}TL\nSteam Price: {steam_price}$\nDiscount: {discount}%\nID: {listing_no}\nLink: ",
                            "link": ("Click Here", buy_link),
                            "save_button": ("Quick Save", listing_no)  # New save button
                        }
                        
                        self.update_queue.put(("message", message_parts))
                        
                    except Exception as e:
                        print(f"Error processing skin: {e}")
                        continue
                
                time.sleep(5) # refresh rate
                
            except Exception as e:
                print(f"Error fetching skins: {e}")
                time.sleep(5)

    def process_queue(self):
        try:
            while True:
                message_type, content = self.update_queue.get_nowait()
                
                if message_type == "message":
                    # Add header and details
                    self.output_text.insert(tk.END, content["header"])
                    self.output_text.insert(tk.END, content["details"])
                    
                    # Add clickable link
                    link_text, url = content["link"]
                    link_start = self.output_text.index("end-1c")
                    self.output_text.insert(tk.END, link_text, "hyperlink")
                    link_end = self.output_text.index("end-1c")
                    
                    # Create link tag
                    tag_name = f"link_{link_start}"
                    self.output_text.tag_add(tag_name, link_start, link_end)
                    self.output_text.tag_configure(tag_name,
                                                foreground=self.colors['highlight'],
                                                underline=1)
                    self.output_text.tag_bind(tag_name, "<Button-1>",
                                           lambda e, url=url: webbrowser.open(url))
                    
                    # Add separators and buttons
                    self.output_text.insert(tk.END, " | ")
                    
                    # Add quick save button
                    save_text, listing_no = content["save_button"]
                    save_start = self.output_text.index("end-1c")
                    self.output_text.insert(tk.END, save_text, "save_button")
                    save_end = self.output_text.index("end-1c")
                    
                    # Create save button tag
                    save_tag = f"save_{save_start}"
                    self.output_text.tag_add(save_tag, save_start, save_end)
                    self.output_text.tag_configure(save_tag,
                                                foreground=self.colors['accent'],
                                                underline=1)
                    self.output_text.tag_bind(save_tag, "<Button-1>",
                                           lambda e, id=listing_no: self.quick_save_skin(id))
                    
                    # Add snipe button
                    self.output_text.insert(tk.END, " | ")
                    snipe_start = self.output_text.index("end-1c")
                    self.output_text.insert(tk.END, "Snipe!", "snipe_button")
                    snipe_end = self.output_text.index("end-1c")
                    
                    # Create snipe button tag
                    snipe_tag = f"snipe_{snipe_start}"
                    self.output_text.tag_add(snipe_tag, snipe_start, snipe_end)
                    self.output_text.tag_configure(snipe_tag,
                                                foreground='#ff4444',  # Red color for urgency
                                                underline=1)
                    self.output_text.tag_bind(snipe_tag, "<Button-1>",
                                           lambda e, id=listing_no: self.snipe_skin(id))
                    
                    # Add hover effects for all buttons
                    for tag in [save_tag, snipe_tag]:
                        self.output_text.tag_bind(tag, "<Enter>",
                                               lambda e: self.output_text.configure(cursor="hand2"))
                        self.output_text.tag_bind(tag, "<Leave>",
                                               lambda e: self.output_text.configure(cursor=""))
                    
                    # Add newline after buttons
                    self.output_text.insert(tk.END, "\n")
                    
                self.output_text.see(tk.END)
                
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
                product_url = skin_data.get("buylink", skin_data["link"])
                session = requests.Session()
                session.timeout = (5, 15)
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504, 429]
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                session.mount("https://", adapter)
                print("Fetching main page...")
                main_response = session.get(
                    "https://www.bynogame.com/en",
                    timeout=(5, 15),
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                main_response.raise_for_status()
                print("Main page loaded successfully")
                print(f"Fetching product page: {product_url}")
                product_response = session.get(
                    product_url,
                    timeout=(5, 15),
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                product_response.raise_for_status()
                print("Product page loaded successfully")
                html_content = product_response.text
                
                # Extract CSRF token using the helper method
                csrf_token = self._extract_csrf_token(html_content, session)
                if not csrf_token:
                    messagebox.showerror("Error", "Could not get authentication token. Please try again.")
                    return
                    
                cart_endpoints = [
                    "https://www.bynogame.com/en/add-cart",
                    f"https://www.bynogame.com/en/cart/add/{listing_no}",
                    "https://www.bynogame.com/en/api/cart/add"
                ]
                cart_data = {
                    "listingNo": str(listing_no),
                    "quantity": "1",
                    "productType": "cs2-skin",
                    "_token": csrf_token,
                    "csrf_token": csrf_token
                }
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRF-TOKEN': csrf_token,
                    'Origin': 'https://www.bynogame.com',
                    'Referer': product_url
                }
                cookie_string = '; '.join([f"{cookie.name}={cookie.value}" for cookie in session.cookies])
                headers['Cookie'] = cookie_string
                
                success = False
                for cart_url in cart_endpoints:
                    try:
                        print(f"\nTrying cart endpoint: {cart_url}")
                        response = session.post(
                            cart_url,
                            data=cart_data,
                            headers=headers,
                            timeout=(5, 15)
                        )
                        print(f"Response Status: {response.status_code}")
                        if response.status_code in [200, 201, 302]:
                            success = True
                            break
                    except requests.exceptions.RequestException as e:
                        print(f"Failed with endpoint {cart_url}: {str(e)}")
                        continue
                
                if success:
                    webbrowser.open("https://www.bynogame.com/en/cart")
                    messagebox.showinfo("Success", f"Added {skin_data['name']} to cart!\nCheckout page opened in browser.")
                else:
                    error_msg = "Failed to add item to cart with all endpoints"
                    if 'response' in locals() and response.text:
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('message', error_msg)
                        except:
                            error_msg = f"{error_msg}\nLast response: {response.text[:100]}..."
                    messagebox.showerror("Error", error_msg)
                
            except Exception as e:
                messagebox.showerror("Error", f"Unexpected error while sniping skin: {str(e)}")
                print(f"Full error: {str(e)}")
    
    def _extract_csrf_token(self, html_content, session):
        """Helper method to extract CSRF token from HTML or session cookies"""
        # Method 1: Check the session cookie
        token = session.cookies.get('XSRF-TOKEN')
        if token:
            token = unquote(token)
            if token:
                print(f"Token from cookie: {token}")
                return token
        # Method 2: Use BeautifulSoup to find a meta tag
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            meta = soup.find('meta', attrs={'name': 'csrf-token'})
            if meta and meta.get('content'):
                print(f"Token from meta tag: {meta['content']}")
                return meta['content']
        except ImportError:
            pass
        # Method 3: Regex to find meta or input token
        regex = re.search(
            r'<meta[^>]*?name=[\'"](?:csrf-token|_token)[\'"][^>]*?content=["\']([^"\']+)["\']', 
            html_content, re.I
        )
        if regex:
            print(f"Token from regex meta: {regex.group(1)}")
            return regex.group(1)
        regex = re.search(
            r'<input[^>]*?name=["\'](?:csrf|_token)["\'][^>]*?value=["\']([^"\']+)["\']', 
            html_content, re.I
        )
        if regex:
            print(f"Token from regex input: {regex.group(1)}")
            return regex.group(1)
        # Method 4: Try to find token in JavaScript variables
        regex = re.search(r'(?:csrf_token|_token)[\'"]\s*:\s*[\'"]([^"\']+)[\'"]', html_content)
        if regex:
            print(f"Token from JS variable: {regex.group(1)}")
            return regex.group(1)
        return None

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

def main():
    root = tk.Tk()
    app = SkinTrackerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()


