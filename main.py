import os
import shutil
import struct
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from zipfile import ZipFile, ZIP_DEFLATED
import rarfile
import subprocess
import platform
import threading
from PIL import Image, ImageDraw
from source.dev import *

class MyArcCompressor:
    """My own NARC compress (but there's a problems) method. I'll improve method in few updates"""
    MAGIC = b'NARC1.0'
    
    @staticmethod
    def compress(input_path, output_path):
        with open(output_path, 'wb') as f_out:
            f_out.write(MyArcCompressor.MAGIC)
            
            if os.path.isfile(input_path):
                files = [input_path]
            else:
                files = [
                    os.path.join(root, file) 
                    for root, _, files in os.walk(input_path) 
                    for file in files
                ]
            
            for file_path in files:
                rel_path = os.path.relpath(file_path, os.path.dirname(input_path))
                file_size = os.path.getsize(file_path)
                header = struct.pack(
                    'I', 
                    len(rel_path.encode('utf-8'))
                ) + rel_path.encode('utf-8') + struct.pack('Q', file_size)
                
                f_out.write(header)
                
                with open(file_path, 'rb') as f_in:
                    shutil.copyfileobj(f_in, f_out, 1024*1024)

    @staticmethod
    def extract(archive_path, output_dir):
        with open(archive_path, 'rb') as f_in:
            magic = f_in.read(len(MyArcCompressor.MAGIC))
            if magic != MyArcCompressor.MAGIC:
                raise ValueError("Invalid NARC archive")
            
            os.makedirs(output_dir, exist_ok=True)
            
            while True:
                size_data = f_in.read(4)
                if not size_data: break
                
                name_len = struct.unpack('I', size_data)[0]
                name = f_in.read(name_len).decode('utf-8')
                file_size = struct.unpack('Q', f_in.read(8))[0]
                
                output_path = os.path.join(output_dir, name)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f_out:
                    remaining = file_size
                    while remaining:
                        chunk = min(remaining, 1024*1024)
                        f_out.write(f_in.read(chunk))
                        remaining -= chunk


class ThemeManager:
    """App theme manager"""
    THEMES = {
        "Light": "blue",
        "Dark": "dark-blue",
    }
    
    @staticmethod
    def set_theme(theme_name):
        """Set choosen theme"""
        theme = ThemeManager.THEMES.get(theme_name, "blue")
        ctk.set_default_color_theme(theme)

        if "dark" in theme_name.lower() or "dark" in theme_name.lower():
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")


class WinRARClone:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title(f"{app_name} - Cool archiver lol")
        self.root.geometry("900x650")
        self.root.minsize(800, 600)

        self.current_theme = "Light"
        ThemeManager.set_theme(self.current_theme)

        self.temp_dir = os.path.join(os.getcwd(), ".tmp_next")
        os.makedirs(self.temp_dir, exist_ok=True)
        if platform.system() == 'Windows':
            subprocess.call(f'attrib +h "{self.temp_dir}"', shell=True)

        self.current_archive = None
        self.archive_files = {}

        self.create_widgets()

        self.formats = ['.zip', '.rar', '.myarc']
        self.compression_levels = {
            'Store': 0,
            'Fastest': 1,
            'Fast': 3,
            'Normal': 5,
            'Good': 7,
            'Best': 9
        }
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """Main UI"""
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self.root, height=40)
        toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        toolbar.grid_columnconfigure(0, weight=1)

        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side=ctk.LEFT, padx=5)
        
        btn_add = ctk.CTkButton(btn_frame, text="Add to archive", width=100, command=self.add_files)
        btn_add.pack(side=ctk.LEFT, padx=2)
        
        btn_extract = ctk.CTkButton(btn_frame, text="Extract", width=100, command=self.extract_archive)
        btn_extract.pack(side=ctk.LEFT, padx=2)
        
        btn_view = ctk.CTkButton(btn_frame, text="View", width=100, command=self.view_archive)
        btn_view.pack(side=ctk.LEFT, padx=2)
        
        btn_open = ctk.CTkButton(btn_frame, text="Open file in app", width=100, command=self.open_selected_file)
        btn_open.pack(side=ctk.LEFT, padx=2)

        settings_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        settings_frame.pack(side=ctk.RIGHT, padx=5)

        theme_menu = ctk.CTkOptionMenu(
            settings_frame, 
            values=list(ThemeManager.THEMES.keys()),
            command=self.change_theme,
            width=150
        )
        theme_menu.set(self.current_theme)
        theme_menu.pack(side=ctk.LEFT, padx=5)

        btn_about = ctk.CTkButton(
            settings_frame, 
            text=f"About {app_name}", 
            width=120, 
            fg_color="#2e8b57", 
            hover_color="#3cb371",
            command=self.show_about
        )
        btn_about.pack(side=ctk.LEFT, padx=5)
        
        list_frame = ctk.CTkFrame(self.root)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_frame,
            font=("Arial", 11),
            relief="flat",
            highlightthickness=0
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.bind('<Double-Button-1>', lambda e: self.open_selected_file())
        self.listbox.bind('<Return>', lambda e: self.open_selected_file())
        
        scrollbar = ctk.CTkScrollbar(list_frame, command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        self.status = ctk.StringVar(value="Ready")
        status_bar = ctk.CTkLabel(
            self.root, 
            textvariable=self.status, 
            anchor="w",
            height=24,
            corner_radius=0,
            font=("Arial", 10)
        )
        status_bar.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))

    def clear_temp_dir(self):
        """Cleaning temp dir"""
        for item in os.listdir(self.temp_dir):
            item_path = os.path.join(self.temp_dir, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

    def extract_to_temp(self, archive_path):
        """Extraction archive to temp dir"""
        self.clear_temp_dir()
        
        try:
            ext = os.path.splitext(archive_path)[1].lower()
            
            if ext == '.zip':
                with ZipFile(archive_path, 'r') as zipf:
                    zipf.extractall(self.temp_dir)
            
            elif ext == '.rar':
                with rarfile.RarFile(archive_path) as rarf:
                    rarf.extractall(self.temp_dir)
            
            elif ext == '.narc':
                MyArcCompressor.extract(archive_path, self.temp_dir)
            
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Extraction error: {str(e)}")
            return False

    def add_files(self):
        files = filedialog.askopenfilenames(title="Choose files for pack in archive")
        if not files: return
        
        archive_path = filedialog.asksaveasfilename(
            title="Save archive as...",
            filetypes=[("Archives", "*.zip *.rar *.narc"), ("All files", "*.*")]
        )
        if not archive_path: return
        
        ext = os.path.splitext(archive_path)[1].lower()
        
        try:
            if ext == '.zip':
                with ZipFile(archive_path, 'w', ZIP_DEFLATED) as zipf:
                    for file in files:
                        zipf.write(file, os.path.basename(file))
            
            elif ext == '.rar':
                messagebox.showinfo(
                    "Info", 
                    "Creation RAR archives currently unsupported. Use NARC."
                )
                MyArcCompressor.compress(files[0], archive_path)
            
            elif ext == '.narc':
                MyArcCompressor.compress(files[0], archive_path)
            
            self.status.set(f"Archive successfully created in: {archive_path}")
        
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def extract_archive(self):
        archive_path = filedialog.askopenfilename(
            title="Choose archive",
            filetypes=[("Archives", "*.zip *.rar *.narc"), ("All files", "*.*")]
        )
        if not archive_path: return
        
        output_dir = filedialog.askdirectory(title="Choose dir for extract current archive")
        if not output_dir: return
        
        try:
            ext = os.path.splitext(archive_path)[1].lower()
            
            if ext == '.zip':
                with ZipFile(archive_path, 'r') as zipf:
                    zipf.extractall(output_dir)
            
            elif ext == '.rar':
                with rarfile.RarFile(archive_path) as rarf:
                    rarf.extractall(output_dir)
            
            elif ext == '.narc':
                MyArcCompressor.extract(archive_path, output_dir)
            
            self.status.set(f"Files unpacked in: {output_dir}")
        
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def view_archive(self):
        archive_path = filedialog.askopenfilename(
            title="Select archive",
            filetypes=[(f"Archives", "*.zip *.rar *.narc"), ("All files", "*.*")]
        )
        if not archive_path: return
        
        self.current_archive = archive_path
        self.listbox.delete(0, tk.END)
        self.archive_files = {}
        
        def extract_and_list():
            self.status.set("Extracting the archive...")
            if self.extract_to_temp(archive_path):
                self.status.set("Creating a list of files...")
                
                file_list = []
                for root, _, files in os.walk(self.temp_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.temp_dir)
                        file_list.append(rel_path)
                        self.archive_files[rel_path] = full_path

                self.root.after(0, lambda: self.update_file_list(file_list))
                self.status.set(f"Viewing archive: {archive_path}")
        
        threading.Thread(target=extract_and_list, daemon=True).start()

    def update_file_list(self, file_list):
        """Updating the list of files in the interface"""
        self.listbox.delete(0, tk.END)
        for file in sorted(file_list):
            self.listbox.insert(tk.END, file)

    def open_selected_file(self):
        """Opening the selected file from the archive"""
        selected = self.listbox.curselection()
        if not selected:
            return
            
        file_name = self.listbox.get(selected[0])
        file_path = self.archive_files.get(file_name)
        
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "File not found in temp folder")
            return
        
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't open file: {str(e)}")
    
    def change_theme(self, theme_name):
        """Change app theme"""
        self.current_theme = theme_name
        ThemeManager.set_theme(theme_name)
        
        try:
            if "dark" in theme_name.lower() in theme_name.lower():
                self.listbox.config(
                    bg='#2a2d2e', 
                    fg='white',
                    selectbackground='#3b8ed0',
                    selectforeground='white'
                )
            else:
                self.listbox.config(
                    bg='white', 
                    fg='black',
                    selectbackground='#1f6aa5',
                    selectforeground='white'
                )
        except Exception:
            pass
    
    def show_about(self):
        """Displaying information about the program"""
        about_window = ctk.CTkToplevel(self.root)
        about_window.title(f"About {app_name}")
        about_window.geometry("500x400")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        
        main_frame = ctk.CTkFrame(about_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        logo_frame = ctk.CTkFrame(main_frame, width=100, height=100, corner_radius=50)
        logo_frame.pack(pady=20)
        logo_label = ctk.CTkLabel(
            logo_frame, 
            text="NΞXT", 
            font=("Arial", 24, "bold"),
            width=100,
            height=100
        )
        logo_label.pack()
        
        # Информация о программе
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=10)
        
        program_name = ctk.CTkLabel(
            info_frame, 
            text=f"{app_name} / NEXT", 
            font=("Arial", 20, "bold")
        )
        program_name.pack(pady=(0, 10))
        
        info_text = f"""
Version: {version}
Author: {author}

{app_name} - custom WinRAR client with support:
- ZIP - (reading/writing)
- RAR - (reading only)
- NARC (Next ARC) - (Custom format)
        """
        
        info_label = ctk.CTkLabel(
            info_frame, 
            text=info_text,
            justify="left"
        )
        info_label.pack(anchor="w", padx=10)
        
        # Кнопка закрытия
        btn_close = ctk.CTkButton(
            main_frame, 
            text="Close", 
            command=about_window.destroy,
            width=120
        )
        btn_close.pack(pady=20)

    def on_closing(self):
        """Actions when closing the program"""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass
        self.root.destroy()
        
    def mainloop(self):
        """Starting the main application cycle"""
        self.root.mainloop()


if __name__ == "__main__":
    app = WinRARClone()
    app.mainloop()