# Interface Descriptions Added

## Date: 2025-01-19

---

## Summary

Brief, clear descriptions have been added to every choice/option in the GUI interface to help users understand what each option does.

---

## Descriptions Added

### 1. File/Folder Selection

#### Pasta (análise automática)
**Description**: `→ Analisa todos os Excel na pasta e escolhe o melhor`

**Explanation**: When you select a folder, the system automatically analyzes all Excel files and recommends the best one based on quality metrics.

#### OU Ficheiro específico
**Description**: `→ Seleciona um ficheiro Excel específico manualmente`

**Explanation**: Alternative option to manually select a specific Excel file instead of using automatic folder analysis.

#### Analisar Pasta
**Description**: `→ Analisa qualidade dos ficheiros e mostra recomendações`

**Explanation**: Button that triggers analysis of all Excel files in the folder and displays quality recommendations.

---

### 2. Output

#### Output
**Description**: `→ Ficheiro Excel de saída com resultados`

**Explanation**: The output Excel file where all selected documents and results will be saved.

---

### 3. Selection Modes

#### Modo A: 1/Área
**Description**: `→ 1/Área - Um melhor documento por área (diversidade máxima)`

**Explanation**: Selects exactly one best document per area, maximizing diversity across different research areas.

#### Modo B: Quotas
**Description**: `→ Quotas - Distribui N documentos proporcionalmente por área`

**Explanation**: Distributes N documents proportionally across areas based on how many documents each area has.

#### Modo C: Global Capped
**Description**: `→ Global Capped - Top N global com limite por área`

**Explanation**: Selects top N documents globally, but with a maximum limit per area (uses "Max por Área" parameter).

#### Modo D: Top N Fixo/Área
**Description**: `→ Top N Fixo/Área - N documentos por área (recomendado)`

**Explanation**: Selects exactly N documents per area (recommended mode for balanced selection).

---

### 4. Parameters

#### N (Total ou por Área)
**Description**: `→ Número de documentos a selecionar (total ou por área conforme modo)`

**Explanation**: 
- In Mode A: Not used (always 1 per area)
- In Mode B: Total number to distribute proportionally
- In Mode C: Total number globally
- In Mode D: Number per area

#### Max por Área (Modo C)
**Description**: `→ Limite máximo de documentos por área no Modo C`  
**Additional**: `→ Usado apenas no Modo C (Global Capped)`

**Explanation**: Maximum number of documents allowed per area when using Mode C. Prevents one area from dominating the selection.

---

### 5. Options (Checkboxes)

#### Seleção Automática
**Description**: `→ Analisa pasta e escolhe automaticamente o melhor ficheiro e sheet`

**Explanation**: When enabled, automatically analyzes the folder and selects the best Excel file and sheet based on quality metrics. No manual selection needed.

#### Agrupar sub-áreas em Macro-Áreas
**Description**: `→ Simplifica áreas específicas (ex: 'Marine Biology' → 'Biology & Medicine')`

**Explanation**: Groups specific sub-areas into broader macro-areas. For example:
- "Marine Biology" → "Biology & Medicine"
- "Computer Science" → "Computer Science"
- "Applied Mathematics" → "Mathematics"

This reduces the number of unique areas and makes selection more manageable.

#### Usar Métricas de Rede
**Description**: `→ Inclui métricas de rede (PageRank, Betweenness) do sheet 'Network Metrics'`

**Explanation**: If the Excel file has a "Network Metrics" sheet, this option merges network analysis metrics (PageRank, Betweenness centrality) into the main dataset for more sophisticated ranking.

#### Gerar Listas de Leitura e Download
**Description**: `→ Cria listas adicionais: Core (importantes), Recent (recentes), Bridge (pontes), Diversity (diversos)`

**Explanation**: Generates four additional reading lists:
- **Core**: Most important documents (high citation impact + PageRank)
- **Recent**: Most recent and highly used documents
- **Bridge**: Documents with high betweenness (connect different areas)
- **Diversity**: Diverse selection across areas

---

### 6. Recommendations Area

#### Recomendação
**Description**: `→ Análise de qualidade e recomendações do sistema`

**Explanation**: Displays the system's analysis results including:
- Recommended file name
- Recommended sheet name
- Quality score (0-100%)
- Number of records
- Which fields are present (title, DOI, year, author, area, metrics)

---

## Visual Layout

```
┌─────────────────────────────────────────────────────────┐
│ Pasta (análise automática):                             │
│ → Analisa todos os Excel na pasta e escolhe o melhor   │
│ [________________________] [Buscar Pasta]               │
│                                                          │
│ OU Ficheiro específico:                                 │
│ → Seleciona um ficheiro Excel específico manualmente     │
│ [________________________] [Buscar Ficheiro]            │
│                                                          │
│ [Analisar Pasta] → Analisa qualidade e mostra recomendações│
│                                                          │
│ Recomendação:                                            │
│ → Análise de qualidade e recomendações do sistema        │
│ [Text area with recommendations]                        │
│                                                          │
│ Modo de Seleção:                                         │
│ ○ A: 1/Área → 1/Área - Um melhor documento por área    │
│ ○ B: Quotas → Quotas - Distribui N proporcionalmente    │
│ ○ C: Global Capped → Top N global com limite por área  │
│ ● D: Top N Fixo/Área → N documentos por área (recomendado)│
│                                                          │
│ N: [3] → Número de documentos a selecionar             │
│ Max por Área: [3] → Limite máximo por área (Modo C)    │
│                                                          │
│ ☑ Seleção Automática → Analisa e escolhe automaticamente│
│ ☑ Agrupar Macro-Áreas → Simplifica áreas específicas   │
│ ☑ Usar Métricas de Rede → Inclui PageRank, Betweenness │
│ ☐ Gerar Listas → Cria Core, Recent, Bridge, Diversity  │
└─────────────────────────────────────────────────────────┘
```

---

## Benefits

1. **User Understanding**: Users immediately understand what each option does
2. **Reduced Errors**: Clear descriptions prevent incorrect selections
3. **Better UX**: No need to guess or read documentation
4. **Contextual Help**: Descriptions appear right next to options
5. **Professional Appearance**: Gray text provides subtle guidance

---

## Format

All descriptions follow this format:
- **Location**: Right next to the option (inline)
- **Style**: Gray text, smaller font (Arial 8)
- **Prefix**: Arrow symbol (→) for visual connection
- **Length**: Brief (one line when possible)

---

## Example Usage

When a user sees:
```
☑ Seleção Automática → Analisa pasta e escolhe automaticamente o melhor ficheiro e sheet
```

They immediately understand:
- What the option does (automatic selection)
- How it works (analyzes folder)
- What it chooses (best file and sheet)

---

*Interface descriptions added: 2025-01-19*

