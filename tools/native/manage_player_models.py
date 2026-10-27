#!/usr/bin/env python3
"""Desktop player-model manager, opened before gameplay from Settings → Mods."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog

from player_models.install import change, profile_manifest, selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    args = parser.parse_args()
    root = tk.Tk()
    root.title('Ocarina ReTuned — Player models')
    root.minsize(520, 310)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Player appearance', font=('', 18, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Import a human-rig OoT PAK or ZOBJ for each age.\nSaves, settings, and textures are preserved.').pack(anchor='w', pady=(8, 16))
    age = tk.StringVar(value='child')
    mode = tk.StringVar(value='Original Link')
    status = tk.StringVar()
    choices = ttk.Frame(frame)
    choices.pack(fill='x')
    for label, value in (('Child', 'child'), ('Adult', 'adult')):
        ttk.Radiobutton(choices, text=label, value=value, variable=age).pack(side='left', padx=(0, 18))
    ttk.Label(frame, text='Player model').pack(anchor='w', pady=(16, 4))
    picker = ttk.Combobox(frame, textvariable=mode, values=('Original Link', 'PAK Importer'), state='readonly')
    picker.pack(fill='x')
    current = tk.StringVar()
    ttk.Label(frame, textvariable=current).pack(anchor='w', pady=8)
    ttk.Label(frame, textvariable=status, wraplength=470).pack(anchor='w', pady=8)
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x', pady=(8, 0))
    executor = ThreadPoolExecutor(max_workers=1)
    job = None

    def refresh(*unused):
        try:
            _, _, manifest = profile_manifest(args.data)
            active = selection(manifest).get(age.get())
            retained = selection(manifest, 'available_player_models').get(age.get())
            mode.set('PAK Importer' if active else 'Original Link')
            current.set('Imported model: ' + retained.get('name', 'PAK') if retained else 'No imported model for this age')
        except (OSError, ValueError, KeyError):
            status.set('Prepare your game before importing a player model.')

    def set_busy(busy):
        for widget in (*choices.winfo_children(), picker, *buttons.winfo_children()):
            widget.configure(state='disabled' if busy else ('readonly' if widget is picker else 'normal'))

    def poll():
        nonlocal job
        if not job.done():
            root.after(100, poll)
            return
        try:
            job.result()
            status.set('Player model ready. Close this window to reopen the game.')
        except Exception:
            status.set('The model could not be applied. Choose a supported human-rig OoT PAK or ZOBJ. Your previous selection is unchanged.')
        finally:
            job = None
            set_busy(False)
            refresh()

    def apply(package=None):
        nonlocal job
        if job is not None:
            return
        if not package:
            _, _, manifest = profile_manifest(args.data)
            active = bool(selection(manifest).get(age.get()))
            if active == (mode.get() == 'PAK Importer'):
                status.set('This model is already selected.')
                return
        status.set('Converting and verifying model…' if package else 'Updating model selection…')
        set_busy(True)
        job = executor.submit(change, args.data, age=age.get(), package=package,
                              use_imported=not package and mode.get() == 'PAK Importer')
        root.after(100, poll)

    def browse():
        package = filedialog.askopenfilename(parent=root, title='Import player model',
                                             filetypes=(('Player models', '*.pak *.zobj'), ('All files', '*')))
        if package:
            mode.set('PAK Importer')
            apply(package)

    ttk.Button(buttons, text='Import PAK file', command=browse).pack(side='left')
    ttk.Button(buttons, text='Apply selection', command=apply).pack(side='left', padx=8)
    ttk.Button(buttons, text='Done', command=lambda: close()).pack(side='right')
    age.trace_add('write', refresh)

    def close():
        if job is None:
            root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    refresh()
    root.mainloop()
    executor.shutdown(wait=True)


if __name__ == '__main__':
    main()
