# SDK de Plugins

Este módulo define o SDK para plugins, pontos de extensão e ferramentas de instalação.

## Pontos de extensão

Os pontos de extensão padrão estão em `plugins.sdk.DEFAULT_EXTENSION_POINTS`. Cada ponto define um esquema mínimo de payload para validação.

## Catálogo interno

O catálogo interno fica em `data/plugins_catalog.json` e descreve plugins aprovados, com caminho de origem e checksum do manifesto.

## Instalação e atualização

Use `PluginManager` para instalar e atualizar plugins:

```python
from plugins import PluginManager

manager = PluginManager("data/plugins_catalog.json", "data/plugins_installed")
manager.install("example-echo")
manager.update("example-echo")
```

## Sandboxing

Os hooks são executados em subprocesso isolado (`python -I`) com limites de CPU/memória, bloqueio de rede/subprocess e escrita em disco por monkeypatch.
A sandbox é defensiva, mas não substitui isolamento de SO (como containers ou seccomp).
