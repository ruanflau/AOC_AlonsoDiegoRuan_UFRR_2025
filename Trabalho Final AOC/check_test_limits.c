
#include <assert.h>
#include <stdint.h>

extern int nondet_int();

int main() {
    // Variáveis espelhadas do AST
    int acc = 0; 
    int data;
    
    // Máscara derivada do AST (JSON)
    int DATA_MASK = 255; 

    // O loop simula o Hardware: Roda EXATAMENTE 'DEPTH' vezes.
    for (int i = 0; i < 20; i++) {
        data = nondet_int();
        
        // [AST CONSISTENCY]
        // Aplica a máscara para garantir que o 'int' do C se comporte
        // como o 'std_logic_vector' do VHDL ou 'wire' do Verilog.
        data = data & DATA_MASK; 
        
        acc += data;

        // Asserções injetadas via Parser de Tags
        assert(acc >= 0);
    }
    return 0;
}
