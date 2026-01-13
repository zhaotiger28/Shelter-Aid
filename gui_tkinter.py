import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

from algov1 import process_csv, write_ranked_csv


def human_path(p):
    return p


class ShelterApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Shelter Ranker (Desktop)')

        frm = ttk.Frame(root, padding=12)
        frm.pack(fill='both', expand=True)

        lbl_text = 'Drop a CSV here (if supported) or click "Open CSV".'
        if not DND_AVAILABLE:
            lbl_text = 'Drag-and-drop not available. Click "Open CSV" to select a file.'

        self.drop_label = ttk.Label(frm, text=lbl_text, relief='ridge', padding=20)
        self.drop_label.pack(fill='x')

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill='x', pady=8)

        open_btn = ttk.Button(btn_frame, text='Open CSV', command=self.open_file)
        open_btn.pack(side='left')

        save_btn = ttk.Button(btn_frame, text='Save ranked CSV', command=self.save_ranked, state='disabled')
        save_btn.pack(side='left', padx=8)
        self.save_btn = save_btn

        self.tree = ttk.Treeview(frm, columns=('rank','name','niche','score','finance','supply','population','urgency','capacity'), show='headings')
        for col in self.tree['columns']:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor='w')
        self.tree.pack(fill='both', expand=True)

        self.shelters = None

        if DND_AVAILABLE:
            try:
                # If using TkinterDnD2, we need the special root
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self._on_drop)
            except Exception:
                pass

    def _on_drop(self, event):
        data = event.data
        # data may be like '{C:/path/to/file.csv}' or 'C:/path/to/file.csv'
        data = data.strip()
        if data.startswith('{') and data.endswith('}'):
            data = data[1:-1]
        path = data.split()[-1]
        if os.path.isfile(path):
            self.load_and_display(path)

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[('CSV files','*.csv'), ('All files','*.*')])
        if path:
            self.load_and_display(path)

    def load_and_display(self, path):
        try:
            shelters = process_csv(path)
        except Exception as e:
            messagebox.showerror('Processing error', f'Failed to process CSV:\n{e}')
            return

        self.shelters = shelters
        self.save_btn.config(state='normal')

        # clear tree
        for r in self.tree.get_children():
            self.tree.delete(r)

        display_fields = ['rank','name','niche','score','finance','supply','population','urgency','capacity']
        for s in shelters:
            vals = [s.get(f) for f in display_fields]
            self.tree.insert('', 'end', values=vals)

    def save_ranked(self):
        if not self.shelters:
            return
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], initialfile='ranked_shelters.csv')
        if not path:
            return
        try:
            write_ranked_csv(self.shelters, path)
            messagebox.showinfo('Saved', f'Wrote ranked CSV to:\n{path}')
        except Exception as e:
            messagebox.showerror('Save failed', f'Could not save file:\n{e}')


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = ShelterApp(root)
    root.geometry('900x600')
    root.mainloop()


if __name__ == '__main__':
    main()
