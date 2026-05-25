# Documentacao de Avaliacoes

Esta documentacao cobre as avaliacoes apos uma viagem concluida.

## Papel das avaliacoes

As avaliacoes ajudam cliente, empresa e motorista a construir reputacao dentro
do CargoLink.

Regras principais:

- So e possivel avaliar depois da viagem estar `concluida`.
- Apenas participantes da viagem podem avaliar.
- Ninguem pode avaliar a si mesmo.
- O mesmo utilizador nao pode avaliar o mesmo participante duas vezes na mesma viagem.

## Criar avaliacao

```http
POST /ratings/trips/{trip_id}
```

Permissao:

```text
cliente dono da carga
empresa dona da viagem
motorista atribuido
admin
```

Body:

```json
{
  "rated_user_id": 12,
  "score": 5,
  "comment": "Entrega feita com cuidado e no prazo."
}
```

Campos:

- `rated_user_id`: utilizador avaliado.
- `score`: nota de 1 a 5.
- `comment`: comentario opcional.

Efeito:

- Cria linha em `ratings`.
- Atualiza `drivers.avaliacao_media`, se o avaliado for motorista.
- Atualiza `companies.avaliacao_media`, se o avaliado for empresa.
- Cria notificacao para o avaliado.
- Emite WebSocket `rating.created`.

## Listar avaliacoes da viagem

```http
GET /ratings/trips/{trip_id}
```

Retorna avaliacoes da viagem para participantes autorizados.

## Minhas avaliacoes recebidas

```http
GET /ratings/me/received
```

## Minhas avaliacoes feitas

```http
GET /ratings/me/given
```

## Evento realtime

Quando uma avaliacao e criada:

```json
{
  "type": "rating.created",
  "trip_id": 12,
  "load_id": 4,
  "rating": {
    "id": 9,
    "trip_id": 12,
    "rater_id": 8,
    "rated_user_id": 12,
    "score": 5,
    "comment": "Entrega feita com cuidado e no prazo.",
    "created_at": "2026-05-26T12:00:00"
  }
}
```

Tambem e enviada notificacao:

```text
notification_type = "rating.created"
```
