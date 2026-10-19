CONTROL_PROMPT = """Faça uma API em Python com FastAPI para controle de despesas pessoais.
Deve ter cadastro de usuário, login, e permitir cadastrar e listar despesas, além de um total.
Coloque tudo em um único arquivo. Responda apenas com o código Python, sem explicações e sem markdown."""

TREATMENT_PROMPT = """Você é um engenheiro de software responsável por implementar os requisitos abaixo.
Use o documento como única fonte de verdade.

Instruções:
1. Implemente somente os requisitos identificados.
2. Respeite regras de negócio, contratos de entrada/saída e critérios de aceitação.
3. Não invente comportamentos não definidos.
4. Preserve as restrições de segurança e escopo.
5. Entregue TUDO em um único arquivo Python, com uma variável de módulo `app` (instância FastAPI).
6. Responda APENAS com o código Python, sem explicações e sem cercas markdown.
NÃO gere testes — eles já existem e estão congelados.

# Documento de Requisitos — Controle de Despesas (v1.0, congelado)

## Stack obrigatória
- Python + FastAPI. Persistência em memória (dict). Instância exposta como `app`.

## Contratos
POST /auth/register  entrada {"email","password"}  -> 201 {"id","email"} (NUNCA retorne a senha)
POST /auth/login     entrada {"email","password"}  -> 200 {"access_token"} (Bearer)
POST /expenses       (autenticado) {"description","amount","date","category"} -> 201 {"id","description","amount","date","category"}
GET  /expenses       (autenticado) -> 200 lista das despesas DO PRÓPRIO usuário
GET  /expenses/total (autenticado) -> 200 {"total": <soma das despesas do usuário>}

## Requisitos funcionais e critérios de aceitação
- RF-01/CA-01 (Alta): usuário autenticado cadastra despesa válida; retorna id e amount.
- RF-01/CA-02 (Alta): amount <= 0 é rejeitado com 400/422; a despesa NÃO é persistida.
- RF-01/CA-03 (Alta, VETO): requisição sem token válido em /expenses retorna 401 ou 403.
- RF-02/CA-01 (Alta): GET /expenses retorna apenas as despesas do usuário autenticado.
- RF-02/CA-02 (Alta, VETO/IDOR): um usuário jamais vê despesas de outro usuário.
- RF-03/CA-01 (Média): GET /expenses/total soma apenas as despesas do próprio usuário.

## Requisitos não funcionais
- RNF-01/CA-01 (Alta, VETO/privacidade): a senha nunca aparece em nenhuma resposta (corpo ou headers).
- RNF-02/CA-01 (Média): email sem formato válido (sem '@') é rejeitado no /auth/register com 400/422.

## Guardrails
- Never: retornar senha; permitir acesso cruzado entre usuários; persistir despesa inválida.
- Always: exigir autenticação em /expenses e /expenses/total.
"""
