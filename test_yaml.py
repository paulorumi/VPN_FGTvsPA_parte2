import yaml

with open("config/vpn_params_example.yaml", "r") as f:
    cfg = yaml.safe_load(f)

print("Conteúdo carregado do YAML:")
print(cfg)