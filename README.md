# AOC_AlonsoDiegoRuan_UFRR_2025

**Universidade Federal de Roraima (UFRR)**
**Disciplina:** Arquitetura e Organização de Computadores (2025.2)
**Autores:**

---

## 📌 Sobre o Projeto
Este repositório contém os artefatos da **Atividade Final (Task 04): Automatizando e ampliando a metodologia de verificação (VHDL → C → ESBMC)**.

O projeto implementa um **pipeline de verificação formal automatizado** que unifica a validação de hardware (RTL) e software (Modelos C). O principal diferencial é o uso de um *Front-end* baseado em AST (Árvore de Sintaxe Abstrata), extraído via Yosys, que garante consistência matemática entre os tipos do VHDL (ex: vetores de 8 bits) e os tipos do C (máscaras de bits dinâmicas), eliminando falsos positivos na verificação.

---

## ⚙️ Guia de Instalação (Passo a Passo)

Este projeto foi desenvolvido para rodar em ambiente **Linux** (Nativo ou WSL no Windows). Siga os comandos abaixo para configurar todas as ferramentas necessárias do zero.

### 1. Atualizar sistema e dependências básicas
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git wget curl unzip python3 python3-pip clang
