import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import json
import os
from assistant.voice_assistant import VoiceAssistant
from app_indexer.windows_app_indexer import WindowsAppIndexer

class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert("end", str, (self.tag,))
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        pass

class VoiceAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Assistant Control Panel")
        self.root.geometry("800x600")

        self.assistant = VoiceAssistant()
        self.is_running = False

        self.indexer = WindowsAppIndexer()

        # Tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.create_dashboard_tab()
        self.create_macros_tab()
        self.create_apps_tab()
        self.create_settings_tab()

    def create_dashboard_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Dashboard")

        # Control Frame
        control_frame = ttk.LabelFrame(tab, text="Control", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)

        self.status_var = tk.StringVar(value="Status: Stopped")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var, font=('Helvetica', 12, 'bold'))
        self.status_label.pack(side='left', padx=10)

        self.start_btn = ttk.Button(control_frame, text="Start Agent", command=self.start_agent)
        self.start_btn.pack(side='right', padx=5)

        self.stop_btn = ttk.Button(control_frame, text="Stop Agent", command=self.stop_agent, state='disabled')
        self.stop_btn.pack(side='right', padx=5)

        # Logs
        log_frame = ttk.LabelFrame(tab, text="Logs", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=10)
        self.log_area.pack(fill='both', expand=True)
        
        # Redirect stdout/stderr
        sys.stdout = TextRedirector(self.log_area, "stdout")
        sys.stderr = TextRedirector(self.log_area, "stderr")

    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")
        
        # n8n Settings
        n8n_frame = ttk.LabelFrame(tab, text="n8n Integration", padding=10)
        n8n_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(n8n_frame, text="Webhook URL:").pack(side='left', padx=5)
        self.n8n_url_var = tk.StringVar(value="http://localhost:5678/webhook/voice-assistant") # TODO: Load from config
        ttk.Entry(n8n_frame, textvariable=self.n8n_url_var).pack(side='left', fill='x', expand=True, padx=5)
        
        # LLM Settings
        llm_frame = ttk.LabelFrame(tab, text="LLM Configuration (Ollama)", padding=10)
        llm_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(llm_frame, text="Ollama URL:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.ollama_url_var = tk.StringVar(value="http://localhost:11434/api/generate")
        ttk.Entry(llm_frame, textvariable=self.ollama_url_var).grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        ttk.Label(llm_frame, text="Model:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.model_var = tk.StringVar(value="llama3")
        ttk.Entry(llm_frame, textvariable=self.model_var).grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        llm_frame.columnconfigure(1, weight=1)
        
        # Save Button
        ttk.Button(tab, text="Save Settings", command=self.save_settings).pack(pady=10)

    def save_settings(self):
        # TODO: Persist these settings to a config file or constants
        messagebox.showinfo("Settings", "Settings saved (In-memory for now)")

    def create_macros_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Macros")
        
        self.macro_file_path = "config/macro_definitions.json"
        
        # Toolbar
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="Refresh", command=self.load_macros).pack(side='left')
        ttk.Button(toolbar, text="Save", command=self.save_macros).pack(side='left', padx=5)

        # Content
        self.macro_editor = scrolledtext.ScrolledText(tab)
        self.macro_editor.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.load_macros()

    def load_macros(self):
        if os.path.exists(self.macro_file_path):
            with open(self.macro_file_path, 'r') as f:
                content = f.read()
                self.macro_editor.delete('1.0', tk.END)
                self.macro_editor.insert('1.0', content)
        else:
            self.macro_editor.insert('1.0', "Macro file not found.")

    def save_macros(self):
        content = self.macro_editor.get('1.0', tk.END).strip()
        try:
            # Validate JSON
            json.loads(content)
            with open(self.macro_file_path, 'w') as f:
                f.write(content)
            messagebox.showinfo("Success", "Macros saved successfully.")
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON: {e}")

    def create_apps_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="App Manager")

        # Toolbar
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="Refresh Apps", command=self.refresh_apps).pack(side='left')
        ttk.Button(toolbar, text="Rebuild Cache", command=self.rebuild_cache).pack(side='left', padx=5)
        
        # Search
        search_frame = ttk.Frame(tab)
        search_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side='left')
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_apps)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side='left', fill='x', expand=True, padx=5)

        # List
        self.app_tree = ttk.Treeview(tab, columns=('Name', 'Type', 'Path'), show='headings')
        self.app_tree.heading('Name', text='Name')
        self.app_tree.heading('Type', text='Type')
        self.app_tree.heading('Path', text='Path/AUMID')
        self.app_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.refresh_apps()

    def refresh_apps(self):
        self.indexer._load_app_cache()
        self.update_app_list(self.indexer.apps)

    def rebuild_cache(self):
        self.log_area.insert(tk.END, "Rebuilding app cache...\n")
        self.indexer.build_cache(force_rebuild=True)
        self.refresh_apps()
        self.log_area.insert(tk.END, "App cache rebuilt.\n")

    def filter_apps(self, *args):
        query = self.search_var.get().lower()
        if not query:
            self.update_app_list(self.indexer.apps)
            return
            
        filtered = {k: v for k, v in self.indexer.apps.items() if query in k.lower()}
        self.update_app_list(filtered)

    def update_app_list(self, apps):
        for item in self.app_tree.get_children():
            self.app_tree.delete(item)
        
        for name, data in apps.items():
            path = data.get('path') or data.get('aumid') or ""
            self.app_tree.insert('', tk.END, values=(name, data.get('type'), path))

    def start_agent(self):
        if not self.is_running:
            self.status_var.set("Status: Running")
            self.start_btn.configure(state='disabled')
            self.stop_btn.configure(state='normal')
            self.is_running = True
            
            # Run in thread
            threading.Thread(target=self.assistant.start).start()

    def stop_agent(self):
        if self.is_running:
            self.status_var.set("Status: Stopping...")
            self.assistant.stop()
            self.status_var.set("Status: Stopped")
            self.start_btn.configure(state='normal')
            self.stop_btn.configure(state='disabled')
            self.is_running = False

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceAgentGUI(root)
    root.mainloop()
