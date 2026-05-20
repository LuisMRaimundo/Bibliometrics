# Manual do `select_texts_gui.py`

## Objetivo
Selecionar **textos mais relevantes** a partir do Excel do núcleo (folha `Records+Metrics`), usando a métrica **MNCS** (`cf`/`c_f`) já calculada a montante. O script **não recalcula métricas**; apenas lê, filtra, ordena e exporta seleções.

---

## Pré-requisitos
- Python 3.x com `pandas` e `openpyxl`.
- Excel do núcleo (ex.: `OpenAlex_uniform_metrics_pro.xlsx`) com a(s) folha(s) esperadas.

---

## Entradas e saídas
- **Entrada**: ficheiro `.xlsx` com a folha **`Records+Metrics`**.
- **Saídas**:
  - **Modo A/B/C** (individual): um `.xlsx` com a seleção (ex.: `*_topA.xlsx`).
  - **Pacote** (**bundle**): um `.xlsx` com **quatro separadores** — `TopA`, `TopB`, `TopC` e **`Lista`** (coluna única com `ano; título; DOI`, cada célula é *hyperlink* para o DOI).

---

## Campos da GUI (linha a linha)
1. **Excel** – caminho para o `*_metrics_pro.xlsx` (fonte dos dados).
2. **Folha** – por defeito `Records+Metrics` (alterar só se o ficheiro usar outro nome).
3. **Coluna de área (opcional)** – se vazio, o script tenta: `domain_label` → `domain_id` → `community_label` → `community`.
   - **Necessária** para **Modos A e B**; sem área o script interrompe.
   - Em **bundle**, se faltar, A e B degradam para *top global* (mesmo resultado que C sem limite).
4. **Gerar pacote A+B+C + Lista** – cria um **único Excel** com `TopA`, `TopB`, `TopC` e `Lista`.
5. **Modo (se não usar pacote)** – escolher **A**, **B** ou **C**:
   - **A – 1 por área**: escolhe o melhor `cf` em cada área; ordena por `cf` e corta a *n* (maximiza **diversidade**).
   - **B – quotas proporcionais** (*maiores restos*): reparte *n* por áreas proporcionalmente ao seu tamanho; dentro de cada quota, escolhe por `cf` (balanceia **representatividade** por área).
   - **C – top global com teto por área**: ordena globalmente por `cf` e aplica **limite** por área (**Máx./área**) (privilegia **excelência** com **controlo de concentração**).
6. **Total (n)** – número total de textos na seleção final (aplica-se a A, B, C e bundle).
7. **Máx./área (modo C)** – teto de itens por área **no modo C** (e na folha `TopC` do bundle).
8. **Usar métricas de rede (pagerank/betweenness)** – se existir a folha `Network Metrics`, o script faz *merge* por `idx` e usa estas métricas **apenas como desempate** (não alteram o critério principal).
9. **Folha rede** – nome da folha com métricas de rede (por defeito `Network Metrics`).
10. **Apenas focais** – se existir `is_focal`, mantém **só** os focais (`==1`).
11. **Excluir retratados** – se existir `is_retracted`, remove registos retratados (`!=1`).
12. **Ficheiro de saída (opcional)** – nome do `.xlsx` final; se vazio, o script gera automaticamente: `*_topA.xlsx`, `*_topB.xlsx`, `*_topC.xlsx` ou `*_topABC.xlsx` (pacote).
13. **Executar / Fechar** – corre a seleção e grava; opção de abrir a pasta no fim.

---

## Significado bibliométrico das opções
### Métricas usadas
- **`cf`**: **MNCS** (citações normalizadas por campo/ano). Critério **principal** de relevância.
- **`c_use_window`** / **`c_use`**: **desempate** (preferência por impacto **recente** via janela).
- **`pagerank`** / **`betweenness`**: **desempate estrutural** (autoridade/ponte na rede); só se marcada a opção e existir a folha de rede.

**Ordem de decisão (descendente)**: `cf` → `c_use_window` → `c_use` → `pagerank` → `betweenness`.

### Modos
- **A (1 por área)** – cobertura mínima de todas as áreas; bom para *surveys* equilibrados.
- **B (quotas proporcionais)** – **representatividade** ao volume por área (método dos **maiores restos**).
- **C (top global + teto)** – maximiza **excelência normalizada** mantendo **diversidade controlada** por limite.

### Filtros
- **Apenas focais** – restringe ao **corpus base**.
- **Excluir retratados** – remove casos problemáticos.

### Área ausente
- **Modos A/B**: erro (impossível “por área”).
- **Bundle**: A/B tornam-se *top global*; C segue sem limite efetivo.

---

## Saída “Lista” (pacote)
Separador **`Lista`** com **uma única coluna**: `ano; título; DOI`. Cada célula é um **hyperlink** para o DOI (quando existe). Útil para **copiar/colar** rápido para relatórios ou e-mails.

---

## Exemplos de uso
### GUI
1. Abrir `select_texts_gui.py`.
2. Escolher `OpenAlex_uniform_metrics_pro.xlsx`.
3. Marcar **Gerar pacote A+B+C + Lista** → `n=10` → **Máx./área=3** → **Executar**.
   - Saída: `OpenAlex_uniform_metrics_pro_topABC.xlsx` com as quatro folhas.

### CLI
**Pacote completo:**
```bash
python select_texts_gui.py --xlsx ".\OpenAlex_uniform_metrics_pro.xlsx" --bundle -n 10 --max-per-area 3
```
**Apenas Modo C com impressão no ecrã:**
```bash
python select_texts_gui.py --xlsx ".\OpenAlex_uniform_metrics_pro.xlsx" --mode C -n 10 --max-per-area 3 --print
```

---

## Erros e diagnóstico (mensagens típicas)
- **Coluna 'cf' (ou 'c_f') não encontrada** – o Excel não contém MNCS; reexportar pelo núcleo.
- **Modos A/B sem área** – definir “Coluna de área” ou gerar o Excel com domínios.
- **Sem folha `Network Metrics`** – a opção de rede pode estar ativa; o desempate estrutural simplesmente **não** se aplica.

---

## Critérios de qualidade a verificar
- **Ordenação**: `cf` estritamente **descendente** (monotónica).
- **A**: exatamente **1 por área**.
- **B**: distribuição por área **aprox. proporcional** ao tamanho do campo no corpus.
- **C**: **nenhuma área** excede **Máx./área**.
- **Lista**: células no formato `ano; título; DOI` com link ativo.
