"""
PDF to CSV - GUI

Seleciona múltiplos PDFs, extrai tabelas usando pdfplumber e exporta para CSV.
Requisitos: pdfplumber

Uso: executar o script e escolher arquivos e pasta de saída.
"""

import threading
import csv
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import pdfplumber
except Exception:
    pdfplumber = None


def extract_tables_from_pdf(pdf_path: Path, out_dir: Path, progress_callback=None):
    """Extrai tabelas de um PDF e salva como CSVs no out_dir.
    Retorna número de tabelas extraídas.
    """
    count = 0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    tables = page.extract_tables()
                except Exception:
                    tables = []

                for t_index, table in enumerate(tables, start=1):
                    # table é lista de linhas (listas)
                    if not table:
                        continue

                    stem = pdf_path.stem
                    out_name = f"{stem}_page{page_num}_table{t_index}.csv"
                    out_path = out_dir / out_name

                    # garante nome unico
                    i = 1
                    while out_path.exists():
                        out_path = out_dir / f"{stem}_page{page_num}_table{t_index} ({i}).csv"
                        i += 1

                    with open(out_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        for row in table:
                            # normaliza valores None -> ''
                            row_norm = [cell if cell is not None else '' for cell in row]
                            writer.writerow(row_norm)

                    count += 1
                    if progress_callback:
                        progress_callback(pdf_path, out_path)
    except Exception as e:
        raise

    return count


class App:
    def __init__(self, root):
        self.root = root
        root.title('PDF to CSV')
        root.geometry('640x420')

        main = ttk.Frame(root, padding=12)
        main.pack(fill='both', expand=True)

        # file selection
        file_frame = ttk.LabelFrame(main, text='Arquivos PDF')
        file_frame.pack(fill='both', expand=False, pady=(0, 8))

        btn_select = ttk.Button(file_frame, text='Selecionar PDFs', command=self.select_files)
        btn_select.grid(row=0, column=0, padx=6, pady=6, sticky='w')

        btn_clear = ttk.Button(file_frame, text='Limpar', command=self.clear_files)
        btn_clear.grid(row=0, column=1, padx=6, pady=6, sticky='w')

        self.listbox = tk.Listbox(file_frame, height=8)
        self.listbox.grid(row=1, column=0, columnspan=3, sticky='nsew', padx=6, pady=(0,6))
        file_frame.columnconfigure(2, weight=1)

        # output folder
        out_frame = ttk.Frame(main)
        out_frame.pack(fill='x', pady=(0,8))

        ttk.Label(out_frame, text='Pasta de saída:').grid(row=0, column=0, sticky='w')
        self.out_var = tk.StringVar()
        self.out_entry = ttk.Entry(out_frame, textvariable=self.out_var, width=60)
        self.out_entry.grid(row=0, column=1, padx=6, sticky='w')

        btn_out = ttk.Button(out_frame, text='Selecionar...', command=self.select_out)
        btn_out.grid(row=0, column=2, padx=6)

        # options
        opt_frame = ttk.Frame(main)
        opt_frame.pack(fill='x', pady=(0,8))

        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, text='Procurar recursivamente em subpastas', variable=self.recursive_var).grid(row=0, column=0, sticky='w')

        # run
        run_frame = ttk.Frame(main)
        run_frame.pack(fill='x', pady=(0,8))

        self.btn_run = ttk.Button(run_frame, text='Extrair para CSV', command=self.start_extraction)
        self.btn_run.grid(row=0, column=0, padx=6)

        self.btn_open_out = ttk.Button(run_frame, text='Abrir pasta de saída', command=self.open_out_dir)
        self.btn_open_out.grid(row=0, column=1, padx=6)

        # progress
        prog_frame = ttk.LabelFrame(main, text='Progresso')
        prog_frame.pack(fill='both', expand=True)

        self.progress_text = tk.Text(prog_frame, height=10, state='disabled')
        self.progress_text.pack(fill='both', expand=True, padx=6, pady=6)

        # store files
        self.files = []

    def select_files(self):
        files = filedialog.askopenfilenames(title='Selecione PDFs', filetypes=[('PDF files', '*.pdf')])
        if files:
            for f in files:
                if f not in self.files:
                    self.files.append(f)
                    self.listbox.insert('end', f)

    def clear_files(self):
        self.files = []
        self.listbox.delete(0, 'end')

    def select_out(self):
        d = filedialog.askdirectory(title='Pasta de saída')
        if d:
            self.out_var.set(d)

    def open_out_dir(self):
        out = self.out_var.get() or ''
        if not out:
            messagebox.showinfo('Info', 'Informe a pasta de saída primeiro.')
            return
        p = Path(out)
        if not p.exists():
            messagebox.showerror('Erro', 'Pasta de saída não existe.')
            return
        try:
            if sys.platform.startswith('win'):
                import subprocess
                subprocess.Popen(['explorer', str(p)])
            else:
                import webbrowser
                webbrowser.open(str(p))
        except Exception as e:
            messagebox.showerror('Erro', f'Não foi possível abrir a pasta: {e}')

    def log(self, message: str):
        self.progress_text.configure(state='normal')
        self.progress_text.insert('end', message + '\n')
        self.progress_text.see('end')
        self.progress_text.configure(state='disabled')

    def progress_callback(self, pdf_path, out_path):
        self.log(f'Extraido: {pdf_path.name} -> {out_path.name}')

    def start_extraction(self):
        if pdfplumber is None:
            messagebox.showerror('Dependencia ausente', 'Biblioteca pdfplumber não encontrada. Instale com:\n\npip install pdfplumber')
            return

        if not self.files:
            messagebox.showinfo('Info', 'Selecione ao menos um arquivo PDF.')
            return

        out = self.out_var.get() or ''
        if not out:
            messagebox.showinfo('Info', 'Selecione a pasta de saída.')
            return

        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)

        # disable UI
        self.btn_run.config(state='disabled')
        self.log('Iniciando extração...')

        # run in thread
        t = threading.Thread(target=self._run_extraction, args=(list(self.files), out_path, self.recursive_var.get()))
        t.daemon = True
        t.start()

    def _run_extraction(self, files, out_path: Path, recursivo: bool):
        total_tables = 0
        for f in files:
            p = Path(f)
            # if recursivo and is dir? We didn't allow selecting dirs; keep simple
            try:
                n = extract_tables_from_pdf(p, out_path, progress_callback=self.progress_callback)
                if n == 0:
                    self.log(f'Nenhuma tabela encontrada em {p.name}')
                total_tables += n
            except Exception as e:
                self.log(f'Erro ao processar {p.name}: {e}')

        self.log(f'Concluído. Total de tabelas extraídas: {total_tables}')
        self.btn_run.config(state='normal')


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
