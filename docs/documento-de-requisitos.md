# Documento de Requisitos

**Grupo:** Fornecimento e Produtos
**Sistema:** Portal B2B Distribuído (disciplina de Sistemas Distribuídos)
**Integrantes:** Daniel Carvalho Coutinho, Davi Coelho de Alvarenga, Gabriel Vicentte dos Santos Ferreira, Rafael de Castro Noleto
**Versão:** 0.3 (rascunho para revisão interna)
**Data:** 09/10/2026

> Itens com status **Pendente** ou **Proposto** ainda podem mudar. O time de QA deve testar apenas itens com status **Confirmado** até a versão 1.0 deste documento.

---

## 1. Introdução

### 1.1 Propósito

Este documento descreve os requisitos dos serviços sob responsabilidade do grupo Fornecimento e Produtos. Ele é a referência do time de QA para planejar e executar testes. Cada requisito indica a fonte de onde veio e o seu status, para que fique claro o que foi exigido pelo professor, o que vem do diagrama de arquitetura e o que é decisão do grupo.

### 1.2 Escopo

Conforme o diagrama "Arquitetura do Portal B2B Distribuído" fornecido pelo professor (fonte F2), o grupo é responsável por dois microsserviços:

| Serviço | Bloco no diagrama | Responsabilidades | Banco |
|---|---|---|---|
| Produtos | 2 | Catálogo de produtos, categoria, unidade, tipo de transporte | db produtos |
| Fornecimentos | 3 | Relação entre fornecedor e produto, preço, quantidade, origem, estoque | db fornecimentos |

Os dois serviços se comunicam com os demais módulos por eventos no Kafka.

Na divisão das equipes, o professor atribuiu ao grupo produtos, fornecimentos, categoria de produtos e todo o controle de estoque: "A parte de estoque é toda de vocês e fornecimentos também" (F7, 19:01 a 19:59).

A lista de responsabilidades do grupo (F1) diz "conversar com o time de mercado e negociação, logística frete e transportadoras". O texto fala em conversar com outros times, e o diagrama (F2) mostra esses módulos como serviços próprios (blocos 5, 6, 8 e 9). O papel do grupo em relação a eles é de **integração** por eventos, e não de implementação.

### 1.3 Fora do escopo

Os itens abaixo pertencem a outros grupos. Este documento descreve apenas a interface que esperamos deles (seção 2.2).

- Cadastro de empresas, perfis de acesso, emissão e validação de tokens (grupo de autenticação, F7, 19:09 a 19:22)
- Definição dos padrões visuais e de usabilidade (equipe de UX, F7, 9:17 a 9:40). Quem implementa as telas do nosso módulo está em aberto (P-22)
- Demanda, Mercado (matching), Negociação/Leilão e Pedidos. A divisão da responsabilidade por pedidos entre os grupos ainda não foi fechada (P-23)
- Solicitação, cotação e acompanhamento de frete, cadastro de transportadoras (Logística/Frete e Transportadoras)
- Infraestrutura de plataforma: cluster Kafka, Schema Registry, API Gateway, monitoramento e logs centralizados (grupo de infra)

### 1.4 Fontes

| ID | Fonte |
|---|---|
| F1 | Lista de responsabilidades do grupo (arquivo "FORNECIMENTO E PRODUTOS - MEMBROS"): gestão de estoque, conversa com os times de mercado e negociação, logística, frete e transportadoras, fornecimento e produtos, estoque, tipo de transporte, cadastro de produtos, categoria de produto, quantidade e origem de produtos, preço, relação entre fornecedor e produto, criação de relação de fornecimento pelos fornecedores |
| F2 | Diagrama "Arquitetura do Portal B2B Distribuído", elaborado pelo professor |
| F3 | Requisitos gerais do professor: autenticação obrigatória e token temporário |
| F4 | Decisões do grupo, justificadas no Relatório Técnico |
| F5 | Orientações de integração via Kafka (tecnologia definida pela turma): o módulo produz e consome tópicos para atualizar o estoque, publica e consome eventos de criação, alteração e exclusão de produtos e eventos de pedido de fornecimento entre fornecedor e grupo |
| F6 | Transcrição automática do áudio da aula 1, em que o professor explica o fluxo do negócio (perfis, demanda, leilão, reserva de estoque, frete) |
| F7 | Transcrição automática do áudio da aula 2, em que o professor divide as equipes e define responsabilidades, ferramentas obrigatórias e padrões de interface |

As transcrições F6 e F7 têm muitos erros de reconhecimento. Só trechos sem ambiguidade são usados como fonte de requisito confirmado, sempre com a marcação de tempo do áudio (ex.: F7, 19:35). Trechos duvidosos aparecem apenas nas pendências.

### 1.5 Convenções

**Identificadores:** RF (requisito funcional), RNF (requisito não funcional), RD (requisito de dados), RN (regra de negócio), UC (caso de uso), CA (critério de aceitação), P (pendência).

**Origem:** identificador da fonte (F1 a F7, seção 1.4). F4 indica decisão do grupo.

**Status:**

| Status | Significado |
|---|---|
| Confirmado | Definido por fonte do professor (F1, F2, F3, F5, F6 ou F7). Pode ser testado |
| Proposto | Decisão do grupo. Pode mudar até a versão 1.0 |
| Pendente | Depende de resposta externa. A pendência correspondente é indicada |

### 1.6 Glossário

| Termo | Definição |
|---|---|
| Produto | Item do catálogo, com categoria, unidade e tipo de transporte (F2, bloco 2) |
| Categoria | Classificação do produto. Forma de cadastro em aberto (P-10) |
| Unidade | Unidade de medida em que o produto é negociado. Valores em aberto (P-06) |
| Tipo de transporte | Atributo do produto que indica como ele precisa ser transportado (F2, bloco 2). Exemplo citado pelo professor: câmara frigorífica (F7, 25:43). Logística/Frete usa esse atributo para escolher as transportadoras que podem levar o produto (F6, 10:33; F7, 24:56 a 25:21). Valores em aberto (P-06) |
| Perfil | Papel de uma empresa no portal: fornecedor, comprador ou transportadora. Uma empresa pode ter os três perfis ao mesmo tempo, e o que o usuário acessa depende do perfil (F6) |
| Fornecedor | Empresa (CNPJ) com perfil de fornecedor, cadastrada no módulo Usuários/Acesso (F2, bloco 1) |
| Fornecimento | Registro em que um fornecedor oferece um produto, com preço, quantidade e origem (F2, bloco 3). É o mesmo que "relação de fornecimento": o fornecedor coloca o produto "na prateleira" para os compradores visualizarem (F7, 29:16 a 29:34). Corresponde ao passo 1 do fluxo do diagrama: "Fornecedor publica fornecimento" |
| Demanda | Necessidade de compra registrada por um comprador, por exemplo "15 mil litros de leite por mês durante um ano". Não significa compra efetiva (F7, 2:03 a 2:28 e 26:51 a 27:11). Responsabilidade de outro grupo |
| Estoque | Quantidade de um produto ofertada por um fornecedor. Dividida em quantidade disponível e quantidade reservada (F6). A granularidade por fornecimento é uma interpretação do grupo (P-03) |
| Quantidade disponível | Parte do estoque que pode ser negociada e que fica visível para quem quer comprar (F6) |
| Quantidade reservada | Parte do estoque bloqueada por um pedido em andamento. Volta a ficar disponível se o pedido for cancelado e sai do estoque se a venda for concluída (F6) |
| Origem | Significado em aberto (P-05). F1 a associa ao produto ("quantidade e origem de produtos") e F2 a coloca no bloco Fornecimentos |
| Evento | Mensagem publicada no Kafka que informa algo que já aconteceu |
| Token | Credencial temporária de acesso. O diagrama cita JWT/OAuth2 (F2, infraestrutura) |

---

## 2. Contexto

### 2.1 Atores

| Ator | Interação com os nossos serviços | Status |
|---|---|---|
| Fornecedor | Cadastra produtos (F7, 1:46) e publica fornecimentos com preço (F2, fluxo passo 1; F6; F7, 29:16) | Confirmado |
| Comprador | Cadastra produtos, porque precisa deles para registrar demandas (F7, 1:39 a 2:03). Consulta os fornecimentos e o estoque disponível (F6, 9:26; F7, 29:29) | Confirmado |
| Administrador | Aparece como cliente no diagrama. Permissões nos nossos serviços não definidas | Pendente (P-07) |
| Serviços de outros grupos | Publicam e consomem eventos via Kafka | Ver seção 9 |

Uma mesma empresa pode ter os perfis de fornecedor, comprador e transportadora ao mesmo tempo, e o acesso de cada usuário depende do perfil (F6, 1:34 a 1:50). Os nossos serviços autorizam cada operação pelo perfil, não só pela autenticação.

### 2.2 Interfaces esperadas de outros módulos

| Módulo | O que esperamos dele | Status |
|---|---|---|
| Usuários/Acesso (grupo de autenticação) | Cadastro de empresas e dos três perfis (F7, 19:09 a 19:22). Token com identificação da empresa e do perfil ativo. Evento `empresa_cadastrada` com identificador e perfis da empresa. O professor deixou a forma de autenticação para os alunos definirem (F6, 1:08) | Pendente (P-04, P-12) |
| API Gateway | Autenticação das requisições e roteamento para os nossos serviços. Definição de como a identidade do usuário chega ao serviço | Pendente (P-04) |
| Pedidos | Eventos `pedido_criado` e `pedido_atualizado` (F2) que indiquem criação, cancelamento e conclusão da venda, com identificador do pedido, fornecimento e quantidade. O pedido é criado ao entrar em leilão ou em negociação direta, e nesse momento o estoque precisa ser bloqueado (F6, 8:19; F7, 21:03). Segundo o professor, quem cuidar de pedidos já foi orientado sobre a reserva (F6, 9:07 a 9:14) | Pendente (P-02, P-23) |
| Mercado | Consumo de `fornecimento_criado` e `estoque_atualizado` para o cálculo de oferta e demanda (F2, fluxo passo 4) | Pendente (P-19) |
| Logística/Frete | Consumo do tipo de transporte do produto. Quando a venda ocorre, só as transportadoras que podem transportar aquele tipo de produto são notificadas (F6, 10:08 a 10:33) | Confirmado (contrato: P-19) |
| Infra | Cluster Kafka disponível, criação dos eventos e definição do stack de ferramentas (F7, 21:25 a 21:45). A transcrição registra "carro" onde o contexto indica Kafka. Definição sobre o uso do Schema Registry | Pendente (P-08, P-17) |
| Banco de dados | O professor pediu que o grupo de banco participe das conversas (F7, 22:44 a 22:47). Papel desse grupo em relação aos bancos próprios de cada serviço (F2) a definir | Pendente (P-24) |
| UX | Padrões visuais e de usabilidade e garantia de qualidade das telas (F7, 9:17 a 9:40) | Pendente (P-22) |

### 2.3 Premissas

1. A autenticação usa tokens JWT/OAuth2, como indicado na camada de segurança do diagrama (F2). O mecanismo exato de validação é definido pelo grupo de autenticação (P-04). Na aula foi discutida uma proposta em que cada empresa é um tenant e cada usuário tem papéis por perfil dentro dela (F6, 2:43 a 3:52). A proposta não foi definida como obrigatória.
2. Cada serviço tem banco de dados próprio e nenhum outro serviço o acessa diretamente (F2, legenda "Banco de dados próprio de cada serviço").
3. Toda comunicação entre módulos acontece por eventos Kafka. Chamadas REST ocorrem apenas entre Frontend, API Gateway e serviços (F2, legenda).

---

## 3. Requisitos funcionais

### 3.1 Serviço de Produtos

| ID | Requisito | Origem | Status |
|---|---|---|---|
| RF-01 | O sistema deve permitir que empresas com perfil de fornecedor ou de comprador cadastrem produto com categoria, unidade e tipo de transporte | F1, F2, F7 | Confirmado (atributos completos: P-06) |
| RF-02 | O sistema deve permitir consultar produtos, em lista e por identificador | F4 | Proposto |
| RF-03 | O sistema deve permitir alterar um produto cadastrado | F5 | Confirmado |
| RF-04 | O sistema deve permitir excluir um produto | F5 | Confirmado (regra de exclusão: P-09) |
| RF-05 | O sistema deve permitir gerenciar as categorias de produto | F1, F2 | Pendente (P-10) |
| RF-06 | Ao cadastrar um produto, o serviço deve publicar o evento `produto_cadastrado` | F2, F5 | Confirmado |
| RF-07 | Ao alterar um produto, o serviço deve publicar o evento `produto_atualizado` | F5 | Confirmado (nome do evento: Proposto) |
| RF-08 | Ao excluir um produto, o serviço deve publicar o evento `produto_excluido` | F5 | Confirmado (nome do evento: Proposto) |

### 3.2 Serviço de Fornecimentos

| ID | Requisito | Origem | Status |
|---|---|---|---|
| RF-09 | O fornecedor deve poder criar um fornecimento (relação de fornecimento) informando produto, preço, quantidade e origem | F1, F2 | Confirmado |
| RF-10 | O sistema deve permitir que compradores consultem os fornecimentos, em lista e por identificador, incluindo a quantidade disponível | F6, F7 | Confirmado |
| RF-11 | O sistema deve permitir alterar ou encerrar um fornecimento | F4 | Pendente (P-11) |
| RF-12 | Ao criar um fornecimento, o serviço deve publicar o evento `fornecimento_criado` | F2 | Confirmado |
| RF-13 | O serviço deve manter, para cada fornecimento, a quantidade disponível e a quantidade reservada | F1, F2, F6 | Confirmado (granularidade por fornecimento: P-03) |
| RF-14 | Ao consumir o evento de criação de pedido, o serviço deve reservar a quantidade do pedido: subtrair da quantidade disponível e somar à quantidade reservada | F2, F5, F6 | Confirmado (contrato do evento: P-02) |
| RF-15 | Sempre que o estoque mudar, o serviço deve publicar o evento `estoque_atualizado` | F2, F5 | Confirmado |
| RF-19 | Ao consumir o evento de cancelamento de pedido, o serviço deve devolver a quantidade reservada à quantidade disponível | F6 | Confirmado (contrato do evento: P-02) |
| RF-20 | Ao consumir o evento de conclusão da venda, o serviço deve dar baixa definitiva na quantidade reservada | F6 | Confirmado (contrato do evento: P-02) |
| RF-21 | Os eventos de produto devem conter o tipo de transporte, para que Logística/Frete identifique as transportadoras que podem transportar o produto | F6, F4 | Proposto |

**Justificativa do RF-13, RF-14, RF-19 e RF-20:** na aula 2, o professor diz ao grupo que, "a partir do momento de entrar no leilão ou fizer uma negociação, tem que fechar um pedido, tem que bloquear" o estoque (F7, 21:03). Na aula 1 (F6, 8:13 a 9:42), ele descreve que, ao criar um pedido, o produto sai do estoque e fica bloqueado no pedido, enquanto o restante continua visível para quem quer comprar. Se o pedido for cancelado, a quantidade volta ao estoque. Se a negociação terminar em venda, a operação é finalizada. Ele chama a operação de transação.
| RF-16 | O serviço de Fornecimentos deve consumir os eventos de produto (criação, alteração e exclusão) para manter uma referência local dos produtos válidos | F5, F4 | Proposto |
| RF-17 | O serviço de Fornecimentos deve consumir o evento `empresa_cadastrada` para reconhecer as empresas com perfil de fornecedor | F2, F4 | Pendente (P-12) |
| RF-18 | O sistema deve publicar e consumir eventos de pedido de fornecimento entre fornecedor e grupo | F5 | Pendente (P-13) |

**Justificativa do RF-16:** as orientações de integração (F5) exigem que o módulo consuma eventos de produto. Com Produtos e Fornecimentos em serviços separados e com bancos separados (F2), o serviço de Fornecimentos precisa saber quais produtos existem sem acessar o banco de Produtos. Consumir os eventos de produto atende às duas exigências.

---

## 4. Requisitos não funcionais

| ID | Requisito | Categoria | Origem | Status |
|---|---|---|---|---|
| RNF-01 | Todos os endpoints dos dois serviços exigem autenticação. Requisição sem token é recusada | Segurança | F3 | Confirmado |
| RNF-02 | Requisição com token expirado ou inválido é recusada com HTTP 401, e o cliente precisa se autenticar novamente | Segurança | F3 | Confirmado (formato da resposta: P-04) |
| RNF-03 | Requisição autenticada sem o perfil necessário é recusada com HTTP 403 | Segurança | F6, F4 | Confirmado (permissões por operação: P-07) |
| RNF-04 | A comunicação entre módulos é feita por eventos Kafka | Interoperabilidade | F2, F5 | Confirmado |
| RNF-05 | Cada serviço tem banco próprio, inacessível diretamente por outros serviços | Manutenibilidade | F2 | Confirmado |
| RNF-06 | O processamento de eventos consumidos é idempotente: o mesmo evento recebido mais de uma vez produz o mesmo resultado que uma única vez | Confiabilidade | F4 | Proposto |
| RNF-07 | Eventos de uma mesma entidade são publicados com o identificador da entidade como chave da mensagem | Confiabilidade | F4 | Proposto |
| RNF-08 | Os produtores Kafka são configurados com `acks=all` e `enable.idempotence=true` | Confiabilidade | F4 | Proposto |
| RNF-09 | Nenhum evento publicado contém token de acesso | Segurança | F4 | Proposto |
| RNF-10 | Um evento que falha no processamento depois de esgotadas as tentativas é enviado a um tópico de erro, sem bloquear o consumo dos demais | Confiabilidade | F4 | Proposto |
| RNF-11 | Os serviços registram logs com identificador de correlação por requisição e por evento | Manutenibilidade | F4 | Proposto (integração com ELK/Loki: P-14) |
| RNF-12 | Os serviços são executáveis em contêiner Docker | Portabilidade | F2, F7 | Confirmado ("vocês precisam trabalhar com docker", F7, 21:48 a 21:58) |
| RNF-13 | Os esquemas dos eventos são registrados no Schema Registry | Interoperabilidade | F2 | Pendente (P-08) |
| RNF-14 | A reserva de estoque é atômica: reservas simultâneas para o mesmo fornecimento não podem, somadas, ultrapassar a quantidade disponível | Confiabilidade | F6, F4 | Proposto (P-16) |
| RNF-15 | As telas seguem o padrão visual definido pela equipe de UX: visual limpo, verde e branco, linhas finas nas bordas dos campos | Usabilidade | F7 (6:44 a 7:28, 9:06) | Confirmado (aplicação ao nosso módulo: P-22) |
| RNF-16 | As telas têm modo escuro, em cinza escuro e preto, com destaques em verde mais escuro | Usabilidade | F7 (7:50 a 8:59) | Confirmado, obrigatório (aplicação ao nosso módulo: P-22) |
| RNF-17 | As telas atendem a requisitos de acessibilidade | Usabilidade | F7 (7:58 a 8:10) | Confirmado (critérios: P-22) |
| RNF-18 | As telas são responsivas | Usabilidade | F7 (10:31 a 10:36) | Confirmado (aplicação ao nosso módulo: P-22) |

**Justificativas técnicas:**

- **RNF-06:** em caso de falha do consumidor entre o processamento da mensagem e o registro do offset, o Kafka entrega a mensagem novamente (semântica "at least once", documentação do Apache Kafka, seção *Message Delivery Semantics*). Sem idempotência, uma mesma baixa de estoque poderia ser aplicada duas vezes.
- **RNF-07:** o Kafka garante ordem apenas dentro de uma partição, e mensagens com a mesma chave vão para a mesma partição (documentação do Apache Kafka, seção *Topics and Partitions*). Usar o identificador da entidade como chave preserva a ordem dos eventos de um mesmo produto ou fornecimento.
- **RNF-08:** são os padrões do produtor desde o Kafka 3.0 (KIP-679). Um defeito impediu que fossem aplicados nas versões 3.0.0 e 3.1.0, corrigido em 3.0.1, 3.1.1 e 3.2.0 (notas de atualização do Apache Kafka). A configuração explícita elimina a dependência da versão usada.
- **RNF-14:** o professor trata a reserva como transação (F6, 9:18) e levanta o caso de 30 compradores querendo o mesmo produto na mesma hora (F6, 14:40). Se duas reservas lerem o mesmo saldo e gravarem em seguida, as duas podem ser aceitas e o estoque fica negativo. A verificação do saldo e a reserva precisam acontecer na mesma operação atômica.
- **RNF-09:** o token expira, e o evento permanece armazenado no Kafka durante o período de retenção. Gravar o token no evento expõe uma credencial. O evento leva apenas o identificador de quem executou a ação.

**Desempenho:** nenhuma fonte define metas de desempenho. Nenhum requisito de desempenho é incluído até essa definição (P-18), porque um requisito sem meta mensurável não pode ser verificado pelo QA.

---

## 5. Requisitos de dados

| ID | Entidade | Atributos | Origem | Status |
|---|---|---|---|---|
| RD-01 | Produto | Identificador, categoria, unidade, tipo de transporte | F1, F2 | Confirmado |
| RD-02 | Produto | Nome e descrição | F4 | Proposto (P-06) |
| RD-03 | Fornecimento | Identificador, fornecedor (empresa), produto, preço, quantidade, origem | F1, F2 | Confirmado (posição de origem: P-05) |
| RD-04 | Fornecimento | Formato do preço (moeda e precisão) | F4 | Pendente (P-15) |
| RD-05 | Categoria | Estrutura (lista fixa, cadastro, hierarquia) | F1 | Pendente (P-10) |
| RD-06 | Estoque do fornecimento | Quantidade disponível e quantidade reservada | F6 | Confirmado |

---

## 6. Regras de negócio

### 6.1 Regras definidas

| ID | Regra | Origem | Status |
|---|---|---|---|
| RN-01 | Um fornecimento relaciona um fornecedor e um produto | F1, F2 | Confirmado |
| RN-02 | Apenas empresas com perfil de fornecedor podem criar fornecimentos | F1, F2, F6 | Confirmado |
| RN-03 | Um fornecimento só pode referenciar um produto existente no catálogo | F4 | Proposto |
| RN-04 | Uma empresa pode ter os perfis de fornecedor, comprador e transportadora ao mesmo tempo | F6 | Confirmado |
| RN-05 | Um mesmo produto pode ser ofertado por vários fornecedores | F6 | Confirmado |
| RN-06 | A quantidade reservada por um pedido volta a ficar disponível se o pedido for cancelado | F6 | Confirmado |
| RN-07 | A quantidade reservada por um pedido sai do estoque quando a venda é concluída | F6 | Confirmado |
| RN-08 | Empresas com perfil de fornecedor ou de comprador podem cadastrar produtos | F7 (1:17 a 1:49) | Confirmado |
| RN-09 | Todo produto tem um tipo de transporte definido | F7 (25:21: "tem que ter um tipo de transporte disponível para ter produtos") | Proposto (P-06) |

### 6.2 Regras em aberto

As perguntas abaixo não têm resposta nas fontes. Não devem ser testadas até a definição.

| Pendência | Pergunta |
|---|---|
| P-09 | A exclusão de produto é lógica ou física? O que acontece com os fornecimentos ativos do produto excluído? |
| P-16 | O estoque pode ficar negativo? O que acontece quando chega um pedido com quantidade maior que a disponível? |
| P-20 | O mesmo fornecedor pode ter mais de um fornecimento do mesmo produto? |
| P-21 | Preço e quantidade podem ser zero? |

---

## 7. Casos de uso

### UC-01 Cadastrar produto

- **Ator:** empresa com perfil de fornecedor ou de comprador (RN-08)
- **Pré-condição:** ator autenticado com token válido
- **Fluxo principal:**
  1. O ator envia os dados do produto.
  2. O serviço valida os dados obrigatórios.
  3. O serviço grava o produto.
  4. O serviço publica `produto_cadastrado`.
  5. O serviço retorna HTTP 201 com o identificador do produto.
- **Fluxos alternativos:**
  - A1. Token ausente, expirado ou inválido: o serviço retorna HTTP 401. Nada é gravado nem publicado.
  - A2. Dados obrigatórios ausentes ou inválidos: o serviço retorna HTTP 400 indicando os campos com erro. Nada é gravado nem publicado.
  - A3. Perfil ativo sem permissão de cadastro (por exemplo, apenas transportadora): o serviço retorna HTTP 403. Nada é gravado nem publicado.
- **Requisitos relacionados:** RF-01, RF-06, RN-08, RNF-01, RNF-02, RNF-03

### UC-02 Publicar fornecimento

- **Ator:** Fornecedor
- **Pré-condição:** fornecedor autenticado com token válido
- **Fluxo principal** (F2, fluxo passo 1):
  1. O fornecedor informa produto, preço, quantidade e origem.
  2. O serviço valida os dados e verifica se o produto existe (RN-03).
  3. O serviço grava o fornecimento.
  4. O serviço publica `fornecimento_criado`.
  5. O serviço retorna HTTP 201 com o identificador do fornecimento.
- **Fluxos alternativos:**
  - A1. Token ausente, expirado ou inválido: HTTP 401. Nada é gravado nem publicado.
  - A2. Empresa sem perfil de fornecedor: HTTP 403 (RN-02, P-07).
  - A3. Produto inexistente: HTTP 422. Nada é gravado nem publicado.
  - A4. Dados inválidos: HTTP 400 indicando os campos com erro.
- **Requisitos relacionados:** RF-09, RF-12, RN-01, RN-02, RN-03

### UC-03 Reservar, liberar e baixar estoque a partir de eventos de pedido

- **Ator:** serviço de Pedidos (P-02)
- **Pré-condição:** fornecimento existente
- **Fluxo principal (reserva):**
  1. O serviço de Fornecimentos consome o evento de criação de pedido.
  2. O serviço verifica se o identificador do evento já foi processado.
  3. Em uma única operação atômica, o serviço confere se há quantidade disponível suficiente, subtrai a quantidade do pedido da quantidade disponível e a soma à quantidade reservada (RNF-14).
  4. O serviço publica `estoque_atualizado`.
- **Fluxos alternativos:**
  - A1. Evento já processado: o serviço ignora o evento e não publica novo `estoque_atualizado` (RNF-06).
  - A2. Evento com formato inválido ou que falha após as tentativas: o evento vai para o tópico de erro (RNF-10).
  - A3. Quantidade do pedido maior que a disponível: comportamento em aberto (P-16).
  - A4. Pedido cancelado: o serviço devolve a quantidade reservada à quantidade disponível e publica `estoque_atualizado` (RF-19, RN-06).
  - A5. Venda concluída: o serviço retira a quantidade reservada do estoque e publica `estoque_atualizado` (RF-20, RN-07).
- **Requisitos relacionados:** RF-13, RF-14, RF-15, RF-19, RF-20, RNF-06, RNF-10, RNF-14

---

## 8. Critérios de aceitação

```gherkin
CA-01 (RNF-01)
Dado uma requisição sem token de acesso
Quando o cliente chama qualquer endpoint do serviço de Produtos ou de Fornecimentos
Então a resposta tem status 401
E nenhum dado é retornado

CA-02 (RNF-02)
Dado um token cuja data de expiração já passou
Quando o cliente chama qualquer endpoint do serviço de Produtos ou de Fornecimentos
Então a resposta tem status 401
E nenhum dado é retornado

CA-03 (RF-01, RF-06, RN-08)
Dado um usuário autenticado com perfil de fornecedor ou de comprador
Quando ele cadastra um produto com dados válidos
Então a resposta tem status 201 e contém o identificador do produto
E o evento produto_cadastrado é publicado com o identificador do produto como chave

CA-04 (RF-03, RF-07)
Dado um produto cadastrado
Quando um usuário autorizado altera o produto
Então o evento produto_atualizado é publicado com o identificador do produto como chave

CA-05 (RF-04, RF-08)
Dado um produto cadastrado
Quando um usuário autorizado exclui o produto
Então o evento produto_excluido é publicado com o identificador do produto como chave

CA-06 (RF-09, RF-12)
Dado um fornecedor autenticado
E um produto existente no catálogo
Quando o fornecedor cria um fornecimento com preço, quantidade e origem válidos
Então a resposta tem status 201
E o evento fornecimento_criado é publicado com o identificador do fornecimento como chave

CA-07 (RNF-06, UC-03)
Dado um evento de pedido já processado
Quando o mesmo evento é recebido novamente
Então as quantidades disponível e reservada do fornecimento não mudam
E nenhum novo evento estoque_atualizado é publicado

CA-08 (RNF-09)
Dado qualquer evento publicado pelos serviços de Produtos ou de Fornecimentos
Quando o conteúdo e os headers do evento são inspecionados
Então nenhum token de acesso está presente

CA-09 (UC-01 A1, UC-02 A1)
Dado uma requisição de cadastro com token expirado
Quando o serviço recusa a requisição
Então nenhum registro é gravado
E nenhum evento é publicado

CA-10 (RF-14, UC-03)
Dado um fornecimento com 100 unidades disponíveis e 0 reservadas
Quando o serviço consome a criação de um pedido de 30 unidades desse fornecimento
Então o fornecimento passa a ter 70 unidades disponíveis e 30 reservadas
E o evento estoque_atualizado é publicado

CA-11 (RF-19, RN-06, UC-03 A4)
Dado um fornecimento com 70 unidades disponíveis e 30 reservadas por um pedido
Quando o serviço consome o cancelamento desse pedido
Então o fornecimento passa a ter 100 unidades disponíveis e 0 reservadas
E o evento estoque_atualizado é publicado

CA-12 (RF-20, RN-07, UC-03 A5)
Dado um fornecimento com 70 unidades disponíveis e 30 reservadas por um pedido
Quando o serviço consome a conclusão da venda desse pedido
Então o fornecimento passa a ter 70 unidades disponíveis e 0 reservadas
E o evento estoque_atualizado é publicado

CA-13 (RNF-03, RN-02)
Dado um usuário autenticado cujo perfil ativo é apenas transportadora
Quando ele tenta criar um fornecimento
Então a resposta tem status 403
E nenhum registro é gravado
E nenhum evento é publicado

CA-14 (RF-10)
Dado um usuário autenticado com perfil de comprador
E fornecimentos cadastrados
Quando ele consulta os fornecimentos
Então a resposta tem status 200
E cada fornecimento retornado informa a quantidade disponível
```

Os valores numéricos dos CA-10 a CA-12 são exemplos para o teste, não regras de negócio. Os eventos de pedido citados dependem do contrato com o grupo responsável por pedidos (P-02).

O CA-02 poderá exigir o cabeçalho `WWW-Authenticate: Bearer error="invalid_token"` (RFC 6750, seção 3.1) se o grupo de autenticação confirmar o uso de Bearer token (P-04).

---

## 9. Eventos

| Evento | Serviço | Papel do serviço | Chave | Consumidores esperados | Status |
|---|---|---|---|---|---|
| `produto_cadastrado` | Produtos | Publica | Identificador do produto | Fornecimentos, Logística/Frete (tipo de transporte). Outros: P-19 | Confirmado (F2) |
| `produto_atualizado` | Produtos | Publica | Identificador do produto | Fornecimentos, Logística/Frete. Outros: P-19 | Proposto |
| `produto_excluido` | Produtos | Publica | Identificador do produto | Fornecimentos, Logística/Frete. Outros: P-19 | Proposto |
| `produto_*` | Fornecimentos | Consome | Identificador do produto | | Proposto (RF-16) |
| `fornecimento_criado` | Fornecimentos | Publica | Identificador do fornecimento | Mercado (P-19) | Confirmado (F2) |
| `estoque_atualizado` | Fornecimentos | Publica | Identificador do fornecimento | P-19 | Confirmado (F2) |
| `empresa_cadastrada` | Fornecimentos | Consome | Definida por Usuários/Acesso | | Pendente (P-12) |
| `pedido_criado` | Fornecimentos | Consome (reserva) | Definida pelo produtor | | Pendente (P-02) |
| `pedido_atualizado` | Fornecimentos | Consome (cancelamento devolve, venda dá baixa) | Definida pelo produtor | | Pendente (P-02) |
| Pedido de fornecimento | A definir | Publica e consome | A definir | | Pendente (P-13) |

O diagrama não deixa claro se os nomes acima são nomes de tópicos ou tipos de evento (P-17). A diferença importa: se `produto_cadastrado` e `produto_atualizado` estiverem em tópicos diferentes, o Kafka não garante a ordem entre eles, e um consumidor pode receber a alteração antes do cadastro (ver justificativa do RNF-07).

O formato do conteúdo de cada evento será detalhado em documento próprio de contrato de eventos, depois da definição da turma sobre serialização e envelope (P-08).

---

## 10. Matriz de rastreabilidade

| Requisito | Origem | Caso de uso | Critério de aceitação |
|---|---|---|---|
| RF-01 | F1, F2, F7 | UC-01 | CA-03 |
| RF-03 | F5 | | CA-04 |
| RF-04 | F5 | | CA-05 |
| RF-06 | F2, F5 | UC-01 | CA-03 |
| RF-07 | F5 | | CA-04 |
| RF-08 | F5 | | CA-05 |
| RF-09 | F1, F2 | UC-02 | CA-06 |
| RF-10 | F6, F7 | | CA-14 |
| RF-12 | F2 | UC-02 | CA-06 |
| RF-13, RF-14, RF-15 | F1, F2, F5, F6 | UC-03 | CA-07, CA-10 |
| RF-19 | F6 | UC-03 | CA-11 |
| RF-20 | F6 | UC-03 | CA-12 |
| RNF-01 | F3 | UC-01, UC-02 | CA-01 |
| RNF-02 | F3 | UC-01, UC-02 | CA-02, CA-09 |
| RNF-03 | F6 | UC-01, UC-02 | CA-13 |
| RNF-06 | F4 | UC-03 | CA-07 |
| RNF-09 | F4 | | CA-08 |

RNF-04, RNF-05 e RNF-12 são verificados por inspeção da arquitetura e da execução em contêiner, e não por cenário de teste. RNF-15 a RNF-18 recebem critérios quando a P-22 for resolvida. Os demais requisitos sem critério estão com status Proposto ou Pendente.

---

## 11. Pendências

| ID | Pergunta | A quem perguntar |
|---|---|---|
| P-01 | **Resolvida na versão 0.2.** O escopo do grupo é implementar os blocos 2 e 3 do diagrama e integrar com os demais. A lista de responsabilidades (F1) fala em "conversar com" os times de mercado, negociação, logística, frete e transportadoras, e o diagrama (F2) mostra esses módulos como serviços próprios | |
| P-02 | **Parcialmente resolvida na versão 0.3.** `pedido_criado` reserva o estoque, e o cancelamento e a conclusão da venda liberam ou dão baixa (F2, F6, F7). Falta o contrato: campos, como o pedido identifica o fornecimento e como cancelamento e venda aparecem em `pedido_atualizado` | Grupo responsável por pedidos (P-23) |
| P-03 | O estoque é controlado por fornecimento ou por produto? F6 descreve a reserva sem dizer, e F7 (23:43) tem a frase "fornecimento em estoque", de leitura incerta. Como vários fornecedores vendem o mesmo produto com preços próprios (RN-05), o grupo adota o controle por fornecimento | Professor |
| P-04 | O serviço deve revalidar o JWT ou confiar no API Gateway? Como o token informa a empresa e o perfil ativo? Qual o formato da resposta de token inválido? | Grupo de autenticação |
| P-05 | O que significa "origem"? Ela é atributo do produto (F1 cita "quantidade e origem de produtos") ou do fornecimento (F2 a coloca no bloco Fornecimentos)? Em F6 (10:58), ao falar de frete, o professor diz que a origem é o endereço do fornecedor e o destino é o endereço do comprador. Se for esse o sentido, a origem pertence ao fornecimento | Professor |
| P-06 | Quais os atributos obrigatórios do produto e os valores possíveis de unidade e tipo de transporte? Os valores de tipo de transporte precisam ser combinados com Logística/Frete, que os usa para escolher transportadoras | Professor, grupo de Logística/Frete |
| P-07 | **Parcialmente resolvida na versão 0.3.** Fornecedor e comprador cadastram produtos (F7) e o comprador consulta fornecimentos (F6, F7). Falta: quem pode alterar e excluir um produto (só quem cadastrou ou qualquer empresa com o perfil)? Quem gerencia categorias? O administrador acessa os nossos serviços? | Professor |
| P-08 | Qual a serialização dos eventos, o envelope padrão e o uso do Schema Registry? | Grupo de infra, turma |
| P-09 | A exclusão de produto é lógica ou física? O que acontece com os fornecimentos do produto? | Professor |
| P-10 | Categorias são uma lista fixa ou um cadastro? Existe hierarquia? | Professor |
| P-11 | Um fornecimento pode ser alterado (inclusive para repor quantidade) ou encerrado? Há eventos para isso? F1 cita "gestão de estoque" sem detalhar as operações | Professor |
| P-12 | Qual o contrato do evento `empresa_cadastrada`? | Grupo de Usuários/Acesso |
| P-13 | "Pedido de fornecimento entre fornecedor e grupo" corresponde ao `fornecimento_criado` ou é outro fluxo? Em F6 (19:31 a 19:52) há um trecho, com transcrição ruim, em que o professor parece falar de um fornecedor que anuncia que vai abastecer de forma recorrente um grupo ou setor de compradores, ligado à demanda recorrente. Pode ser esse o fluxo | Professor |
| P-14 | **Parcialmente resolvida na versão 0.3.** Docker é obrigatório (F7, 21:58). Falta: logs centralizados (ELK/Loki) e monitoramento (Prometheus/Grafana) são obrigatórios? Em F7 (0:55 a 1:17) o professor diz que algumas ferramentas sugeridas são obrigatórias e cita monitoramento, mas a transcrição não deixa claro quais | Professor, grupo de infra |
| P-15 | Qual o formato do preço (moeda e precisão)? | Professor |
| P-16 | O que acontece quando chega um pedido com quantidade maior que a disponível? O pedido é recusado? Há um evento de falha de reserva? F6 trata a reserva como transação (9:18) e cita o caso de 30 compradores pedindo o mesmo produto na mesma hora (14:40) | Professor, grupo responsável por pedidos |
| P-17 | Os nomes de eventos do diagrama são tópicos ou tipos de evento? | Grupo de infra, turma |
| P-18 | Existem metas de desempenho? | Professor |
| P-19 | Além de Fornecimentos e de Logística/Frete, quais módulos consomem os eventos de produto, `fornecimento_criado` e `estoque_atualizado`? | Demais grupos |
| P-20 | **Parcialmente resolvida na versão 0.3.** Vários fornecedores podem ofertar o mesmo produto (F6, 16:04 a 16:13). Falta: o mesmo fornecedor pode ter mais de um fornecimento do mesmo produto? | Professor |
| P-21 | Preço e quantidade podem ser zero? | Professor |
| P-22 | Quem implementa as telas do nosso módulo? Em F7 (21:45 a 21:58) o professor diz "a linguagem que vocês escolherem, o front e o back", o que sugere que cada grupo faz o próprio frontend seguindo os padrões da equipe de UX. Quais critérios de acessibilidade serão exigidos? | Professor, equipe de UX |
| P-23 | Qual grupo é responsável por pedidos? Em F7 (3:17 a 3:31) o professor diz que produtos, estoque e pedidos podem ser divididos entre os grupos, e em 2:46 a 2:55 associa o fechamento de pedido a quem cuida dos compradores | Professor, demais grupos |
| P-24 | Qual o papel do grupo de banco de dados, já que cada serviço tem banco próprio (F2)? Ele define tecnologia e infraestrutura dos bancos ou apenas apoia os grupos? | Grupo de banco de dados |
| P-25 | A transcrição F7 termina no meio de uma frase sobre empresas que têm dois perfis (29:45). Existe continuação dessa explicação? | Grupo (verificar gravação) |

---

## 12. Referências

- ISO/IEC/IEEE 29148:2018, Systems and software engineering, Life cycle processes, Requirements engineering. Base da estrutura deste documento.
- ISO/IEC 25010, modelo de qualidade de produto. Base das categorias dos requisitos não funcionais.
- Apache Kafka, documentação oficial: https://kafka.apache.org/documentation/
- KIP-679, Producer will enable the strongest delivery guarantee by default: https://cwiki.apache.org/confluence/display/KAFKA/KIP-679%3A+Producer+will+enable+the+strongest+delivery+guarantee+by+default
- Apache Kafka, notas de atualização (correção do KAFKA-13598): https://kafka.apache.org/31/getting-started/upgrade/
- RFC 6750, The OAuth 2.0 Authorization Framework: Bearer Token Usage: https://datatracker.ietf.org/doc/html/rfc6750
- RFC 9110, HTTP Semantics (códigos 400, 401, 403 e 422): https://datatracker.ietf.org/doc/html/rfc9110
- Gherkin Reference: https://cucumber.io/docs/gherkin/reference/

---

## Histórico de revisões

| Versão | Data | Descrição |
|---|---|---|
| 0.1 | 09/10/2026 | Rascunho inicial com base no enunciado, nos requisitos do professor e no diagrama de arquitetura |
| 0.2 | 09/10/2026 | Inclusão da lista de responsabilidades do grupo como fonte F1 e das orientações de Kafka como fonte F5. Origem de cada requisito passa a indicar a fonte exata. P-01 resolvida. P-05 e P-11 detalhadas |
| 0.3 | 09/10/2026 | Inclusão das transcrições das aulas 1 e 2 como fontes F6 e F7. Estoque passa a ter quantidade disponível e reservada, com reserva, liberação e baixa a partir de eventos de pedido (RF-13, RF-14, RF-19, RF-20, RN-06, RN-07, RNF-14, UC-03). Comprador e fornecedor podem cadastrar produtos (RN-08). Comprador consulta fornecimentos (RF-10). Perfis e autorização por perfil confirmados (RN-02, RN-04, RNF-03). Docker obrigatório (RNF-12). Requisitos de interface incluídos (RNF-15 a RNF-18). Novos critérios CA-10 a CA-14. P-02, P-07, P-14 e P-20 parcialmente resolvidas. Novas pendências P-22 a P-25 |
