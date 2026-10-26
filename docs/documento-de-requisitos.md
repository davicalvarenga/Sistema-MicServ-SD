# Documento de Requisitos

**Grupo:** Fornecimento e Produtos
**Sistema:** Portal B2B Distribuído (disciplina de Sistemas Distribuídos)
**Integrantes:** Daniel Carvalho Coutinho, Davi Coelho de Alvarenga, Gabriel Vicentte dos Santos Ferreira, Rafael de Castro Noleto
**Versão:** 0.4 (rascunho para revisão interna)
**Data:** 26/10/2026

> Itens com status **Pendente** ou **Proposto** ainda podem mudar. O Grupo de Teste (QA) deve testar apenas itens com status **Confirmado** até a versão 1.0 deste documento.

---

## 1. Introdução

### 1.1 Propósito

Este documento descreve os requisitos dos serviços sob responsabilidade do grupo Fornecimento e Produtos. Ele é a referência do Grupo de Teste (QA) para planejar e executar testes. Cada requisito indica a fonte de onde veio e o seu status, para que fique claro o que foi exigido pelo professor, o que vem do diagrama de arquitetura e o que é decisão do grupo.

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

- Cadastro de empresas, perfis de acesso, emissão de tokens (grupo de Autenticação, `usuarios-service`, F7 e F8)
- Front-ends e padrões visuais (grupo de UX/UI, F8). O front-end `/app/produtos` ("Catálogo e Gestão de Estoque do Fornecedor") é feito por esse grupo e consome a nossa API pelo gateway
- Demanda (grupo de Compra e Demanda, `demanda-service`)
- Mercado, Negociação/Leilão e Pedidos (grupo de Mercado, Negociação/Leilão e Pedidos, F9)
- Frete e transportadoras (grupo de Logística/Transporte, `logistica-service` e `transportadoras-service`)
- Modelagem e DDL do banco, roles e auditoria (grupo de Banco de Dados, F8)
- Gateway, cluster Redpanda (Kafka), Schema Registry, observabilidade e CI/CD (grupo de Infraestrutura, F8)
- Testes funcionais, de integração, de carga e de caos (Grupo de Teste, F8)

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
| F8 | Kit de integração do grupo de Infraestrutura (repositório `Printf-PedroCardoso/portal-b2b-kit-infra`, commit `630515c`, 25/10/2026): guia `ORIENTACOES-ARQUITETURA-GRUPOS.md`, catálogo de eventos `CONTRACTS.md`, script de tópicos, script do banco e boilerplates dos serviços |
| F9 | Relação final de grupos e integrantes divulgada à turma |

Quando F8 divergir de uma orientação do professor (F2, F3, F6, F7), vale a do professor, e a divergência é registrada como pendência para alinhamento com o grupo de Infraestrutura. Quando os próprios arquivos de F8 divergirem entre si, vale o que está implementado (script de tópicos, script do banco e código), e a divergência também é registrada.

As transcrições F6 e F7 têm muitos erros de reconhecimento. Só trechos sem ambiguidade são usados como fonte de requisito confirmado, sempre com a marcação de tempo do áudio (ex.: F7, 19:35). Trechos duvidosos aparecem apenas nas pendências.

### 1.5 Convenções

**Identificadores:** RF (requisito funcional), RNF (requisito não funcional), RD (requisito de dados), RN (regra de negócio), UC (caso de uso), CA (critério de aceitação), P (pendência).

**Origem:** identificador da fonte (F1 a F9, seção 1.4). F4 indica decisão do grupo.

**Status:**

| Status | Significado |
|---|---|
| Confirmado | Definido por fonte do professor (F1, F2, F3, F5, F6 ou F7) ou pelo acordo de integração entre os grupos (F8). Pode ser testado |
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
| Autenticação (`usuarios-service`) | Cadastro de empresas e perfis (F7, 19:09). Token JWT com `sub`, empresa, `perfil` (comprador, fornecedor, transportadora ou admin) e `exp`. Access token de 15 minutos e refresh token de 8 horas (F8). Evento `empresa_cadastrada`, com chave `empresaId` (F8) | Confirmado (divergências: P-04, P-31; conteúdo do evento: P-12) |
| Gateway (grupo de Infraestrutura) | Gateway Nginx na porta 8080: rotas `/api/v1/produtos` e `/api/v1/fornecimentos`, limite de 100 requisições por segundo por IP e repasse do cabeçalho `X-Correlation-Id` (F8). A validação do token é feita em cada serviço, não no gateway (F8, `services/common/auth.py`) | Confirmado |
| Mercado, Negociação/Leilão e Pedidos (`pedidos-service`) | Eventos `pedido_criado` e `pedido_atualizado` com identificação do fornecimento, quantidade e situação (criado, cancelado, venda concluída). O professor associa a criação do pedido à entrada em leilão ou negociação, momento em que o estoque precisa ser bloqueado (F6, 8:19; F7, 21:03) | Pendente (P-02, P-29) |
| Mercado (`mercado-service`) | Consome `produto_cadastrado`, `fornecimento_criado` e `estoque_atualizado` (F8, `CONTRACTS.md`) | Confirmado |
| Compra e Demanda (`demanda-service`) | Consome `produto_cadastrado` (F8, `CONTRACTS.md`) | Confirmado |
| Logística/Transporte (`logistica-service`) | Precisa do tipo de transporte do produto para escolher as transportadoras (F6, 10:33; F7, 24:56). F8 não lista Logística como consumidora de eventos de produto | Pendente (P-27) |
| Banco de Dados | Banco único PostgreSQL 16 `portal_b2b` com um schema por serviço (`produtos` e `fornecimentos`). DDL feito pelo grupo de Banco de Dados com o usuário `portal_ddl`. Os serviços usam os usuários `svc_produtos` e `svc_fornecimentos`, só com DML no próprio schema (F8) | Confirmado (ajuste no DDL: P-28; permissões: P-32) |
| Infraestrutura | Cluster Redpanda (compatível com Kafka) na porta 19092, tópicos e DLTs criados pelo script do kit, Schema Registry embutido na porta 18081, Prometheus, Grafana, Loki e Jaeger (F8) | Confirmado |
| UX/UI | Front-end `/app/produtos` e padrões visuais, consumindo a API pelo gateway e exibindo `title`, `detail` e `correlationId` dos erros (F8) | Confirmado |
| Teste | Testes de contrato, integração, carga (k6) e caos sobre os nossos serviços, com as metas da seção 4 (F8) | Confirmado |

### 2.3 Premissas

1. A autenticação usa JWT assinado com HS256. Cada serviço valida o token localmente com a chave compartilhada, usando a biblioteca comum do kit (F8, `services/common/auth.py`).
2. Cada serviço tem o seu próprio schema no banco `portal_b2b`, e nenhum outro serviço acessa esse schema (F2, legenda "Banco de dados próprio de cada serviço"; F8, seção 5.1 do guia).
3. Toda comunicação de negócio entre módulos acontece por eventos no cluster Redpanda, compatível com a API do Kafka. Chamadas REST ocorrem apenas entre front-end, gateway e serviços (F2, legenda; F8, seção 3 do guia).
4. Os serviços rodam em contêineres Docker, em duas instâncias cada (`app1-*` e `app2-*`), atrás do gateway (F7, 21:58; F8, `docker-compose.yml`).

---

## 3. Requisitos funcionais

### 3.1 Serviço de Produtos

| ID | Requisito | Origem | Status |
|---|---|---|---|
| RF-01 | O sistema deve permitir que empresas com perfil de fornecedor ou de comprador cadastrem produto com nome, categoria, unidade e tipo de transporte | F1, F2, F7, F8 | Confirmado (perfil comprador: P-30; valores aceitos: P-06) |
| RF-02 | O sistema deve permitir consultar produtos, em lista paginada (com filtro por categoria) e por identificador | F4, F8 | Confirmado |
| RF-03 | O sistema deve permitir alterar um produto cadastrado | F5 | Confirmado |
| RF-04 | O sistema deve permitir excluir um produto | F5 | Confirmado (regra de exclusão: P-09) |
| RF-05 | O sistema deve permitir gerenciar as categorias de produto | F1, F2 | Pendente (P-10) |
| RF-06 | Ao cadastrar um produto, o serviço deve publicar o evento `produto_cadastrado`, com chave `produtoId` | F2, F5, F8 | Confirmado |
| RF-07 | Ao alterar um produto, o serviço deve publicar um evento de alteração de produto | F5 | Confirmado (o kit não tem tópico para esse evento: P-26) |
| RF-08 | Ao excluir um produto, o serviço deve publicar um evento de exclusão de produto | F5 | Confirmado (o kit não tem tópico para esse evento: P-26) |

### 3.2 Serviço de Fornecimentos

| ID | Requisito | Origem | Status |
|---|---|---|---|
| RF-09 | O fornecedor deve poder criar um fornecimento (relação de fornecimento) informando produto, preço, quantidade e origem | F1, F2, F8 | Confirmado |
| RF-10 | O sistema deve permitir que compradores consultem os fornecimentos, em lista e por identificador, incluindo a quantidade disponível | F6, F7, F8 | Confirmado |
| RF-11 | O sistema deve permitir alterar ou encerrar um fornecimento | F4 | Pendente (P-11) |
| RF-12 | Ao criar um fornecimento, o serviço deve publicar o evento `fornecimento_criado`, com chave `fornecimentoId` | F2, F8 | Confirmado |
| RF-13 | O serviço deve manter, para cada fornecimento, a quantidade disponível e a quantidade reservada | F1, F2, F6 | Confirmado (granularidade: P-03; ajuste no DDL do kit: P-28) |
| RF-14 | Ao consumir o evento de criação de pedido, o serviço deve reservar a quantidade do pedido: subtrair da quantidade disponível e somar à quantidade reservada | F2, F5, F6 | Confirmado (contrato do evento: P-02; momento da criação do pedido: P-29) |
| RF-15 | Sempre que o estoque mudar, o serviço deve publicar o evento `estoque_atualizado`, com chave `fornecimentoId` | F2, F5, F8 | Confirmado |
| RF-16 | O serviço de Fornecimentos deve consumir os eventos de produto para manter uma referência local dos produtos válidos | F5, F8, F4 | Confirmado para `produto_cadastrado` (F8). Alteração e exclusão: P-26 |
| RF-17 | O serviço de Fornecimentos deve consumir o evento `empresa_cadastrada` para reconhecer as empresas com perfil de fornecedor | F2, F8 | Confirmado (conteúdo do evento: P-12) |
| RF-18 | O sistema deve publicar e consumir eventos de pedido de fornecimento entre fornecedor e grupo | F5 | Pendente (P-13) |
| RF-19 | Ao consumir o evento de cancelamento de pedido, o serviço deve devolver a quantidade reservada à quantidade disponível | F6 | Confirmado (contrato do evento: P-02) |
| RF-20 | Ao consumir o evento de conclusão da venda, o serviço deve dar baixa definitiva na quantidade reservada | F6 | Confirmado (contrato do evento: P-02) |
| RF-21 | Os eventos de produto devem conter o tipo de transporte, para que Logística/Transporte identifique as transportadoras que podem transportar o produto | F6, F4 | Proposto (P-27) |

**Justificativa do RF-13, RF-14, RF-19 e RF-20:** na aula 2, o professor diz ao grupo que, "a partir do momento de entrar no leilão ou fizer uma negociação, tem que fechar um pedido, tem que bloquear" o estoque (F7, 21:03). Na aula 1 (F6, 8:13 a 9:42), ele descreve que, ao criar um pedido, o produto sai do estoque e fica bloqueado no pedido, enquanto o restante continua visível para quem quer comprar. Se o pedido for cancelado, a quantidade volta ao estoque. Se a negociação terminar em venda, a operação é finalizada. Ele chama a operação de transação.

**Justificativa do RF-16:** as orientações de integração (F5) exigem que o módulo consuma eventos de produto. Com Produtos e Fornecimentos em schemas separados e sem acesso cruzado (F2, F8), o serviço de Fornecimentos precisa saber quais produtos existem sem consultar o schema de Produtos. Consumir os eventos de produto atende às duas exigências.

---

## 4. Requisitos não funcionais

| ID | Requisito | Categoria | Origem | Status |
|---|---|---|---|---|
| RNF-01 | Todos os endpoints de negócio dos dois serviços exigem autenticação. Requisição sem token é recusada com HTTP 401 | Segurança | F3, F8 | Confirmado |
| RNF-02 | Requisição com token expirado ou inválido é recusada com HTTP 401, e o cliente precisa se autenticar novamente | Segurança | F3, F8 | Confirmado |
| RNF-03 | Requisição autenticada sem o perfil necessário é recusada com HTTP 403 | Segurança | F6, F8 | Confirmado (permissões por operação: P-07, P-30) |
| RNF-04 | A comunicação de negócio entre módulos é feita por eventos no cluster Redpanda, compatível com a API do Kafka | Interoperabilidade | F2, F5, F8 | Confirmado |
| RNF-05 | Cada serviço usa apenas o próprio schema do banco `portal_b2b` (`produtos` ou `fornecimentos`). Nenhum serviço consulta ou altera schemas de outro | Manutenibilidade | F2, F8 | Confirmado |
| RNF-06 | O processamento de eventos consumidos é idempotente: o `eventId` é registrado na tabela `processed_events` do próprio schema, na mesma transação da alteração de dados, e um evento repetido é ignorado | Confiabilidade | F8, F4 | Confirmado |
| RNF-07 | Todo evento publicado usa o `aggregateId` como chave da mensagem: `produtoId` nos eventos de produto e `fornecimentoId` nos eventos de fornecimento e de estoque | Confiabilidade | F8, F4 | Confirmado (divergência no guia do kit: P-33) |
| RNF-08 | Os produtores são configurados com `acks=all` e `enable.idempotence=true` | Confiabilidade | F8, F4 | Confirmado |
| RNF-09 | Nenhum evento publicado contém token de acesso | Segurança | F4 | Proposto |
| RNF-10 | Um evento que falha depois de 3 tentativas, com espera de 1, 2 e 4 segundos, é enviado ao tópico `produtos.dlt` ou `fornecimentos.dlt`, sem bloquear o consumo dos demais | Confiabilidade | F8, F4 | Confirmado |
| RNF-11 | Os serviços registram logs em JSON na saída padrão, com o `correlationId` em todas as linhas. O `correlationId` vem do cabeçalho `X-Correlation-Id` ou é gerado (UUID v4) e é repassado nos eventos publicados | Manutenibilidade | F8 | Confirmado |
| RNF-12 | Os serviços são executáveis em contêiner Docker | Portabilidade | F2, F7, F8 | Confirmado ("vocês precisam trabalhar com docker", F7, 21:48 a 21:58) |
| RNF-13 | Os eventos são publicados em JSON com o envelope canônico: `eventId`, `eventType`, `eventVersion`, `timestamp`, `source`, `correlationId`, `aggregateId` e `payload` | Interoperabilidade | F8 | Confirmado (uso do Schema Registry: P-08) |
| RNF-14 | A reserva de estoque é atômica: reservas simultâneas para o mesmo fornecimento não podem, somadas, ultrapassar a quantidade disponível | Confiabilidade | F6, F8, F4 | Confirmado (comportamento quando falta estoque: P-16) |
| RNF-15 | As telas seguem o padrão visual definido pela equipe de UX: visual limpo, verde e branco, linhas finas nas bordas dos campos | Usabilidade | F7, F8 | Confirmado. Responsabilidade do grupo de UX/UI (F8) |
| RNF-16 | As telas têm modo escuro, em cinza escuro e preto, com destaques em verde mais escuro | Usabilidade | F7, F8 | Confirmado. Responsabilidade do grupo de UX/UI (F8) |
| RNF-17 | As telas atendem a requisitos de acessibilidade | Usabilidade | F7, F8 | Confirmado. Responsabilidade do grupo de UX/UI (F8) |
| RNF-18 | As telas são responsivas | Usabilidade | F7, F8 | Confirmado. Responsabilidade do grupo de UX/UI (F8) |
| RNF-19 | As rotas de negócio usam os prefixos `/api/v1/produtos` e `/api/v1/fornecimentos`. Fora de `/api/v1` só existem as rotas técnicas do RNF-22 | Interoperabilidade | F8 | Confirmado |
| RNF-20 | Toda resposta de erro (4xx e 5xx) segue a RFC 7807, com `Content-Type: application/problem+json` e os campos `type`, `title`, `status`, `detail`, `instance`, `correlationId` e `timestamp` | Interoperabilidade | F8 | Confirmado |
| RNF-21 | Toda listagem é paginada com `page` e `size`. Pedido com `size` maior que 100 é recusado com HTTP 422 | Desempenho | F8 | Confirmado |
| RNF-22 | Cada serviço expõe `GET /health` (processo vivo), `GET /health/ready` (200 se PostgreSQL e Redpanda respondem, 503 se não), `GET /metrics` (formato Prometheus, com requisições por código de status e tempo de resposta) e `GET /docs` com `GET /openapi.json` | Manutenibilidade | F8 | Confirmado |
| RNF-23 | Cada instância do serviço usa no máximo 5 conexões com o banco | Desempenho | F8 | Confirmado |
| RNF-24 | Cada serviço se conecta ao banco com o próprio usuário (`svc_produtos` ou `svc_fornecimentos`), que só tem permissão de leitura e escrita de dados no próprio schema. O usuário administrativo `portal_admin` nunca é usado pelos serviços | Segurança | F8 | Confirmado (falha no script do kit: P-32) |
| RNF-25 | Metas de desempenho: leitura com p95 de até 500 ms com 200 requisições simultâneas, escrita com p95 de até 1000 ms e menos de 1% de respostas 5xx sob estresse | Desempenho | F8 (metas do Grupo de Teste) | Confirmado |
| RNF-26 | Os serviços não guardam estado de negócio em memória. Todo estado fica no banco, para que as duas instâncias de cada serviço respondam igual | Confiabilidade | F8, F4 | Confirmado |

**Justificativas técnicas:**

- **RNF-06:** em caso de falha do consumidor entre o processamento da mensagem e o registro do offset, o Kafka entrega a mensagem novamente (semântica "at least once", documentação do Apache Kafka, seção *Message Delivery Semantics*). Sem idempotência, uma mesma reserva de estoque poderia ser aplicada duas vezes. O registro precisa estar no banco, e não na memória do processo, porque a memória se perde quando o serviço reinicia, e as duas instâncias do serviço não compartilham memória (RNF-26).
- **RNF-07:** o Kafka garante ordem apenas dentro de uma partição, e mensagens com a mesma chave vão para a mesma partição (documentação do Apache Kafka, seção *Topics and Partitions*). Usar o identificador da entidade como chave preserva a ordem dos eventos de um mesmo produto ou fornecimento dentro de cada tópico.
- **RNF-08:** são os padrões do produtor desde o Kafka 3.0 (KIP-679). Um defeito impediu que fossem aplicados nas versões 3.0.0 e 3.1.0, corrigido em 3.0.1, 3.1.1 e 3.2.0 (notas de atualização do Apache Kafka). A biblioteca comum do kit já configura os dois valores (F8, `services/common/events.py`).
- **RNF-09:** o token expira, e o evento permanece armazenado no Kafka durante o período de retenção (7 dias nos tópicos do kit, F8). Gravar o token no evento expõe uma credencial. O evento leva apenas o identificador de quem executou a ação.
- **RNF-14:** o professor trata a reserva como transação (F6, 9:18) e levanta o caso de 30 compradores querendo o mesmo produto na mesma hora (F6, 14:40). Se duas reservas lerem o mesmo saldo e gravarem em seguida, as duas podem ser aceitas e o estoque fica negativo. A verificação do saldo e a reserva precisam acontecer na mesma operação atômica. O boilerplate do kit também proíbe estoque negativo (F8, `fornecimentos-service/main.py`).
- **RNF-24:** é o princípio do menor privilégio. Se o serviço for comprometido, o atacante fica limitado ao schema do serviço e não consegue criar, apagar ou alterar tabelas.
- **RNF-26:** o gateway distribui as requisições entre `app1` e `app2` de cada serviço (F8, `docker-compose.yml` e `gateway/nginx.conf`). Um produto guardado na memória de `app1` não existiria para `app2`. Os boilerplates do kit guardam os dados em dicionários na memória e precisam ser substituídos por acesso ao banco.
- **RNF-25:** as metas são do Grupo de Teste, que vai reprovar o serviço que não as atingir (F8, seção 10.2 do guia).

---

## 5. Requisitos de dados

| ID | Entidade | Atributos | Origem | Status |
|---|---|---|---|---|
| RD-01 | Produto | Identificador, nome, categoria, unidade e tipo de transporte, todos obrigatórios | F1, F2, F8 | Confirmado |
| RD-02 | Produto | Descrição | F4 | Proposto (P-06) |
| RD-03 | Fornecimento | Identificador, fornecedor (empresa), produto, preço, quantidade, origem | F1, F2, F8 | Confirmado (significado de origem: P-05) |
| RD-04 | Fornecimento | Preço e quantidades com até 2 casas decimais (`NUMERIC(12,2)` no banco do kit). Quantidades decimais permitem unidades como KG e L | F8 | Confirmado (moeda: P-15) |
| RD-05 | Categoria | Estrutura (lista fixa, cadastro, hierarquia) | F1 | Pendente (P-10) |
| RD-06 | Estoque do fornecimento | Quantidade disponível e quantidade reservada | F6 | Confirmado (a tabela do kit só tem a disponível: P-28) |
| RD-07 | Controle de eventos | Tabela `processed_events` (`event_id`, `processed_at`) em cada schema | F8 | Confirmado |

---

## 6. Regras de negócio

### 6.1 Regras definidas

| ID | Regra | Origem | Status |
|---|---|---|---|
| RN-01 | Um fornecimento relaciona um fornecedor e um produto | F1, F2 | Confirmado |
| RN-02 | Apenas empresas com perfil de fornecedor podem criar fornecimentos | F1, F2, F6, F8 | Confirmado |
| RN-03 | Um fornecimento só pode referenciar um produto existente no catálogo | F4 | Proposto |
| RN-04 | Uma empresa pode ter os perfis de fornecedor, comprador e transportadora ao mesmo tempo | F6 | Confirmado (o modelo de dados do kit tem um tipo por empresa e um perfil por usuário: P-31) |
| RN-05 | Um mesmo produto pode ser ofertado por vários fornecedores | F6 | Confirmado |
| RN-06 | A quantidade reservada por um pedido volta a ficar disponível se o pedido for cancelado | F6 | Confirmado |
| RN-07 | A quantidade reservada por um pedido sai do estoque quando a venda é concluída | F6 | Confirmado |
| RN-08 | Empresas com perfil de fornecedor ou de comprador podem cadastrar produtos | F7 (1:17 a 1:49) | Confirmado (o guia do kit restringe o comprador: P-30) |
| RN-09 | Todo produto tem um tipo de transporte definido | F7 (25:21), F8 (`tipo_transporte NOT NULL`) | Confirmado (valores aceitos: P-06) |
| RN-10 | O fornecedor de um fornecimento é a empresa do token (`empresaId`). O serviço ignora qualquer identificador de fornecedor enviado no corpo da requisição | F4 | Proposto |
| RN-11 | O estoque nunca fica negativo. Uma operação que pede mais do que a quantidade disponível é recusada, com HTTP 422 quando a operação vem por REST | F8, F6 | Confirmado (falta de estoque em evento de pedido: P-16) |

### 6.2 Regras em aberto

As perguntas abaixo não têm resposta nas fontes. Não devem ser testadas até a definição.

| Pendência | Pergunta |
|---|---|
| P-09 | A exclusão de produto é lógica ou física? O que acontece com os fornecimentos ativos do produto excluído? |
| P-16 | Como o serviço avisa o grupo de Pedidos quando chega um pedido com quantidade maior que a disponível? |
| P-20 | O mesmo fornecedor pode ter mais de um fornecimento do mesmo produto? |
| P-21 | Preço e quantidade podem ser zero? O boilerplate do kit exige valores maiores que zero no cadastro (F8) |

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
  - A2. Dados obrigatórios ausentes ou inválidos: o serviço retorna HTTP 422 indicando os campos com erro. Nada é gravado nem publicado.
  - A3. Perfil ativo sem permissão de cadastro (por exemplo, apenas transportadora): o serviço retorna HTTP 403. Nada é gravado nem publicado.
- **Requisitos relacionados:** RF-01, RF-06, RN-08, RNF-01, RNF-02, RNF-03

### UC-02 Publicar fornecimento

- **Ator:** Fornecedor
- **Pré-condição:** fornecedor autenticado com token válido
- **Fluxo principal** (F2, fluxo passo 1):
  1. O fornecedor informa produto, preço, quantidade e origem. O fornecedor é a empresa do token (RN-10).
  2. O serviço valida os dados e verifica se o produto existe na referência local de produtos (RN-03, RF-16).
  3. O serviço grava o fornecimento.
  4. O serviço publica `fornecimento_criado`.
  5. O serviço retorna HTTP 201 com o identificador do fornecimento.
- **Fluxos alternativos:**
  - A1. Token ausente, expirado ou inválido: HTTP 401. Nada é gravado nem publicado.
  - A2. Perfil ativo diferente de fornecedor: HTTP 403 (RN-02).
  - A3. Produto inexistente: HTTP 422. Nada é gravado nem publicado.
  - A4. Dados inválidos: HTTP 422 indicando os campos com erro (padrão de validação do FastAPI, base do kit). Nada é gravado nem publicado.
  - Todas as respostas de erro seguem a RFC 7807 (RNF-20).
- **Requisitos relacionados:** RF-09, RF-12, RN-01, RN-02, RN-03, RN-10, RNF-20

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

CA-15 (RNF-21)
Dado um usuário autenticado
Quando ele lista produtos ou fornecimentos com size=101
Então a resposta tem status 422
E o corpo segue a RFC 7807

CA-16 (RNF-20, RNF-11)
Dado uma requisição com o cabeçalho X-Correlation-Id "abc-123"
Quando o serviço responde com erro 4xx ou 5xx
Então o Content-Type é application/problem+json
E o corpo contém type, title, status, detail, instance, timestamp e correlationId igual a "abc-123"

CA-17 (RNF-22)
Dado que o PostgreSQL ou o Redpanda está fora do ar
Quando o cliente chama GET /health/ready
Então a resposta tem status 503
E GET /health continua respondendo 200

CA-18 (RNF-13, RNF-07, RF-12)
Dado um fornecimento criado com sucesso
Quando o evento fornecimento_criado é lido no tópico
Então a mensagem tem como chave o fornecimentoId
E o valor contém eventId, eventType, eventVersion, timestamp, source, correlationId, aggregateId e payload

CA-19 (RN-10)
Dado um fornecedor autenticado da empresa A
Quando ele cria um fornecimento enviando no corpo o identificador da empresa B como fornecedor
Então o fornecimento é gravado com a empresa A como fornecedora
```

Os valores numéricos dos CA-10 a CA-12 são exemplos para o teste, não regras de negócio. Os eventos de pedido citados dependem do contrato com o grupo de Mercado, Negociação/Leilão e Pedidos (P-02).

Nos CA-01 e CA-02, a resposta 401 segue a RFC 7807 (RNF-20), como faz a biblioteca comum do kit (F8, `services/common/auth.py`).

O Grupo de Teste já prevê dois testes que cobrem estes critérios (F8, seção 10.2 do guia): token de comprador tentando criar fornecimento deve receber 403 (CA-13) e evento repetido deve ser ignorado com registro em log (CA-07).

---

## 9. Eventos

Os tópicos, as chaves e os consumidores abaixo seguem o catálogo do kit de infraestrutura (F8, `CONTRACTS.md` e `scripts/init_topics.sh`). Cada evento tem o seu próprio tópico, com o mesmo nome do evento, 3 partições, fator de replicação 3 e retenção de 7 dias.

| Tópico | Serviço | Papel | Chave (`aggregateId`) | Outros consumidores (F8) | Status |
|---|---|---|---|---|---|
| `produto_cadastrado` | Produtos | Publica | `produtoId` | Fornecimentos, Demanda, Mercado | Confirmado |
| Alteração de produto | Produtos | Publica | `produtoId` | | Pendente: o kit não tem tópico (P-26) |
| Exclusão de produto | Produtos | Publica | `produtoId` | | Pendente: o kit não tem tópico (P-26) |
| `produto_cadastrado` | Fornecimentos | Consome | `produtoId` | | Confirmado |
| `fornecimento_criado` | Fornecimentos | Publica | `fornecimentoId` | Mercado | Confirmado |
| `estoque_atualizado` | Fornecimentos | Publica | `fornecimentoId` | Mercado | Confirmado |
| `empresa_cadastrada` | Fornecimentos | Consome | `empresaId` | | Confirmado (conteúdo: P-12) |
| `pedido_criado` | Fornecimentos | Consome (reserva) | `pedidoId` | | Pendente (P-02, P-29) |
| `pedido_atualizado` | Fornecimentos | Consome (cancelamento devolve, venda dá baixa) | `pedidoId` | | Pendente (P-02) |
| `produtos.dlt` | Produtos | Publica (falhas) | a do evento original | | Confirmado (1 partição, retenção de 14 dias) |
| `fornecimentos.dlt` | Fornecimentos | Publica (falhas) | a do evento original | | Confirmado (1 partição, retenção de 14 dias) |
| Pedido de fornecimento | A definir | Publica e consome | A definir | | Pendente (P-13) |

**Envelope e conteúdo.** Todos os eventos usam o envelope canônico do RNF-13. O conteúdo do `payload` de cada evento, com JSON Schema e exemplo, está no [Contrato de Eventos](contrato-eventos.md).

**Ordem entre tópicos.** Como cada evento tem o próprio tópico, o Kafka não garante a ordem entre eventos de tópicos diferentes, mesmo com a mesma chave (RNF-07). Isso afeta a proposta da P-26: se a alteração de produto ficar em um tópico separado, um consumidor pode receber a alteração antes do cadastro. O consumidor precisa tolerar essa situação, por exemplo comparando o `timestamp` ou uma versão do produto.

**Consumidores fora do catálogo.** No Kafka, cada serviço lê os tópicos com o próprio grupo de consumidores, de forma independente dos outros. O serviço de Fornecimentos consegue ler `pedido_criado` e `pedido_atualizado` mesmo sem constar como consumidor no `CONTRACTS.md`, mas o catálogo precisa ser atualizado para que o grupo de Pedidos saiba que existe essa dependência (P-02).

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
| RNF-07, RNF-13 | F8 | | CA-18 |
| RNF-11, RNF-20 | F8 | UC-01, UC-02 | CA-16 |
| RNF-21 | F8 | | CA-15 |
| RNF-22 | F8 | | CA-17 |
| RN-10 | F4 | UC-02 | CA-19 |

RNF-04, RNF-05, RNF-12, RNF-19, RNF-23, RNF-24 e RNF-26 são verificados por inspeção da configuração e do código. RNF-25 é verificado pelos testes de carga do Grupo de Teste. RNF-15 a RNF-18 são do grupo de UX/UI. Os demais requisitos sem critério estão com status Proposto ou Pendente.

---

## 11. Pendências

Pendências resolvidas continuam na tabela, marcadas, para manter o histórico. As pendências P-26 a P-33 surgiram da análise do kit de infraestrutura (F8).

| ID | Pergunta | A quem perguntar |
|---|---|---|
| P-01 | **Resolvida na versão 0.2.** O escopo do grupo é implementar os blocos 2 e 3 do diagrama e integrar com os demais | |
| P-02 | **Parcialmente resolvida.** O exemplo de `pedido_criado` no guia do kit traz `pedidoId`, `negociacaoId`, `compradorId`, `fornecedorId`, `produtoId`, `quantidade`, `valorTotal` e `status`. Faltam: (a) o `fornecimentoId`, sem o qual não sabemos de qual oferta reservar se o fornecedor tiver mais de uma do mesmo produto (P-20); (b) os valores de `status` em `pedido_atualizado` que indicam cancelamento e venda concluída; (c) incluir o `fornecimentos-service` como consumidor de `pedido_criado` e `pedido_atualizado` no `CONTRACTS.md`, que hoje lista só a Logística | Grupo de Mercado, Negociação/Leilão e Pedidos; Infraestrutura |
| P-03 | O estoque é controlado por fornecimento ou por produto? O grupo adota o controle por fornecimento, e o kit também (a quantidade fica na tabela `fornecimento`) | Professor |
| P-04 | **Resolvida pelo F8.** O token é JWT HS256, validado em cada serviço com a biblioteca comum do kit. A resposta de erro é 401 no formato RFC 7807. Resta a divergência no nome do claim da empresa (P-33) | |
| P-05 | O que significa "origem"? O kit guarda como texto livre obrigatório na tabela `fornecimento`. Em F6 (10:58), a origem do frete é o endereço do fornecedor | Professor |
| P-06 | **Parcialmente resolvida.** O boilerplate do kit sugere unidades `KG`, `TON`, `UN`, `CX`, `L` e tipos de transporte `GRANEL`, `REFRIGERADO`, `CARGA_SECA`, `PERIGOSO`. Falta confirmar essas listas, principalmente com Logística/Transporte, que usa o tipo de transporte | Grupo de Logística/Transporte |
| P-07 | **Parcialmente resolvida.** Falta: quem pode alterar e excluir um produto (só a empresa que cadastrou?) e o que o perfil `admin` pode fazer nos nossos serviços | Professor |
| P-08 | **Parcialmente resolvida pelo F8.** Serialização em JSON com envelope canônico. O kit sobe o Schema Registry do Redpanda com compatibilidade `BACKWARD`, mas a biblioteca comum publica JSON sem registrar schema. Falta saber se o registro é obrigatório | Infraestrutura |
| P-09 | A exclusão de produto é lógica ou física? A tabela `produto` do kit não tem coluna de situação, o que obrigaria exclusão física ou um ajuste no DDL | Professor, Banco de Dados |
| P-10 | Categorias são uma lista fixa ou um cadastro? O kit guarda a categoria como texto na tabela `produto`, sem tabela própria | Professor |
| P-11 | Um fornecimento pode ser alterado (inclusive para repor quantidade) ou encerrado? Há eventos para isso? O kit não tem tópico para alteração de fornecimento | Professor |
| P-12 | Qual o conteúdo (`payload`) do evento `empresa_cadastrada`? O `CONTRACTS.md` traz só o envelope e a chave | Grupo de Autenticação |
| P-13 | "Pedido de fornecimento entre fornecedor e grupo" corresponde ao `fornecimento_criado` ou é outro fluxo? O kit não tem tópico com esse nome | Professor |
| P-14 | **Resolvida pelo F8.** O kit inclui Prometheus, Grafana, Loki, Jaeger e Alertmanager, e exige `/health`, `/health/ready`, `/metrics` e logs JSON (RNF-11, RNF-22) | |
| P-15 | Qual a moeda do preço? A precisão é de 2 casas decimais (RD-04) | Professor |
| P-16 | Como o serviço avisa o grupo de Pedidos quando chega um pedido com quantidade maior que a disponível? O kit não tem tópico para falha de reserva | Grupo de Mercado, Negociação/Leilão e Pedidos; Infraestrutura |
| P-17 | **Resolvida pelo F8.** Os nomes do diagrama são tópicos: um tópico por tipo de evento | |
| P-18 | **Resolvida pelo F8.** Metas de desempenho do Grupo de Teste no RNF-25 | |
| P-19 | **Resolvida pelo F8.** Consumidores na seção 9. Resta a Logística (P-27) | |
| P-20 | **Parcialmente resolvida.** Vários fornecedores podem ofertar o mesmo produto (F6). Falta: o mesmo fornecedor pode ter mais de um fornecimento do mesmo produto? Se puder, o `pedido_criado` precisa do `fornecimentoId` (P-02) | Professor |
| P-21 | Preço e quantidade podem ser zero? O boilerplate do kit exige valores maiores que zero | Professor |
| P-22 | **Resolvida pelo F8.** Os front-ends são do grupo de UX/UI. O nosso grupo entrega a API e os erros no padrão RFC 7807, que o front-end exibe | |
| P-23 | **Resolvida pelo F9.** Pedidos é do grupo de Mercado, Negociação/Leilão e Pedidos | |
| P-24 | **Resolvida pelo F8.** O grupo de Banco de Dados faz a modelagem, o DDL, as roles, a auditoria e as migrações | |
| P-25 | A transcrição F7 termina no meio de uma frase sobre empresas que têm dois perfis (29:45). Existe continuação? | Grupo (verificar gravação) |
| P-26 | O kit só tem o tópico `produto_cadastrado`. Onde publicar a alteração e a exclusão de produto, exigidas pelo F5? Opções: criar os tópicos `produto_atualizado` e `produto_excluido`, ou publicar os três tipos em um tópico único de produto, o que garante a ordem por `produtoId` | Infraestrutura |
| P-27 | Logística/Transporte precisa do tipo de transporte (F6, F7), mas não consome `produto_cadastrado` no catálogo do kit e consome `pedido_criado`, que não traz esse dado. Logística passa a consumir `produto_cadastrado`, ou o `pedido_criado` passa a levar o tipo de transporte? | Grupo de Logística/Transporte; Mercado, Negociação/Leilão e Pedidos |
| P-28 | A tabela `fornecimentos.fornecimento` do kit só tem `quantidade_disponivel`. A reserva exige `quantidade_reservada` e um registro de reservas por pedido (para liberar ou dar baixa na quantidade certa). O DDL é do grupo de Banco de Dados. Proposta testada em [`banco/`](banco/README.md) | Grupo de Banco de Dados |
| P-29 | Quando o pedido é criado? O professor diz que o estoque é bloqueado ao entrar em leilão ou negociação (F6, 8:19; F7, 21:03). No kit, o `pedidos-service` cria o pedido a partir de `negociacao_fechada`, ou seja, depois da negociação. Nesse caso o estoque não fica bloqueado durante o leilão | Professor; Mercado, Negociação/Leilão e Pedidos |
| P-30 | O professor diz que o comprador pode cadastrar produtos (F7, 1:17 a 1:49). O guia do kit (seção 7.2) diz que o comprador só cria demandas e dá lances. Se o Grupo de Teste seguir o guia, vai esperar 403 quando um comprador cadastrar produto | Infraestrutura, Autenticação, Teste |
| P-31 | O professor diz que uma empresa pode ter os três perfis (F6, 1:34). No banco do kit, `empresa.tipo` e `usuario.perfil` têm um único valor, e o token leva um único `perfil`. Como uma empresa fornecedora e compradora opera? | Grupo de Autenticação, Banco de Dados |
| P-32 | No script do banco do kit, as permissões dos usuários `svc_*` são concedidas antes da criação das tabelas. Teste com PostgreSQL 16 confirmou que `svc_fornecimentos` recebe `permission denied` ao ler a própria tabela. Os contêineres dos serviços também não recebem `DB_USER`, e a biblioteca comum usa `portal_admin`, que é superusuário, por padrão | Infraestrutura, Banco de Dados |
| P-33 | Divergências entre os arquivos do kit: o guia usa `produto_criado`, chave `produto_id` nos eventos de fornecimento e estoque, campo `version` no envelope e claim `empresa_id`. O `CONTRACTS.md`, o script de tópicos e o código usam `produto_cadastrado`, chave `fornecimentoId`, campo `eventVersion` e claim `empresaId`. Este documento segue o que está implementado | Infraestrutura |

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
- RFC 7807, Problem Details for HTTP APIs: https://datatracker.ietf.org/doc/html/rfc7807
- RFC 7519, JSON Web Token: https://datatracker.ietf.org/doc/html/rfc7519
- PostgreSQL 16, comando GRANT (privilégios valem só para objetos existentes) e ALTER DEFAULT PRIVILEGES: https://www.postgresql.org/docs/16/sql-grant.html e https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html
- Kit de integração do grupo de Infraestrutura: https://github.com/Printf-PedroCardoso/portal-b2b-kit-infra (commit `630515c`)

---

## Histórico de revisões

| Versão | Data | Descrição |
|---|---|---|
| 0.1 | 09/10/2026 | Rascunho inicial com base no enunciado, nos requisitos do professor e no diagrama de arquitetura |
| 0.2 | 09/10/2026 | Inclusão da lista de responsabilidades do grupo como fonte F1 e das orientações de Kafka como fonte F5. Origem de cada requisito passa a indicar a fonte exata. P-01 resolvida. P-05 e P-11 detalhadas |
| 0.3 | 09/10/2026 | Inclusão das transcrições das aulas 1 e 2 como fontes F6 e F7. Estoque passa a ter quantidade disponível e reservada, com reserva, liberação e baixa a partir de eventos de pedido (RF-13, RF-14, RF-19, RF-20, RN-06, RN-07, RNF-14, UC-03). Comprador e fornecedor podem cadastrar produtos (RN-08). Comprador consulta fornecimentos (RF-10). Perfis e autorização por perfil confirmados (RN-02, RN-04, RNF-03). Docker obrigatório (RNF-12). Requisitos de interface incluídos (RNF-15 a RNF-18). Novos critérios CA-10 a CA-14. P-02, P-07, P-14 e P-20 parcialmente resolvidas. Novas pendências P-22 a P-25 |
| 0.4 | 26/10/2026 | Inclusão do kit de infraestrutura (F8) e da relação final de grupos (F9). Atualização de interfaces, premissas, eventos, tópicos e chaves. Novos requisitos não funcionais RNF-19 a RNF-26 (padrão de API, RFC 7807, paginação, endpoints técnicos, pool de conexões, usuário do banco, metas de desempenho e serviços sem estado em memória). Novas regras RN-10 e RN-11. Novos critérios CA-15 a CA-19. Pendências P-04, P-14, P-17, P-18, P-19, P-22, P-23 e P-24 resolvidas. Novas pendências P-26 a P-33. Correção da tabela de requisitos funcionais, que tinha linhas fora da tabela na versão 0.3 |
