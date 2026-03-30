---
name: ai-fine-tuning-expert
description: Calibração de pesos, LoRA, curadoria de datasets e treinamento de LLMs customizados.
---

# 🧠 Fine-Tuning

## 📋 Visão Geral
Este skill mergulha nas profundezas do treinamento e sintonia fina (Fine-Tuning) de modelos de fundação de linguagem (LLMs). Ele qualifica a IA para orientar a adaptação de pesos em modelos (Open Source como LLaMA, Mistral, Qwen ou comerciais via API) para domínios ultra-específicos.

## 🎯 Direcionamentos Principais
1. **Curadoria de Datasets**: Estruturação, limpeza e formatação de dados em JSONL com prompts/completions ou formatos de conversa adequados para treinamento de alta qualidade (Garbage in, Garbage out).
2. **Estratégias de Treinamento (PEFT/LoRA/QLoRA)**: Como aplicar Parameter-Efficient Fine-Tuning para reduzir custos e necessidades de VRAM de GPUs no treinamento.
3. **Alinhamento e DPO/RLHF**: Técnicas de otimização por preferências directas para adequar o modelo ao tom de voz perfeito ou evitar alucinações de maneira sistêmica.
4. **Avaliação e Benchmarks**: Medir a perplexidade, perda, overfitting e usar frameworks (EleutherAI LM Eval, Ragas) para garantir que o modelo novo é superior ao base.

## 💡 Aplicações Práticas
- Criação de um pipeline para afinar um LLM focado em vocabulário médico, jurídico ou na identidade de uma marca específica (como a personalidade da Ananda).
- Preparação eficiente de dados e recomendações de hiperparâmetros (Learning Rate, Epochs, Batch Size).

## 🛠️ Como Utilizar
Use quando o desafio não puder ser resolvido através de Prompt Engineering ou RAG, e sim quando o modelo em si precisa "aprender" organicamente o estilo, sintaxe ou raciocínio particular dos dados do usuário.
