import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import configparser
import os
import time
import subprocess
import threading
import sys
from PIL import Image, ImageTk
import pystray
import urllib.request

# Настройки иконок
MAIN_ICON_URL = "https://cdn-icons-png.flaticon.com/512/10268/10268970.png"
HELP_ICON_URL = "https://cdn-icons-png.flaticon.com/512/447/447057.png"
ICON_FILENAME = "music_control_icon.png"
HELP_ICON_FILENAME = "help_icon.png"

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
        
        if 'SETTINGS' not in self.config:
            self.config['SETTINGS'] = {
                'player_version': 'Yandex-music(v1)',
                'set_vol': '50',
                'normal_vol': '70',
                'language': 'ru',
                'window_x': '100',
                'window_y': '100'
            }
    
    def get(self, key, default=None):
        return self.config['SETTINGS'].get(key, default)
    
    def set(self, key, value):
        self.config['SETTINGS'][key] = str(value)
    
    def save(self):
        with open('config.ini', 'w', encoding='utf-8') as f:
            self.config.write(f)

class Language:
    def __init__(self):
        self.cfg = Config()
        self.current_lang = self.cfg.get('language', 'ru')
        self.translations = {
            'ru': {
                'title': "Контроль музыки",
                'select_player': "Выберите плеер:",
                'player_v1': "Yandex-music(v1)",
                'player_v2': "Яндекс Музыка(v2)",
                'custom_player': "Свой вариант",
                'custom_player_prompt': "Введите название процесса:",
                'start_vol': "Стартовая громкость:",
                'normal_vol': "Рабочая громкость:",
                'launch': "Запустить",
                'debug': "Отладка",
                'help_text': "Выберите плеер или укажите свой вариант",
                'console_title': "Консоль отладки",
                'select_lang': "Язык:",
                'error': "Ошибка",
                'launch_error': "Не удалось запустить плеер"
            },
            'en': {
                'title': "Music Control",
                'select_player': "Select player:",
                'player_v1': "Yandex-music(v1)",
                'player_v2': "Yandex Music(v2)",
                'custom_player': "Custom player",
                'custom_player_prompt': "Enter process name:",
                'start_vol': "Start volume:",
                'normal_vol': "Normal volume:",
                'launch': "Launch",
                'debug': "Debug",
                'help_text': "Select player or specify custom",
                'console_title': "Debug Console",
                'select_lang': "Language:",
                'error': "Error",
                'launch_error': "Failed to launch player"
            }
        }
    
    def tr(self, key):
        return self.translations[self.current_lang].get(key, key)
    
    def set_lang(self, lang):
        self.current_lang = lang
        self.cfg.set('language', lang)
        self.cfg.save()

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tip_window, text=self.text, bg="#ffffe0", relief="solid", borderwidth=1)
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class TrayIcon:
    def __init__(self, master, app):
        self.master = master
        self.app = app
        self.icon = None
        self.setup_icon()
    
    def setup_icon(self):
        try:
            if not os.path.exists(ICON_FILENAME):
                urllib.request.urlretrieve(MAIN_ICON_URL, ICON_FILENAME)
            image = Image.open(ICON_FILENAME)
            image = image.resize((64, 64), Image.Resampling.LANCZOS)
        except:
            image = Image.new('RGB', (64, 64), '#1E1E1E')
        
        menu = pystray.Menu(
            pystray.MenuItem(self.app.lang.tr('launch'), self.restore_app),
            pystray.MenuItem(self.app.lang.tr('debug'), self.show_debug),
            pystray.MenuItem("Exit", self.exit_app)
        )
        
        self.icon = pystray.Icon("music_control", image, "Music Control", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()
    
    def restore_app(self):
        self.master.after(0, self.master.deiconify)
        self.master.after(0, self.master.attributes, '-alpha', 1.0)
    
    def show_debug(self):
        self.master.after(0, self.app.show_debug_console)
    
    def exit_app(self):
        self.master.after(0, self.master.destroy)

class MusicControlApp:
    def __init__(self, master):
        self.master = master
        self.cfg = Config()
        self.lang = Language()
        self.setup_window()
        self.load_icon()
        self.setup_fonts()
        self.create_widgets()
        self.tray_icon = TrayIcon(master, self)
        self.debug_process = None
        
        self.master.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.fade_in()
    
    def setup_window(self):
        self.master.title(self.lang.tr('title'))
        self.master.geometry(f"400x500+{self.cfg.get('window_x')}+{self.cfg.get('window_y')}")
        self.master.resizable(False, False)
        self.master.configure(bg='#1E1E1E')
        self.master.attributes('-alpha', 0)
    
    def load_icon(self):
        if not os.path.exists(ICON_FILENAME):
            try:
                urllib.request.urlretrieve(MAIN_ICON_URL, ICON_FILENAME)
            except:
                pass
        
        if os.path.exists(ICON_FILENAME):
            try:
                img = Image.open(ICON_FILENAME)
                self.master.iconphoto(False, ImageTk.PhotoImage(img))
            except:
                pass
    
    def setup_fonts(self):
        self.title_font = ('Helvetica', 16, 'bold')
        self.normal_font = ('Helvetica', 10)
        self.small_font = ('Helvetica', 9)
    
    def create_widgets(self):
        # Main container
        self.main_frame = tk.Frame(self.master, bg='#1E1E1E')
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        self.title_label = tk.Label(
            self.main_frame,
            text=self.lang.tr('title'),
            font=self.title_font,
            fg='#1DB954',
            bg='#1E1E1E'
        )
        self.title_label.pack(pady=(0, 20))
        
        # Language selector
        lang_frame = tk.Frame(self.main_frame, bg='#1E1E1E')
        lang_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(
            lang_frame,
            text=self.lang.tr('select_lang'),
            font=self.small_font,
            fg='white',
            bg='#1E1E1E'
        ).pack(side='left')
        
        self.lang_var = tk.StringVar(value=self.lang.current_lang)
        lang_menu = ttk.Combobox(
            lang_frame,
            textvariable=self.lang_var,
            values=['ru', 'en'],
            font=self.small_font,
            state='readonly',
            width=5
        )
        lang_menu.pack(side='right')
        lang_menu.bind('<<ComboboxSelected>>', self.change_language)
        
        # Help text
        # tk.Label(
        #     self.main_frame,
        #     text=self.lang.tr('help_text'),
        #     font=self.small_font,
        #     fg='#AAAAAA',
        #     bg='#1E1E1E',
        #     justify='left',
        #     wraplength=360
        # ).pack(pady=(0, 20))
        
        # Player selection
        tk.Label(
            self.main_frame,
            text=self.lang.tr('select_player'),
            font=self.normal_font,
            fg='white',
            bg='#1E1E1E'
        ).pack(anchor='w', pady=(0, 5))
        
        self.player_var = tk.StringVar(value=self.cfg.get('player_version'))
        players = [self.lang.tr('player_v1'), self.lang.tr('player_v2'), self.lang.tr('custom_player')]
        self.player_menu = ttk.Combobox(
            self.main_frame,
            textvariable=self.player_var,
            values=players,
            font=self.normal_font,
            state='readonly'
        )
        self.player_menu.pack(fill='x', pady=(0, 10))
        self.player_menu.bind('<<ComboboxSelected>>', self.on_player_select)
        
        # Custom player entry
        self.custom_frame = tk.Frame(self.main_frame, bg='#1E1E1E')
        self.custom_label = tk.Label(
            self.custom_frame,
            text=self.lang.tr('custom_player_prompt'),
            font=self.normal_font,
            fg='white',
            bg='#1E1E1E'
        )
        self.custom_label.pack(anchor='w', pady=(5, 0))
        
        self.custom_entry = ttk.Entry(
            self.custom_frame,
            font=self.normal_font
        )
        self.custom_entry.pack(fill='x', pady=(0, 10))
        
        # Set initial custom player name if exists
        if self.player_var.get() and self.player_var.get() not in [self.lang.tr('player_v1'), self.lang.tr('player_v2')]:
            self.custom_entry.insert(0, self.player_var.get())
        
        # Volume controls
        self.volumes = {
            'set_vol': {'label': self.lang.tr('start_vol'), 'value': tk.IntVar(value=int(self.cfg.get('set_vol', 50)))},
            'normal_vol': {'label': self.lang.tr('normal_vol'), 'value': tk.IntVar(value=int(self.cfg.get('normal_vol', 70)))}
        }
        
        for key in self.volumes:
            frame = tk.Frame(self.main_frame, bg='#1E1E1E')
            frame.pack(fill='x', pady=5)
            
            tk.Label(
                frame,
                text=self.volumes[key]['label'],
                font=self.normal_font,
                fg='white',
                bg='#1E1E1E'
            ).pack(side='left')
            
            scale = tk.Scale(
                frame,
                variable=self.volumes[key]['value'],
                from_=0,
                to=100,
                orient='horizontal',
                bg='#1E1E1E',
                fg='white',
                highlightthickness=0,
                troughcolor='#535353',
                activebackground='#1DB954',
                command=lambda v, k=key: self.save_config()
            )
            scale.pack(side='right', fill='x', expand=True)
        
        # Buttons
        btn_frame = tk.Frame(self.main_frame, bg='#1E1E1E')
        btn_frame.pack(fill='x', pady=(20, 0))
        
        self.debug_btn = tk.Button(
            btn_frame,
            text=self.lang.tr('debug'),
            font=self.normal_font,
            bg='#535353',
            fg='white',
            bd=0,
            padx=20,
            pady=8,
            command=self.show_debug_console
        )
        self.debug_btn.pack(side='left', padx=(0, 10), fill='x', expand=True)
        
        self.launch_btn = tk.Button(
            btn_frame,
            text=self.lang.tr('launch'),
            font=self.normal_font,
            bg='#1DB954',
            fg='white',
            bd=0,
            padx=20,
            pady=8,
            command=self.launch
        )
        self.launch_btn.pack(side='right', fill='x', expand=True)
        
        # Hover effects
        self.launch_btn.bind('<Enter>', lambda e: self.launch_btn.config(bg="#1ED760"))
        self.launch_btn.bind('<Leave>', lambda e: self.launch_btn.config(bg="#1DB954"))
        self.debug_btn.bind('<Enter>', lambda e: self.debug_btn.config(bg="#6D6D6D"))
        self.debug_btn.bind('<Leave>', lambda e: self.debug_btn.config(bg="#535353"))
        
        # Help icon
        help_icon = tk.Label(
            self.main_frame,
            text=" ? ",
            font=self.title_font,
            fg='#1DB954',
            bg='#1E1E1E',
            cursor="hand2"
        )
        help_icon.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)
        ToolTip(help_icon, self.lang.tr('help_text'))
        
        # Initial player selection
        self.on_player_select()
    
    def on_player_select(self, event=None):
        if self.player_var.get() == self.lang.tr('custom_player'):
            self.custom_frame.pack(fill='x', pady=(0, 10))
        else:
            self.custom_frame.pack_forget()
        self.save_config()
    
    def change_language(self, event):
        self.lang.set_lang(self.lang_var.get())
        
        # Update all UI elements
        self.master.title(self.lang.tr('title'))
        self.title_label.config(text=self.lang.tr('title'))
        self.custom_label.config(text=self.lang.tr('custom_player_prompt'))
        
        # Update player menu options
        players = [self.lang.tr('player_v1'), self.lang.tr('player_v2'), self.lang.tr('custom_player')]
        self.player_menu['values'] = players
        
        # Update volume labels
        self.volumes['set_vol']['label'] = self.lang.tr('start_vol')
        self.volumes['normal_vol']['label'] = self.lang.tr('normal_vol')
        
        # Update buttons
        self.launch_btn.config(text=self.lang.tr('launch'))
        self.debug_btn.config(text=self.lang.tr('debug'))
        
        # Update tooltip
        for child in self.main_frame.winfo_children():
            if isinstance(child, tk.Label) and child['text'] == " ? ":
                for handler in child.bindtags():
                    if 'ToolTip' in str(handler):
                        child.unbind("<Enter>")
                        child.unbind("<Leave>")
                        ToolTip(child, self.lang.tr('help_text'))
                        break
    
    def save_config(self):
        # Save player version (use custom entry if custom selected)
        if self.player_var.get() == self.lang.tr('custom_player'):
            player_name = self.custom_entry.get()
            self.cfg.set('player_version', player_name)
        else:
            self.cfg.set('player_version', self.player_var.get())
        
        self.cfg.set('set_vol', self.volumes['set_vol']['value'].get())
        self.cfg.set('normal_vol', self.volumes['normal_vol']['value'].get())
        self.cfg.set('language', self.lang.current_lang)
        self.cfg.set('window_x', self.master.winfo_x())
        self.cfg.set('window_y', self.master.winfo_y())
        self.cfg.save()
    
    def fade_in(self):
        for alpha in [i/20 for i in range(0, 21)]:
            if not self.master.winfo_exists(): break
            self.master.attributes('-alpha', alpha)
            self.master.update()
            time.sleep(0.02)
    
    def minimize_to_tray(self):
        self.save_config()
        self.master.withdraw()
    
    def launch(self):
        self.save_config()
        self.minimize_to_tray()
        
        # Determine player executable
        if self.player_var.get() == self.lang.tr('player_v1'):
            player_exe = 'YandexMusic.exe'
        elif self.player_var.get() == self.lang.tr('player_v2'):
            player_exe = 'Яндекс Музыка.exe'
        else:
            player_exe = self.custom_entry.get()
        
        if not player_exe:
            messagebox.showerror(self.lang.tr('error'), self.lang.tr('launch_error'))
            return
        
        try:
            # Hide console window (Windows only)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Launch gmain.py for debugging
            debug_process = subprocess.Popen(
                [sys.executable, 'gmain.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo
            )
            
            # Launch player
            subprocess.Popen(player_exe, shell=True, startupinfo=startupinfo)
        except Exception as e:
            messagebox.showerror(self.lang.tr('error'), f"{self.lang.tr('launch_error')}: {str(e)}")
    
    def show_debug_console(self):
        if hasattr(self, 'debug_window') and self.debug_window.winfo_exists():
            self.debug_window.lift()
            return
        
        self.debug_window = tk.Toplevel(self.master)
        self.debug_window.title(self.lang.tr('console_title'))
        self.debug_window.geometry("600x400")
        self.debug_window.configure(bg='#1E1E1E')
        
        self.debug_text = scrolledtext.ScrolledText(
            self.debug_window,
            bg='#1E1E1E',
            fg='white',
            insertbackground='white',
            font=('Consolas', 10)
        )
        self.debug_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        try:
            if self.debug_process is None:
                # Read from gmain.py output
                self.debug_process = subprocess.Popen(
                    [sys.executable, 'gmain.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True
                )
            
            threading.Thread(target=self.read_debug_output, daemon=True).start()
        except Exception as e:
            self.debug_text.insert('end', f"Error: {str(e)}\n")
        
        self.debug_window.protocol("WM_DELETE_WINDOW", self.close_debug)
    
    def read_debug_output(self):
        while self.debug_process and self.debug_process.poll() is None:
            output = self.debug_process.stdout.readline()
            if output:
                self.debug_text.insert('end', output)
                self.debug_text.see('end')
                self.debug_text.update()
    
    def close_debug(self):
        if self.debug_process:
            self.debug_process.terminate()
            self.debug_process = None
        self.debug_window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicControlApp(root)
    root.mainloop()