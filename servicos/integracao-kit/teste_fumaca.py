"""Teste de fumaça dos serviços de Fornecimento e Produtos no ambiente do kit.

Passa pelo HTTP das quatro instâncias, pelo Redpanda real, pelo PostgreSQL real e
pela validação RS256 com JWKS. Instruções em README.md, nesta pasta.

Uso:
  python teste_fumaca.py gerar-chaves PASTA   # cria PASTA/privada.pem e PASTA/.well-known/jwks.json
  python /t/teste_fumaca.py executar          # num contêiner da rede portal-net, com PASTA montada em /t
"""

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
import uuid

import jwt

KID = "teste-integracao"
P1, P2 = "http://app1-produtos:8102", "http://app2-produtos:8102"
F1, F2 = "http://app1-fornecimentos:8103", "http://app2-fornecimentos:8103"
BROKER = "rp-0:9092"


def gerar_chaves(pasta: str) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jwt.algorithms import RSAAlgorithm

    destino = pathlib.Path(pasta)
    (destino / ".well-known").mkdir(parents=True, exist_ok=True)
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    (destino / "privada.pem").write_bytes(privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    jwk = json.loads(RSAAlgorithm.to_jwk(privada.public_key()))
    jwk.update({"kid": KID, "use": "sig", "alg": "RS256"})
    (destino / ".well-known" / "jwks.json").write_text(json.dumps({"keys": [jwk]}), encoding="utf-8")
    print(f"chaves de teste criadas em {destino}")


def token(escopo: str | None = "SUPPLIER", tenant: str | None = "EMP-1") -> str:
    """Token no formato do Identity-Service: iss, aud e, depois do switch-context, empresa e escopo."""
    claims = {"sub": "USR-1", "iss": "identity-service", "aud": "b2b-platform", "exp": int(time.time()) + 600}
    if tenant is not None:
        claims["tenant_id"] = tenant
    if escopo is not None:
        claims["active_scope"] = escopo
    return jwt.encode(claims, pathlib.Path("/t/privada.pem").read_text(), algorithm="RS256", headers={"kid": KID})


def http(metodo, url, corpo=None, tok=None, cabecalhos=None):
    h = {"Content-Type": "application/json", **(cabecalhos or {})}
    if tok:
        h["Authorization"] = "Bearer " + tok
    dados = json.dumps(corpo).encode() if corpo is not None else None
    requisicao = urllib.request.Request(url, data=dados, headers=h, method=metodo)
    try:
        with urllib.request.urlopen(requisicao, timeout=10) as r:
            return r.status, json.loads(r.read() or b"null"), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null"), {k.lower(): v for k, v in e.headers.items()}


def esperar(condicao, segundos=40, passo=0.5):
    fim = time.time() + segundos
    while time.time() < fim:
        try:
            valor = condicao()
        except Exception:
            valor = None
        if valor:
            return valor
        time.sleep(passo)
    return None


def executar() -> int:
    from confluent_kafka import Consumer, Producer

    resultados = []

    def verificar(nome, condicao):
        resultados.append(bool(condicao))
        print(("OK   " if condicao else "FALHA"), nome)

    for url in (P1, P2, F1, F2):
        verificar(f"prontidão de {url}", http("GET", url + "/health/ready")[0] == 200)
    falso = jwt.encode({"sub": "x"}, "segredo-compartilhado", algorithm="HS256")
    s, c, _ = http("GET", P1 + "/api/v1/produtos", tok=falso)
    verificar("token HS256 recusado (401 TOKEN_INVALIDO)", s == 401 and c["codigo"] == "TOKEN_INVALIDO")
    s, c, _ = http("GET", P1 + "/api/v1/produtos", tok=token(None, None))
    verificar("token do login, sem empresa, recusado (403 CONTEXTO_NAO_SELECIONADO)", s == 403 and c["codigo"] == "CONTEXTO_NAO_SELECIONADO")

    corr = "fumaca-" + uuid.uuid4().hex[:8]
    s, produto, h = http("POST", P1 + "/api/v1/produtos", {
        "nome": "Leite integral", "categoria": "LATICINIOS", "unidade": "CX", "tipo_transporte": "REFRIGERADO",
        "peso_unitario_kg": 12.35}, token(), {"X-Correlation-Id": corr})
    verificar("cadastro de produto na instância app1 (201, mesmo X-Correlation-Id)", s == 201 and h.get("x-correlation-id") == corr)
    if s != 201:
        print("RESULTADO: interrompido, o cadastro do produto falhou:", s, produto)
        return 1
    pid = produto["produto_id"]
    verificar("consulta do produto na instância app2", http("GET", f"{P2}/api/v1/produtos/{pid}", tok=token("BUYER"))[1] == produto)

    oferta = {"produto_id": pid, "preco": 5.5, "quantidade_disponivel": 100, "origem": {"cidade": "Goiânia", "uf": "GO"}}

    def cadastrar_fornecimento():
        s, c, _ = http("POST", F2 + "/api/v1/fornecimentos", oferta, token())
        return c if s == 201 else None

    inicio = time.time()
    fornecimento = esperar(cadastrar_fornecimento)
    verificar(f"produto chegou ao fornecimentos pelo Kafka em {time.time() - inicio:.1f}s", fornecimento)
    if not fornecimento:
        print("RESULTADO: interrompido, o fornecimentos não recebeu o produto_cadastrado")
        return 1
    fid = fornecimento["fornecimento_id"]

    produtor = Producer({"bootstrap.servers": BROKER, "acks": "all"})

    def publicar(topico, payload, chave):
        envelope = {"eventId": str(uuid.uuid4()), "eventType": topico, "eventVersion": "1.0",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": "teste-fumaca",
                    "correlationId": corr, "aggregateId": chave, "payload": payload}
        produtor.produce(topico, key=chave, value=json.dumps(envelope))
        produtor.flush(10)

    def saldo(disponivel, reservada):
        c = http("GET", f"{F1}/api/v1/fornecimentos/{fid}", tok=token("BUYER"))[1]
        return c["quantidade_disponivel"] == disponivel and c["quantidade_reservada"] == reservada

    pedido = "PED-" + uuid.uuid4().hex[:8]
    publicar("pedido_criado", {"pedidoId": pedido, "fornecimentoId": fid, "produtoId": pid, "fornecedorId": "EMP-1",
                               "quantidade": 4, "status": "CRIADO"}, pedido)
    verificar("pedido_criado reservou 4 (disponível 96, reservada 4)", esperar(lambda: saldo(96, 4)))
    publicar("pedido_atualizado", {"pedidoId": pedido, "fornecimentoId": fid, "status": "CANCELADO"}, pedido)
    verificar("pedido_atualizado CANCELADO liberou a reserva (disponível 100, reservada 0)", esperar(lambda: saldo(100, 0)))

    consumidor = Consumer({"bootstrap.servers": BROKER, "group.id": "fumaca-" + uuid.uuid4().hex,
                           "auto.offset.reset": "earliest"})
    consumidor.subscribe(["produto_cadastrado", "fornecimento_criado", "estoque_atualizado"])
    vistos = {}
    fim = time.time() + 30
    while time.time() < fim and len(vistos) < 4:
        m = consumidor.poll(1.0)
        if m is None or m.error():
            continue
        e = json.loads(m.value())
        if e.get("correlationId") == corr or e.get("aggregateId") in (pid, fid):
            vistos[(m.topic(), e["payload"].get("operacao", ""))] = (m.key().decode(), e)
    consumidor.close()
    pc = vistos.get(("produto_cadastrado", ""))
    verificar("produto_cadastrado no Redpanda com chave, correlationId e pesoUnitarioKg",
              pc and pc[0] == pid and pc[1]["correlationId"] == corr and pc[1]["payload"]["pesoUnitarioKg"] == 12.35)
    fc = vistos.get(("fornecimento_criado", ""))
    verificar("fornecimento_criado no Redpanda com origem {cidade, uf}",
              fc and fc[0] == fid and fc[1]["payload"]["origem"] == {"cidade": "Goiânia", "uf": "GO"})
    verificar("estoque_atualizado com RESERVA e LIBERACAO no Redpanda",
              ("estoque_atualizado", "RESERVA") in vistos and ("estoque_atualizado", "LIBERACAO") in vistos)

    falhas = resultados.count(False)
    print("RESULTADO:", "TUDO OK" if falhas == 0 else f"{falhas} FALHA(S)")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "gerar-chaves":
        gerar_chaves(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "executar":
        sys.exit(executar())
    else:
        print(__doc__)
        sys.exit(2)
