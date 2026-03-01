#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import scrolledtext

import yaml

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "vpn_params_example.yaml"
FGT_SCRIPT = BASE_DIR / "scripts" / "configure_vpn_fortigate.py"
PA_SCRIPT = BASE_DIR / "scripts" / "configure_vpn_paloalto.py"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        messagebox.showerror("Erro", f"Arquivo de config não encontrado:\n{CONFIG_PATH}")
        return {}
    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f) or {}
    # Garantir chaves mínimas
    data.setdefault("vpn", {})
    data["vpn"].setdefault("psk", "admin123")
    data["vpn"].setdefault("remote_gw_fgt", "2.2.2.2")
    data["vpn"].setdefault("remote_gw_pa", "1.1.1.1")

    data["vpn"].setdefault("networks", {})
    data["vpn"]["networks"].setdefault("site_a", "10.10.10.0/24")
    data["vpn"]["networks"].setdefault("site_b", "10.20.20.0/24")

    data["vpn"].setdefault("ike_phase1", {})
    data["vpn"]["ike_phase1"].setdefault("encryption", "des")
    data["vpn"]["ike_phase1"].setdefault("integrity", "sha1")
    data["vpn"]["ike_phase1"].setdefault("dh_group", 2)
    data["vpn"]["ike_phase1"].setdefault("lifetime", 28800)

    data["vpn"].setdefault("ipsec_phase2", {})
    data["vpn"]["ipsec_phase2"].setdefault("encryption", "des")
    data["vpn"]["ipsec_phase2"].setdefault("integrity", "sha1")
    data["vpn"]["ipsec_phase2"].setdefault("dh_group", 2)
    data["vpn"]["ipsec_phase2"].setdefault("lifetime", 3600)
    data["vpn"]["ipsec_phase2"].setdefault("pfs", False)

    # lista de pares de redes para phase2 (opcional)
    data["vpn"].setdefault("phase2_pairs", [])
    return data


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)


class VPNGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Automação VPN IPSec - Fortigate x Palo Alto")
        self.geometry("980x700")
        self.resizable(False, False)

        self.config_data = load_config()

        # lista de linhas de phase2: cada item = dict com StringVars e widgets
        self.phase2_rows: list[dict] = []

        self.create_widgets()
        self.populate_fields()
        self.log("Aplicação iniciada.")
        self.log(f"Config carregada de: {CONFIG_PATH}")

    # ---------------- LOG ---------------- #

    def log(self, msg: str):
        """Escreve uma linha no painel de log."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ------------- EXECUÇÃO DE SCRIPTS ------------- #

    def run_script(self, path: Path, title: str) -> bool:
        if not path.exists():
            msg = f"Script não encontrado: {path}"
            self.log(f"[ERRO] {msg}")
            messagebox.showerror("Erro", msg)
            return False

        self.log(f"[INFO] Executando {title}: {path}")
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
            )
        except Exception as e:
            msg = f"Falha ao executar {title}: {e}"
            self.log(f"[ERRO] {msg}")
            messagebox.showerror("Erro na automação", msg)
            return False

        self.log(f"[INFO] {title} finalizado com código {result.returncode}")

        if result.stdout:
            self.log("----- STDOUT -----")
            for line in result.stdout.splitlines():
                self.log(line)
        if result.stderr:
            self.log("----- STDERR -----")
            for line in result.stderr.splitlines():
                self.log(line)
        self.log("----- FIM -----\n")

        if result.returncode != 0:
            messagebox.showerror(
                "Erro na automação",
                f"{title} terminou com erro (code {result.returncode}). "
                f"Veja detalhes no painel de log."
            )
            return False

        return True

    # ---------------- UI ---------------- #

    def create_widgets(self):
        # parte de cima: notebook com parâmetros
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        notebook = ttk.Notebook(top_frame)
        notebook.pack(fill="both", expand=True)

        frame_params = ttk.Frame(notebook)
        notebook.add(frame_params, text="Parâmetros da VPN")

        # Frames internos
        frame_peers = ttk.LabelFrame(frame_params, text="Peers (Ponta A / Ponta B)")
        frame_peers.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        frame_common = ttk.LabelFrame(frame_params, text="Parâmetros Comuns (Phase 1 & 2)")
        frame_common.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.frame_networks = ttk.LabelFrame(frame_params, text="Redes (Phase 2) - Fortigate x Palo Alto")
        self.frame_networks.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        frame_params.columnconfigure(0, weight=1)

        # --- Peers --- #
        ttk.Label(frame_peers, text="Peer IP Fortigate (Ponta A) -> PA WAN:").grid(
            row=0, column=0, sticky="e", padx=5, pady=3
        )
        self.var_peer_fgt = tk.StringVar()
        ttk.Entry(frame_peers, textvariable=self.var_peer_fgt, width=20).grid(
            row=0, column=1, sticky="w", padx=5, pady=3
        )

        ttk.Label(frame_peers, text="Peer IP Palo Alto (Ponta B) -> FGT WAN:").grid(
            row=1, column=0, sticky="e", padx=5, pady=3
        )
        self.var_peer_pa = tk.StringVar()
        ttk.Entry(frame_peers, textvariable=self.var_peer_pa, width=20).grid(
            row=1, column=1, sticky="w", padx=5, pady=3
        )

        ttk.Label(frame_peers, text="PSK (Pre-Shared Key):").grid(
            row=2, column=0, sticky="e", padx=5, pady=3
        )
        self.var_psk = tk.StringVar()
        ttk.Entry(frame_peers, textvariable=self.var_psk, width=20, show="*").grid(
            row=2, column=1, sticky="w", padx=5, pady=3
        )

        # --- Parâmetros comuns: Phase 1 & 2 --- #
        enc_options = ["des", "aes128"]
        auth_options = ["sha1", "sha256"]
        dh_options = [2, 5, 14]

        row = 0
        ttk.Label(frame_common, text="Phase 1 - Encryption:").grid(
            row=row, column=0, sticky="e", padx=5, pady=3
        )
        self.var_p1_enc = tk.StringVar()
        ttk.Combobox(
            frame_common,
            textvariable=self.var_p1_enc,
            values=enc_options,
            width=10,
            state="readonly",
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(frame_common, text="Phase 1 - Authentication:").grid(
            row=row, column=2, sticky="e", padx=5, pady=3
        )
        self.var_p1_auth = tk.StringVar()
        ttk.Combobox(
            frame_common,
            textvariable=self.var_p1_auth,
            values=auth_options,
            width=10,
            state="readonly",
        ).grid(row=row, column=3, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(frame_common, text="Phase 1 - DH Group:").grid(
            row=row, column=0, sticky="e", padx=5, pady=3
        )
        self.var_p1_dh = tk.IntVar()
        ttk.Combobox(
            frame_common,
            textvariable=self.var_p1_dh,
            values=dh_options,
            width=10,
            state="readonly",
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(frame_common, text="Phase 1 - Lifetime (s):").grid(
            row=row, column=2, sticky="e", padx=5, pady=3
        )
        self.var_p1_lifetime = tk.StringVar()
        ttk.Entry(frame_common, textvariable=self.var_p1_lifetime, width=10).grid(
            row=row, column=3, sticky="w", padx=5, pady=3
        )

        # Phase 2
        row += 1
        ttk.Label(frame_common, text="Phase 2 - Encryption:").grid(
            row=row, column=0, sticky="e", padx=5, pady=3
        )
        self.var_p2_enc = tk.StringVar()
        ttk.Combobox(
            frame_common,
            textvariable=self.var_p2_enc,
            values=enc_options,
            width=10,
            state="readonly",
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(frame_common, text="Phase 2 - Authentication:").grid(
            row=row, column=2, sticky="e", padx=5, pady=3
        )
        self.var_p2_auth = tk.StringVar()
        ttk.Combobox(
            frame_common,
            textvariable=self.var_p2_auth,
            values=auth_options,
            width=10,
            state="readonly",
        ).grid(row=row, column=3, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(frame_common, text="Phase 2 - DH Group:").grid(
            row=row, column=0, sticky="e", padx=5, pady=3
        )
        self.var_p2_dh = tk.IntVar()
        ttk.Combobox(
            frame_common,
            textvariable=self.var_p2_dh,
            values=dh_options,
            width=10,
            state="readonly",
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(frame_common, text="Phase 2 - Lifetime (s):").grid(
            row=row, column=2, sticky="e", padx=5, pady=3
        )
        self.var_p2_lifetime = tk.StringVar()
        ttk.Entry(frame_common, textvariable=self.var_p2_lifetime, width=10).grid(
            row=row, column=3, sticky="w", padx=5, pady=3
        )

        # --- Redes (Phase2) dinâmicas --- #
        self.build_phase2_networks_frame()

        # --- Botões --- #
        frame_buttons = ttk.Frame(self)
        frame_buttons.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Button(frame_buttons, text="Salvar YAML (ambos)", command=self.on_save).pack(
            side="left", padx=5
        )

        frame_fgt_btns = ttk.LabelFrame(frame_buttons, text="Fortigate")
        frame_fgt_btns.pack(side="left", padx=10)
        ttk.Button(
            frame_fgt_btns, text="Aplicar Fortigate", command=self.on_apply_fgt
        ).pack(side="left", padx=5, pady=3)

        frame_pa_btns = ttk.LabelFrame(frame_buttons, text="Palo Alto")
        frame_pa_btns.pack(side="left", padx=10)
        ttk.Button(
            frame_pa_btns, text="Aplicar Palo Alto", command=self.on_apply_pa
        ).pack(side="left", padx=5, pady=3)

        ttk.Button(frame_buttons, text="Fechar", command=self.destroy).pack(
            side="right", padx=5
        )

        # --- Área de Log --- #
        frame_log = ttk.LabelFrame(self, text="Log da Automação")
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(
            frame_log, wrap="word", height=10, state="disabled"
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    # ------- Phase2 Networks UI ------- #

    def build_phase2_networks_frame(self):
        """
        Constrói cabeçalho da tabela de redes e área onde as linhas serão inseridas.
        """
        f = self.frame_networks

        # Cabeçalho
        # Colunas: Par | FGT Local | FGT Remote | PA Local | PA Remote
        ttk.Label(f, text="#").grid(row=0, column=0, padx=5, pady=3)
        ttk.Label(f, text="Fortigate - Local").grid(row=0, column=1, padx=5, pady=3)
        ttk.Label(f, text="Fortigate - Remote").grid(row=0, column=2, padx=5, pady=3)
        ttk.Label(f, text="Palo Alto - Local").grid(row=0, column=3, padx=5, pady=3)
        ttk.Label(f, text="Palo Alto - Remote").grid(row=0, column=4, padx=5, pady=3)

        # Área de linhas começa na row=1
        self.phase2_rows_frame = f

        # Botões Add/Remove
        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=999, column=0, columnspan=5, sticky="w", padx=5, pady=5)

        ttk.Button(btn_frame, text="Adicionar par de redes", command=self.add_phase2_row).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="Remover último par", command=self.remove_phase2_row).pack(
            side="left", padx=5
        )

    def add_phase2_row(self, values=None):
        """
        Adiciona uma linha de pares de redes.
        values pode ser um dict com chaves:
         - fgt_local, fgt_remote, pa_local, pa_remote
        """
        row_index = len(self.phase2_rows) + 1  # começa em 1 (linha 0 é cabeçalho)

        var_fgt_local = tk.StringVar()
        var_fgt_remote = tk.StringVar()
        var_pa_local = tk.StringVar()
        var_pa_remote = tk.StringVar()

        if values:
            var_fgt_local.set(values.get("fgt_local", ""))
            var_fgt_remote.set(values.get("fgt_remote", ""))
            var_pa_local.set(values.get("pa_local", ""))
            var_pa_remote.set(values.get("pa_remote", ""))
        else:
            # defaults vazios; serão preenchidos ou validados depois
            pass

        ttk.Label(self.phase2_rows_frame, text=str(row_index)).grid(
            row=row_index, column=0, padx=5, pady=2
        )
        e1 = ttk.Entry(self.phase2_rows_frame, textvariable=var_fgt_local, width=18)
        e1.grid(row=row_index, column=1, padx=5, pady=2)
        e2 = ttk.Entry(self.phase2_rows_frame, textvariable=var_fgt_remote, width=18)
        e2.grid(row=row_index, column=2, padx=5, pady=2)
        e3 = ttk.Entry(self.phase2_rows_frame, textvariable=var_pa_local, width=18)
        e3.grid(row=row_index, column=3, padx=5, pady=2)
        e4 = ttk.Entry(self.phase2_rows_frame, textvariable=var_pa_remote, width=18)
        e4.grid(row=row_index, column=4, padx=5, pady=2)

        self.phase2_rows.append(
            {
                "row": row_index,
                "fgt_local_var": var_fgt_local,
                "fgt_remote_var": var_fgt_remote,
                "pa_local_var": var_pa_local,
                "pa_remote_var": var_pa_remote,
                "widgets": (e1, e2, e3, e4),
            }
        )

    def remove_phase2_row(self):
        """Remove a última linha de pares de redes, mas garante pelo menos 1."""
        if len(self.phase2_rows) <= 1:
            messagebox.showwarning(
                "Aviso",
                "É obrigatório ter pelo menos um par de Local/Remote Address.",
            )
            return

        last = self.phase2_rows.pop()
        # Apaga widgets da tela
        for w in last["widgets"]:
            w.destroy()
        # também remove label do índice
        row_idx = last["row"]
        for widget in self.phase2_rows_frame.grid_slaves(row=row_idx):
            widget.destroy()

    # ---------------- POPULAR CAMPOS ---------------- #

    def populate_fields(self):
        """Preenche os campos com base no YAML carregado."""
        vpn = self.config_data["vpn"]

        self.var_peer_fgt.set(vpn.get("remote_gw_fgt", "2.2.2.2"))
        self.var_peer_pa.set(vpn.get("remote_gw_pa", "1.1.1.1"))
        self.var_psk.set(vpn.get("psk", "admin123"))

        ike = vpn["ike_phase1"]
        self.var_p1_enc.set(ike.get("encryption", "des"))
        self.var_p1_auth.set(ike.get("integrity", "sha1"))
        self.var_p1_dh.set(int(ike.get("dh_group", 2)))
        self.var_p1_lifetime.set(str(ike.get("lifetime", 28800)))

        ipsec = vpn["ipsec_phase2"]
        self.var_p2_enc.set(ipsec.get("encryption", "des"))
        self.var_p2_auth.set(ipsec.get("integrity", "sha1"))
        self.var_p2_dh.set(int(ipsec.get("dh_group", 2)))
        self.var_p2_lifetime.set(str(ipsec.get("lifetime", 3600)))

        nets = vpn["networks"]
        site_a = nets.get("site_a", "10.10.10.0/24")
        site_b = nets.get("site_b", "10.20.20.0/24")

        # Montar linhas de phase2 a partir de vpn.phase2_pairs se existir
        pairs = vpn.get("phase2_pairs") or []
        if pairs:
            for p in pairs:
                self.add_phase2_row(p)
        else:
            # Se não tem lista ainda, criar 1 linha padrão, coerente com config atual:
            # - Fortigate Local = site_a
            # - Fortigate Remote = site_b
            # - Palo Alto Local = site_b
            # - Palo Alto Remote = site_a
            self.add_phase2_row(
                {
                    "fgt_local": site_a,
                    "fgt_remote": site_b,
                    "pa_local": site_b,
                    "pa_remote": site_a,
                }
            )

    # ---------------- HANDLERS ---------------- #

    def on_save(self):
        """Só salva o YAML com os valores da tela."""
        if not self.update_config_from_fields():
            return
        save_config(self.config_data)
        self.log("Configuração salva em vpn_params_example.yaml.")
        messagebox.showinfo("Salvar", "Configuração salva com sucesso em vpn_params_example.yaml.")

    def on_apply_fgt(self):
        """Salva YAML e aplica APENAS no Fortigate."""
        if not self.update_config_from_fields():
            return
        save_config(self.config_data)
        self.log("Configuração salva. Iniciando automação Fortigate...")
        if self.run_script(FGT_SCRIPT, "Configuração Fortigate"):
            messagebox.showinfo(
                "Automação Fortigate",
                "Configuração aplicada no Fortigate.\nVeja detalhes no painel de log.",
            )

    def on_apply_pa(self):
        """Salva YAML e aplica APENAS no Palo Alto."""
        if not self.update_config_from_fields():
            return
        save_config(self.config_data)
        self.log("Configuração salva. Iniciando automação Palo Alto...")
        if self.run_script(PA_SCRIPT, "Configuração Palo Alto"):
            messagebox.showinfo(
                "Automação Palo Alto",
                "Configuração aplicada no Palo Alto.\nVeja detalhes no painel de log.",
            )

    def update_config_from_fields(self) -> bool:
        """Atualiza self.config_data com base nos campos da UI (incluindo os pares de redes)."""
        try:
            p1_life = int(self.var_p1_lifetime.get())
            p2_life = int(self.var_p2_lifetime.get())
        except ValueError:
            messagebox.showerror("Erro", "Lifetimes devem ser números inteiros (em segundos).")
            return False

        vpn = self.config_data["vpn"]

        vpn["psk"] = self.var_psk.get().strip()
        vpn["remote_gw_fgt"] = self.var_peer_fgt.get().strip()
        vpn["remote_gw_pa"] = self.var_peer_pa.get().strip()

        vpn["ike_phase1"]["encryption"] = self.var_p1_enc.get()
        vpn["ike_phase1"]["integrity"] = self.var_p1_auth.get()
        vpn["ike_phase1"]["dh_group"] = int(self.var_p1_dh.get())
        vpn["ike_phase1"]["lifetime"] = p1_life

        vpn["ipsec_phase2"]["encryption"] = self.var_p2_enc.get()
        vpn["ipsec_phase2"]["integrity"] = self.var_p2_auth.get()
        vpn["ipsec_phase2"]["dh_group"] = int(self.var_p2_dh.get())
        vpn["ipsec_phase2"]["lifetime"] = p2_life

        # Ler todos os pares de redes da tabela
        pairs = []
        for row in self.phase2_rows:
            fgt_local = row["fgt_local_var"].get().strip()
            fgt_remote = row["fgt_remote_var"].get().strip()
            pa_local = row["pa_local_var"].get().strip()
            pa_remote = row["pa_remote_var"].get().strip()

            # Validação mínima: todos os campos dessa linha devem estar preenchidos
            if not (fgt_local and fgt_remote and pa_local and pa_remote):
                messagebox.showerror(
                    "Erro",
                    "Todos os campos de Local/Remote Address devem estar preenchidos "
                    f"(linha {row['row']}).",
                )
                return False

            pairs.append(
                {
                    "fgt_local": fgt_local,
                    "fgt_remote": fgt_remote,
                    "pa_local": pa_local,
                    "pa_remote": pa_remote,
                }
            )

        if not pairs:
            messagebox.showerror(
                "Erro",
                "É obrigatório ter pelo menos um par de Local/Remote Address.",
            )
            return False

        # Salvar lista de pares no YAML
        vpn["phase2_pairs"] = pairs

        # Para manter compatibilidade com os scripts atuais:
        # - networks.site_a = Fortigate Local do primeiro par
        # - networks.site_b = Palo Alto Local do primeiro par
        vpn["networks"]["site_a"] = pairs[0]["fgt_local"]
        vpn["networks"]["site_b"] = pairs[0]["pa_local"]

        return True


if __name__ == "__main__":
    app = VPNGui()
    app.mainloop()