# Muse Spark 1.3 test — round trip with two tools

Checks that the model picks the right tool, receives its result in a `tool` message, then uses it in its final answer. Complements `docs/muse-spark-tool-call-results.md` (first call only). The returned values are fictional and impossible to guess.

- **Run date:** 2026-10-27 19:31 UTC
- **Model:** `muse-spark-1.3` — `max_tokens` = 4000
- **Tools exposed:** `get_filiere_cutoff` (returns 13.87), `get_bursary_amount` (returns 417)

## Summary

| Criterion | Result |
| --- | --- |
| Round trip, right tool + value in the final answer | **5/5** |
| Choice of the other tool (grant), 1 run | ✅ |
| Question without a tool: no call, 1 run | ✅ |
| Chained calls (question needing two tools) | requested in parallel in a single turn (no chaining); answer containing both values: ✅ |

## Cost

Total tokens used: 10465 input, 3777 output (8 conversations). This script does not record the credit rate, so the cost in credits is not given here.

## Limits of this test

- Two tools only, one question per tool; 5 attempts for the round trip, only 1 for each other case: this is not a statistical measurement.
- Fixed tool values; the test covers neither tool errors nor invalid arguments.
- PathProof's real tools (`lookup_filieres`...) are not tested here.

## Raw outputs

### Round trip, run 1

- Question: Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Tools called: ['get_filiere_cutoff']
- Tokens: 1394 input, 638 output
- Result: ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je récupère le seuil de classement pour la filière Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Round trip, run 2

- Question: Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Tools called: ['get_filiere_cutoff']
- Tokens: 1389 input, 355 output
- Result: ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je recherche le seuil pour la Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Round trip, run 3

- Question: Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Tools called: ['get_filiere_cutoff']
- Tokens: 1388 input, 407 output
- Result: ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je recherche le seuil pour Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Round trip, run 4

- Question: Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Tools called: ['get_filiere_cutoff']
- Tokens: 1392 input, 455 output
- Result: ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je récupère le seuil pour la filière Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Round trip, run 5

- Question: Quel est le seuil de moyenne de classement pour la filière Médecine ?
- Tools called: ['get_filiere_cutoff']
- Tokens: 1392 input, 383 output
- Result: ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je récupère le seuil pour la filière Médecine.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le seuil de moyenne de classement pour la filière **Médecine** est de **13.87**.",
    "tool_calls": []
  }
]
```

### Other tool (grant)

- Question: Quel est le montant mensuel de la bourse pour la série D ?
- Tools called: ['get_bursary_amount']
- Tokens: 1373 input, 658 output
- Result: ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je vérifie le montant pour la série D.",
    "tool_calls": [
      {
        "name": "get_bursary_amount",
        "arguments": "{\"serie\":\"D\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Le montant mensuel de la bourse pour la série D est de **417 FCFA**.",
    "tool_calls": []
  }
]
```

### Question without a tool

- Question: Combien font 7 fois 8 ?
- Tools called: none
- Tokens: 622 input, 326 output
- Result: ✅

```json
[
  {
    "finish_reason": "stop",
    "content": "7 fois 8 font **56**.\n",
    "tool_calls": []
  }
]
```

### Chained calls

- Question: Donne-moi le seuil de moyenne de classement de Médecine ET le montant mensuel de la bourse pour la série D.
- Tools called: ['get_filiere_cutoff', 'get_bursary_amount']
- Tokens: 1515 input, 555 output
- Result: ✅

```json
[
  {
    "finish_reason": "tool_calls",
    "content": "Je récupère pour vous le seuil Médecine et la bourse série D.",
    "tool_calls": [
      {
        "name": "get_filiere_cutoff",
        "arguments": "{\"filiere\":\"Médecine\"}"
      },
      {
        "name": "get_bursary_amount",
        "arguments": "{\"serie\":\"D\"}"
      }
    ]
  },
  {
    "finish_reason": "stop",
    "content": "Voici les informations demandées :\n\n* **Seuil de moyenne de classement de Médecine :** **13.87**\n* **Montant mensuel de la bourse pour la série D :** **417 FCFA**",
    "tool_calls": []
  }
]
```

## Rerun

```bash
python scripts/test_muse_roundtrip.py
```
