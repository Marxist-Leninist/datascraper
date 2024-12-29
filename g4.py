#!/usr/bin/env python3
"""
datascraper_advanced_singlefile.py

A more advanced, GUI-based web crawler that:
 - Takes a starting URL (default: https://www.wikipedia.org).
 - Follows links BFS-style across multiple domains (be cautious).
 - Saves *all* scraped text into a timestamped text file.
 - Or, optionally appends to a previous file if the user chooses so.
 - Provides a simple start/stop mechanism in the GUI.

Dependencies:
  pip install requests beautifulsoup4

WARNING:
  This tool can discover thousands of links quickly if not constrained.
  Use responsibly, respect site usage policies and robots.txt.
"""

import os
import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import requests
from collections import deque
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def get_timestamped_filename(base_name="scraped_data"):
    """
    Returns a filename like: scraped_data_YYYYmmdd-HHMMSS.txt
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{base_name}_{timestamp}.txt"

class AggressiveCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Aggressive DataScraper for LLM (Single File)")

        # Default URL and maximum pages
        self.default_url = "https://www.wikipedia.org"
        self.max_pages_default = 50

        # BFS-related
        self.queue = deque()
        self.visited = set()
        self.running = False  # controls the scraping loop

        # Dynamically build the default output filename with a timestamp
        self.output_file = get_timestamped_filename()

        # Build the GUI
        self._build_gui()

    def _build_gui(self):
        # Row 0: URL label + Entry
        lbl_url = tk.Label(self.root, text="Starting URL:")
        lbl_url.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.url_entry = tk.Entry(self.root, width=60)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.url_entry.insert(0, self.default_url)

        # Row 1: Max pages label + Entry
        lbl_max = tk.Label(self.root, text="Max pages:")
        lbl_max.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.max_pages_entry = tk.Entry(self.root, width=20)
        self.max_pages_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.max_pages_entry.insert(0, str(self.max_pages_default))

        # Row 2: Use existing file? Checkbutton
        self.use_existing_var = tk.BooleanVar(value=False)
        chk_use_existing = tk.Checkbutton(
            self.root,
            text="Append to existing file instead of creating new one",
            variable=self.use_existing_var
        )
        chk_use_existing.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Row 3: Buttons: Start, Stop
        self.btn_start = tk.Button(self.root, text="Start Scraping", command=self.start_scraping)
        self.btn_start.grid(row=3, column=0, padx=5, pady=5)

        self.btn_stop = tk.Button(self.root, text="Stop Scraping", command=self.stop_scraping)
        self.btn_stop.grid(row=3, column=1, padx=5, pady=5)

        # Row 4: Output scrolled text
        self.output_area = scrolledtext.ScrolledText(self.root, width=80, height=20, wrap=tk.WORD)
        self.output_area.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

        # Info label
        info = (
            "This tool aggressively crawls the web BFS-style from the starting URL.\n"
            "Be cautious: it can discover thousands of links quickly if not limited!\n"
            "Starting URL and Max pages will apply to the new scrape.\n"
            "Check 'Append to existing file' to use the same file name, otherwise a new one is generated."
        )
        lbl_info = tk.Label(self.root, text=info, fg="blue")
        lbl_info.grid(row=5, column=0, columnspan=3, padx=5, pady=5)

    def start_scraping(self):
        # If user wants to create a new file (use_existing_var == False), generate a new name
        if not self.use_existing_var.get():
            self.output_file = get_timestamped_filename()

        # Reset BFS structures
        self.queue.clear()
        self.visited.clear()

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please provide a starting URL.")
            return

        try:
            max_pages = int(self.max_pages_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Max pages must be an integer.")
            return

        # Add starting URL
        self.queue.append(url)
        self.visited.add(url)

        # Clear output area
        self.output_area.delete("1.0", tk.END)
        self.output_area.insert(tk.END, f"[INFO] Output file: {self.output_file}\n")
        self.output_area.insert(tk.END, f"[INFO] Starting BFS from: {url}\n")

        # Open the file with a header
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write("=== Begin scraping ===\n")

        self.running = True
        self.scrape_thread = threading.Thread(target=self.run_bfs, args=(max_pages,))
        self.scrape_thread.start()

    def stop_scraping(self):
        self.running = False
        self.output_area.insert(tk.END, "[INFO] Stop requested...\n")

    def run_bfs(self, max_pages):
        page_count = 0

        while self.running and page_count < max_pages and self.queue:
            current_url = self.queue.popleft()
            success = self.scrape_page(current_url, page_count + 1)
            if success:
                page_count += 1

        self.output_area.insert(tk.END, f"\n[INFO] BFS finished. Total pages scraped: {page_count}\n")
        self.running = False

    def scrape_page(self, url, page_id):
        """
        1) GET the URL
        2) Extract text => append to the output file
        3) BFS link extraction => add new links to queue
        """
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.output_area.insert(tk.END, f"[ERROR] {url} => {e}\n")
            return False

        soup = BeautifulSoup(resp.text, "html.parser")
        text_content = soup.get_text(separator="\n").strip()

        # Append to single text file
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(f"\n=== Page #{page_id}: {url} ===\n\n")
            f.write(text_content)
            f.write("\n\n")

        self.output_area.insert(tk.END, f"[SCRAPED] Page #{page_id}: {url}\n")
        self.output_area.see(tk.END)

        # BFS link extraction
        for link in soup.find_all("a"):
            href = link.get("href")
            if not href:
                continue
            absolute_url = urljoin(url, href)
            parsed = urlparse(absolute_url)
            if parsed.scheme.startswith("http"):
                if absolute_url not in self.visited:
                    self.visited.add(absolute_url)
                    self.queue.append(absolute_url)

        return True

def main():
    root = tk.Tk()
    app = AggressiveCrawlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
