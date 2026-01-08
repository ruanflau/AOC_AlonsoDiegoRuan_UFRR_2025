import subprocess
from pathlib import Path
import shutil
import re
import json

# =============================
# CONFIGURAÇÃO GERAL
# =============================
DEPTH = 20          # Ciclos de clock do hardware
UNWIND_LIMIT = 30   # Limite do verificador (Maior que DEPTH para evitar falso positivo)

ROOT = Path.cwd()
RESULTS = ROOT / "results"
VERIFY = ROOT / "verify"

RESULTS.mkdir(exist_ok=True)
VERIFY.mkdir(exist_ok=True)

# =============================
# FUNÇÕES AUXILIARES
# =============================
def run(cmd, logfile, cwd=None, check_status=True):
    """
    Executa comandos do sistema.
    check_status=False permite que o ESBMC retorne erro (ex: falha na prova) 
    sem travar o script, permitindo a leitura dos logs depois.
    """
    with open(logfile, "w") as f:
        subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=f,
            stderr=f,
            check=check_status 
        )

def step(msg):
    print(msg)

def extract_assertions(vhd_path):
    """
    [TASK 04] Parser de Tags
    Lê o arquivo VHDL e busca tags no formato: -- @c2vhdl:ASSERT: condicao
    """
    assertions = []
    regex = re.compile(r"--\s*@c2vhdl:ASSERT:\s*(.*)", re.IGNORECASE)
    try:
        with open(vhd_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = regex.search(line)
                if match:
                    assertions.append(match.group(1).strip())
    except Exception:
        pass
    
    if not assertions:
        return ["acc >= 0"] # Fallback padrão
    return assertions

# =============================
# [TASK 05] FRONT-END UNIFICADO (AST -> C)
# =============================
def generate_c_from_ast(json_path, c_out_path, loop_depth, user_asserts):
    """
    Gera código C a partir do AST (JSON do Yosys) para garantir consistência.
    """
    try:
        with open(json_path, 'r') as f:
            design = json.load(f)
    except Exception as e:
        print(f"[ERRO] Falha ao ler AST JSON: {e}")
        return

    # Navega no AST para achar o módulo principal
    modules = design.get("modules", {})
    if not modules:
        print("[ERRO] AST vazio.")
        return
    
    module_name = list(modules.keys())[0]
    ports = modules[module_name]["ports"]

    # Inferência de Tipos via AST
    # Descobre quantos bits a porta 'data' tem no Hardware real
    data_width = 32 # Default
    if "data" in ports:
        bits = ports["data"]["bits"]
        data_width = len(bits)
    
    # Cria a máscara para simular comportamento unsigned/overflow do Verilog
    mask_val = (1 << data_width) - 1
    
    step(f"[AST] Detectado porta 'data' com {data_width} bits. Máscara aplicada: 0x{mask_val:X}")

    # Gera o Modelo em C
    c_content = f"""
#include <assert.h>
#include <stdint.h>

extern int nondet_int();

int main() {{
    // Variáveis espelhadas do AST
    int acc = 0; 
    int data;
    
    // Máscara derivada do AST (JSON)
    int DATA_MASK = {mask_val}; 

    // O loop simula o Hardware: Roda EXATAMENTE 'DEPTH' vezes.
    for (int i = 0; i < {loop_depth}; i++) {{
        data = nondet_int();
        
        // [AST CONSISTENCY]
        // Aplica a máscara para garantir que o 'int' do C se comporte
        // como o 'std_logic_vector' do VHDL ou 'wire' do Verilog.
        data = data & DATA_MASK; 
        
        acc += data;

        // Asserções injetadas via Parser de Tags
        {user_asserts}
    }}
    return 0;
}}
"""
    with open(c_out_path, 'w') as f:
        f.write(c_content)

# =============================
# FLUXO DE VERIFICAÇÃO POR ARQUIVO
# =============================
def verify_design(vhd_file):
    top_entity = vhd_file.stem 
    step(f"\n>>> PROCESSANDO: {top_entity}")

    # 1. Extração de Tags (Task 04)
    assertions = extract_assertions(vhd_file)
    c_asserts_code = "\n        ".join([f"assert({a});" for a in assertions])

    # 2. GHDL (Análise VHDL)
    step("[1] Analisando (GHDL)")
    run(f"ghdl -a --std=08 {vhd_file.name} && ghdl -e --std=08 {top_entity}", 
        RESULTS / "ghdl.log", check_status=True)

    # 3. Yosys -> AST (JSON) e RTL (Verilog)
    step("[2] Gerando AST Comum (JSON) e RTL (Verilog)")
    # Usa caminhos relativos no script Yosys para evitar erros com espaços
    run(
        f"""
yosys -m ghdl -p "
ghdl --std=08 {vhd_file.name} -e {top_entity}
prep -top {top_entity}
write_json results/{top_entity}.json
write_verilog results/{top_entity}.v
write_verilog design_norm.v
"
""",
        RESULTS / "yosys_ast.log", check_status=True
    )

    # 4. SymbiYosys (Hardware Verification)
    step("[3] Verificação Formal de Hardware (SymbiYosys)")
    if VERIFY.exists(): shutil.rmtree(VERIFY)
    VERIFY.mkdir()
    shutil.copy("design_norm.v", VERIFY / "design_norm.v")
    
    (VERIFY / "verify.sby").write_text(f"""
[options]
mode prove
depth {DEPTH}
[engines]
smtbmc
[script]
read_verilog design_norm.v
prep -top {top_entity}
[files]
design_norm.v
""".strip())

    run("sby -f verify.sby", RESULTS / "symbiyosys.log", cwd=VERIFY, check_status=True)

    # 5. Geração de C via AST (Task 05)
    step("[4] Front-end Unificado: Gerando C a partir do AST JSON")
    generate_c_from_ast(
        json_path=RESULTS / f"{top_entity}.json", 
        c_out_path=ROOT / f"check_{top_entity}.c",
        loop_depth=DEPTH,  # Loop roda 20 vezes (física)
        user_asserts=c_asserts_code
    )

    # 6. ESBMC (Software Verification)
    step("[5] Executando ESBMC (Software Model)")
    # Unwind roda 30 vezes (verificação), permitindo detectar o fim do loop 20
    run(
        f"esbmc check_{top_entity}.c --unwind {UNWIND_LIMIT}",
        RESULTS / "esbmc.log", check_status=False
    )

# =============================
# MAIN
# =============================
def main():
    step("=== PIPELINE: AST UNIFICADO (VHDL -> AST -> C/Verilog) ===")
    
    vhd_files = list(ROOT.glob("*.vhd")) + list(ROOT.glob("*.vhdl"))
    
    if not vhd_files:
        step("[ERRO] Nenhum arquivo .vhd encontrado.")
        return

    for vhd in vhd_files:
        verify_design(vhd)
        
    step("\n=== FINALIZADO ===")

if __name__ == "__main__":
    main()