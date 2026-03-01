#!/usr/bin/env python3
import subprocess
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox
from pathlib import Path

from scripts.configure_vpn_fortigate import main as fgt_main
from configparser import ConfigParser  # não usado, mas se quiser depois

import yaml

BASE_DIR = Path(__file__).resolve().parent
VPN_YAML_PATH = BASE_DIR / "config" / "vpn_params_example.yaml"


def load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict):
    with open(path, "w") as f:
        yaml.safe_dump(data, f)


def run_fortigate_automation(output_widget: scrolledtext.ScrolledText,
                             entry_site_a: tk.Entry,
                             entry_site_b: tk.Entry):
    """
    Atualiza as redes de Phase 2 no YAML com o que foi digitado na GUI
    e depois chama o script de automação do Fortigate.
    """
    site_a = entry_site_a.get().strip()
    site_b = entry_site_b.get().strip()

    if not site_a or not site_b:
        messagebox.showwarning("Validação", "Preencha as redes de Phase 2 (Site A e Site B).")
        return

    output_widget.insert(tk.END, f"[GUI] Atualizando Phase 2 no YAML: site_a={site_a}, site_b={site_b}\n")
    output_widget.see(tk.END)

    try:
        cfg = load_yaml(VPN_YAML_PATH)
        cfg["vpn"]["networks"]["site_a"] = site_a
        cfg["vpn"]["networks"]["site_b"] = site_b
        save_yaml(VPN_YAML_PATH, cfg)
        output_widget.insert(tk.END, "[GUI] YAML atualizado com sucesso.\n")
    except Exception as e:
        output_widget.insert(tk.END, f"[GUI] ERRO ao atualizar YAML: {e}\n")
        output_widget.see(tk.END)
        return

    output_widget.insert(tk.END, "[GUI] Iniciando automação Fortigate...\n")
    output_widget.see(tk.END)
    try:
        fgt_main()
        output_widget.insert(tk.END, "[GUI] Automação Fortigate concluída.\n\n")
    except Exception as e:
        output_widget.insert(tk.END, f"[GUI] ERRO ao executar automação Fortigate: {e}\n\n")
    output_widget.see(tk.END)


def run_paloalto_info(output_widget: scrolledtext.ScrolledText):
    script_path = BASE_DIR / "scripts" / "configure_vpn_paloalto.py"
    if not script_path.exists():
        messagebox.showwarning("Aviso", "Script configure_vpn_paloalto.py não encontrado.")
        return

    output_widget.insert(tk.END, "[GUI] Executando script Palo Alto (conceitual)...\n")
    output_widget.see(tk.END)

    try:
        result = subprocess.run(
            ["python", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output_widget.insert(tk.END, "--- STDOUT Palo Alto ---\n")
        output_widget.insert(tk.END, result.stdout + "\n")
        if result.stderr:
            output_widget.insert(tk.END, "--- STDERR Palo Alto ---\n")
            output_widget.insert(tk.END, result.stderr + "\n")
    except Exception as e:
        output_widget.insert(tk.END, f"[GUI] ERRO ao executar script Palo Alto: {e}\n")

    output_widget.insert(tk.END, "\n[GUI] Execução Palo Alto finalizada.\n\n")
    output_widget.see(tk.END)


def ping_test(output_widget: scrolledtext.ScrolledText, dst_host: str = "10.20.20.1"):
    output_widget.insert(tk.END, f"[GUI] Testando ping para {dst_host}...\n")
    output_widget.see(tk.END)

    # Em Windows, troque '-c' por '-n' se necessário
    cmd = ["ping", "-c", "4", dst_host]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        report = {
            "host": dst_host,
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        output_widget.insert(tk.END, json.dumps(report, indent=2, ensure_ascii=False) + "\n\n")
    except Exception as e:
        output_widget.insert(tk.END, f"[GUI] ERRO ao executar ping: {e}\n\n")

    output_widget.see(tk.END)


def main():
    root = tk.Tk()
    root.title("Automação VPN - Fortigate x Palo Alto")

    # Frame para Phase 2
    phase2_frame = tk.LabelFrame(root, text="Redes Phase 2 (Proxy-ID / Subnets)")
    phase2_frame.pack(fill=tk.X, padx=10, pady=10)

    tk.Label(phase2_frame, text="Site A (local, ex: 10.10.10.0/24):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    entry_site_a = tk.Entry(phase2_frame, width=30)
    entry_site_a.grid(row=0, column=1, padx=5, pady=2)
    entry_site_a.insert(0, "10.10.10.0/24")

    tk.Label(phase2_frame, text="Site B (remoto, ex: 10.20.20.0/24):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    entry_site_b = tk.Entry(phase2_frame, width=30)
    entry_site_b.grid(row=1, column=1, padx=5, pady=2)
    entry_site_b.insert(0, "10.20.20.0/24")

    # Frame de botões
    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=10)

    btn_fgt = tk.Button(
        button_frame,
        text="Aplicar VPN no Fortigate",
        command=lambda: run_fortigate_automation(output_box, entry_site_a, entry_site_b),
        width=25,
    )
    btn_fgt.pack(side=tk.LEFT, padx=5)

    btn_pa = tk.Button(
        button_frame,
        text="Rodar automação Palo Alto (conceitual)",
        command=lambda: run_paloalto_info(output_box),
        width=30,
    )
    btn_pa.pack(side=tk.LEFT, padx=5)

    btn_ping = tk.Button(
        button_frame,
        text="Testar conectividade (ping 10.20.20.1)",
        command=lambda: ping_test(output_box, "10.20.20.1"),
        width=30,
    )
    btn_ping.pack(side=tk.LEFT, padx=5)

    # Caixa de saída
    output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=120, height=30)
    output_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()