# DandaraData Next — V3 experimental

**Pipeline modular de entity linking determinístico, sem NER e sem aprendizado de máquina.**

Esta é uma **primeira implementação experimental** e independente. **Não substitui o DandaraData original nem a auditoria histórica.** Os nomes extraídos da FCP são candidatos de busca, não prova automática de que cada fragmento seja uma CRQ distinta. As saídas incluem propostas **não auditadas**; nunca trate essas propostas automaticamente como TP.

## 1. O que vem neste ZIP

- Código Python modular em `src/dandaradata/`, config JSON e testes com `pytest`.
- As duas entradas históricas já incluídas em `data/raw/`: `artigos_atual_ofc.csv` (636 artigos) e `crqrs_atual_ofc.csv` (3.478 registros).
- Referências históricas em `data/reference/`: saída original, validação e falsos negativos. **Esses documentos não são usados para decidir as correspondências da V3**; servem apenas para comparação posterior.
- Pasta `data/outputs/` inicialmente vazia. Cada execução cria uma subpasta diferente.
- Arquivos `.vscode/` opcionais para configuração da interface.

Atenção: os insumos históricos podem conter informações destinadas apenas ao trabalho de laboratório. Controle o compartilhamento do ZIP.

## 2. Preparar no Windows 11 + VS Code

1. Instale **Python 3.11 ou 3.12**, VS Code e a extensão oficial **Python** para VS Code.
2. Extraia o ZIP. No VS Code, use **Arquivo > Abrir Pasta...**, selecionando a pasta `dandaradata-next` (não a pasta superior).
3. Abra **Terminal > Novo Terminal**, que normalmente inicia o PowerShell.
4. Confirme que o Python funciona:

   ```powershell
   py -3.11 --version
   ```

   Se você usa Python 3.12, substitua `-3.11` por `-3.12`.

5. Crie um ambiente virtual na pasta do projeto:

   ```powershell
   py -3.11 -m venv .venv
   ```

6. **Não é necessário ativar o venv** para instalar e executar. A maneira mais robusta no PowerShell é usar diretamente o Python dentro dele:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m pip install -e .
   ```

   `-e .` registra o pacote local em modo editável: as alterações feitas em `src/` são usadas na próxima execução sem reinstalar.

7. No VS Code, `Ctrl+Shift+P` → **Python: Select Interpreter** → escolha `.venv\Scripts\python.exe`.

8. Rode os testes:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   ```

9. Rode o experimento:

   ```powershell
   .\.venv\Scripts\python.exe -m dandaradata --config config/experiment.json
   ```

   Alternativamente, após selecionar o interpretador: `python -m dandaradata --config config/experiment.json`.

### Se preferir ativar o ambiente

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest -q
python -m dandaradata --config config/experiment.json
```

Se o PowerShell bloquear o script de ativação, **use os comandos com `.\.venv\Scripts\python.exe`** acima. Não é necessário alterar a política de execução do Windows. No terminal CMD, a ativação opcional é `.venv\Scripts\activate.bat`.

Se `py` não existir, use a instalação do Python disponível como `python -m venv .venv`, confirmando primeiro que `python --version` mostra Python 3.11 ou mais recente.

## 3. O que é um experimento e por que JSON?

As **duas entradas continuam exatamente as mesmas**. Experimentos mudam **parâmetros da decisão** sem editar o código e sem mudar as bases históricas. Exemplo: executar uma política conservadora (`minimum_score=7`) versus permissiva (`minimum_score=5`), verificando o efeito nas novas relações.

Em `config/experiment.json`:

```json
"matching": {
  "minimum_name_length": 3,
  "minimum_score": 5,
  "require_geographic_evidence": true,
  "homonym_margin": 2,
  "weights": {"name": 3, "municipality": 4, "state": 1, "context": 1, "cooccurrence": 2, "nested_only_penalty": 3}
}
```

Esses pesos são **hipóteses experimentais**, não probabilidades nem parâmetros treinados. Não há calibração científica desses valores nesta primeira versão. O valor de `minimum_score` controla quantas associações são propostas; a qualidade precisa ser validada.

Para testar parâmetros diferentes:

1. Use a configuração já incluída `config/experiment_conservador.json`, ou copie `config/experiment.json` para criar uma nova.
2. Na configuração conservadora de exemplo, `experiment.run_id` já vale `v3_conservador` e `matching.minimum_score` vale `7`.
3. Rode `python -m dandaradata --config config/experiment_conservador.json`.
4. Compare as pastas `data/outputs/v3_primeira_execucao/` e `data/outputs/v3_conservador/`.

**Mudar o algoritmo** (por exemplo, substituir uma regra de hierarquia) continua exigindo modificar código, criar testes e documentar a mudança. O JSON não é uma linguagem mágica que gera lógica nova.

## 4. O que são os resultados intermediários?

Eles são **tabelas geradas automaticamente em cada execução**, somente para explicar e auditar o caminho até a saída. Você não precisa construir manualmente um super-DataFrame nem preparar uma terceira planilha.

| Arquivo em `data/outputs/<run_id>/` | Para que serve |
|---|---|
| `catalogo_candidatos.csv` | Registra o nome derivado da FCP, ID administrativo, ID comunitário interno e situação da identidade |
| `mencoes_detectadas.csv` | Guarda o termo encontrado, artigo, coluna, início/fim na coluna original e trecho de contexto |
| `decisoes_entity_linking.csv` | Registra pontuação, regras aplicadas, evidências JSON e decisão proposta/revisar/rejeitada |
| `relacoes_propostas.csv` | Resultado relacional `UT + identidade candidata` **não auditado** |
| `artigos_final_v3_teste.csv` | Visão por artigo com candidatas propostas; útil para inspeção, **não é a base científica final validada** |
| `comparacao_administrativa.csv` | Compara V3 × saída histórica por `UT + processo FCP` |
| `resumo_execucao.json` | Quantidades e hashes da configuração e das duas entradas |
| `config_utilizada.json` | Cópia da configuração exata aplicada à execução |

Todos ficam na **subpasta do experimento**, não no código. Normalmente só é preciso olhar `relacoes_propostas.csv` e `resumo_execucao.json`; os demais ajudam a investigar casos suspeitos.

## 5. Distinção fundamental entre registro e comunidade

- A **linha FCP** tem `Nº PROCESSO NA FCP` e `Nº DE CRQ`.
- Cada **fragmento separado** vira um candidato de busca, mas não automaticamente uma CRQ certificada.
- Quando `Nº DE CRQ` coincide com o número de nomes candidatos razoáveis, o sistema gera **identidades provisórias** e registra `STATUS_IDENTIDADE=INDIVIDUALIZACAO_PROVISORIA`. Essa coincidência não valida individualmente as identidades.
- Quando `Nº DE CRQ=1`, partes do nome são tratadas como **variantes de uma mesma identidade interna**.
- Em agregações sem individuação, usa `REGISTRO_AGREGADO_NAO_INDIVIDUALIZADO`. Nunca expande Kalunga em 39 relações automaticamente.
- O ID gerado pela V3 (`FCP-...`, `GRUPO-...`) é **interno**, não um identificador oficial e nem uma prova de identidade individual.
- O programa apenas **propõe** vínculos: evidência textual e geográfica não demonstra sozinha que a comunidade foi *objeto do estudo*, e não apenas mencionada.

### Exemplo de rastreabilidade

O artigo 584 menciona `Vila União/Campina` e o registro FCP `01420.001847/2006-27` tem duas CRQs. A geração cria duas identidades **provisórias** e preserva as respectivas menções; a decisão explicará quais critérios textuais e geográficos foram aplicados. A homonímia com o processo isolado de Campina é registrada para revisão, sem tratar automaticamente os dois processos como a mesma comunidade.

## 6. Avaliação científica e limites atuais

Esta versão é **uma plataforma experimental inicial**. Não use os resultados para declarar precisão, recall ou F1 da V3 antes de auditar novas relações. `comparacao_administrativa.csv` mostra somente entradas/saídas por processo. A auditoria anterior foi realizada na unidade `UT + registro FCP` e **não é padrão-ouro suficiente para todas as relações `UT + comunidade certificada`**.

Ainda faltam, para uma versão científica consolidada: catálogo validado de identidades entre processos (caso Castelo), regra robusta para grupos administrativamente agregados, critérios empíricos de classificação de objeto do estudo versus menção incidental, validação de homônimos e avaliação em referência auditada na unidade comunitária.

## 7. Estrutura do código

- `ingestion.py`: valida colunas e lê as duas entradas.
- `fcp_catalog.py`: separa candidatos e atribui identidades internas com status.
- `normalization.py`: normalização Unicode com preservação dos offsets originais.
- `mention_detection.py`: procura expressões nos metadados sem NER.
- `entity_linking.py`: soma evidências e resolve/retém ambiguidades.
- `consolidation.py`: reúne propostas por identidade candidata, não somente por processo.
- `evaluation.py`: compara contra a saída histórica sem inventar TP/FP.
- `pipeline.py`: coordena, grava artefatos e hashes para reprodutibilidade.
- `__main__.py`: interface de linha de comando.

## 8. Controle de qualidade

Use `python -m pytest -q` após cada mudança. Evite ajustar pesos olhando somente os exemplos que já conhecemos (584, 550 etc.). Separe casos auditados de casos de validação independente para testar generalização.

A pasta `data/outputs/` guarda os arquivos; `src/` guarda a lógica; `config/` guarda a política da execução. **Esses elementos são independentes das duas planilhas de entrada.**

## 9. Resultado técnico da primeira execução (não é métrica de qualidade)

O projeto foi testado com os dados do laboratório e **9 testes automatizados passaram**. Na política inicial foram geradas 149 relações propostas (147 pares administrativos distintos), contra os 199 pares da saída original. A comparação administrativa preservou 139 pares, adicionou 8 e removeu 60. **Entre os 60 removidos há 25 TP históricos**. A V3 atual, portanto, **ainda não demonstrou superioridade nem está pronta para substituir a V1**. Esses números servem para depurar o novo pipeline e suas regras de filtragem.

No artigo 584, as candidatas Vila União e Campina do processo composto são preservadas como **identidades provisórias**; a Campina do processo isolado fica marcada para revisão. O artigo 550 preserva Pedro Cubas e Pedro Cubas de Cima. Esse comportamento localizado correto não valida o desempenho geral.

A base FCP contém um registro histórico sem número de processo (`TERRA SECA`, Barra do Turvo/SP); ele é mantido para inspeção, mas não se transforma em proposta administrativa confirmada.
