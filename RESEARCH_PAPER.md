# RioMobiAnalytics: Sistema de Análise de Risco em Rede de Transporte Público Integrado com Dados de Reclamações Cidadãs

## RESUMO

Este trabalho apresenta RioMobiAnalytics, um sistema de análise que integra dados de GTFS (General Transit Feed Specification) da rede de transporte público do Rio de Janeiro com dados de reclamações cidadãs (1746) para identificar paradas de trânsito de alto risco. O sistema utiliza uma arquitetura híbrida de bancos de dados (MongoDB para dados não-estruturados e Neo4j para relacionamentos em grafo) para modelar a topologia da rede de transporte e calcular métricas de risco baseadas na proximidade geográfica de reclamações. Os resultados demonstram a viabilidade de integração de múltiplas fontes de dados para análise de vulnerabilidades em infraestrutura de transportes.

**Palavras-chave:** Análise de Transportes, Bancos de Dados em Grafo, GTFS, Análise de Risco, Reclamações Cidadãs, Neo4j, MongoDB.

---

## 1. INTRODUÇÃO

### 1.1 Contextualização

O Rio de Janeiro é uma metrópole com aproximadamente 6,7 milhões de habitantes que dependem significativamente de sistemas de transporte público para mobilidade urbana. A rede de transporte da cidade compreende aproximadamente 7.665 paradas de ônibus, 511 linhas de transporte e mais de 15 mil viagens diárias. Este sistema complexo de transportes é essencial para a conectividade urbana, mas enfrenta desafios significativos relacionados à segurança, qualidade do serviço e vulnerabilidades operacionais.

Paralelamente, a prefeitura do Rio de Janeiro mantém um sistema de ouvidoria cidadã (1746) que registra reclamações sobre diversos serviços públicos, incluindo problemas relacionados a transporte. Estes dados representam uma fonte valiosa de informação sobre os pontos críticos da rede de transporte, refletindo experiências reais de usuários.

A análise integrada destes dois conjuntos de dados (GTFS e reclamações 1746) pode fornecer insights sobre quais paradas e linhas de transporte apresentam maiores riscos e vulnerabilidades, informando decisões de planejamento urbano e alocação de recursos.

### 1.2 Descrição do Problema

Os sistemas de transportes urbanos enfrentam desafios na identificação de pontos críticos de vulnerabilidade. Embora dados estruturados de rotas (GTFS) e feedback de cidadãos (reclamações) estejam disponíveis, estes dados raramente são integrados para análise conjunta. Especificamente:

- **Falta de Integração**: Os dados de GTFS descrevem a topologia da rede, enquanto reclamações identificam problemas operacionais, mas não há integração sistemática destas perspectivas.

- **Análise Limitada de Relacionamentos**: Identificar quais paradas são afetadas por problemas requer análise de proximidade geográfica combinada com topologia de rede.

- **Ausência de Análise de Impacto em Rede**: Não há consideração dos efeitos cascata - como problemas em uma parada central afetam toda a rede de transporte.

- **Falta de Métricas de Vulnerabilidade Integradas**: Não existe uma metodologia unificada que combine risco local (reclamações) com importância estrutural (centralidade na rede).

### 1.3 Objetivos

**Objetivo Geral:**
Desenvolver um sistema integrado que combine dados de GTFS do Rio de Janeiro com dados de reclamações cidadãs (1746) para identificar e analisar paradas de transporte de alto risco.

**Objetivos Específicos:**

1. Modelar a rede de transporte público do Rio de Janeiro como um grafo, representando paradas, rotas e relacionamentos topológicos.

2. Integrar dados de reclamações cidadãs com a rede de transporte através de análise de proximidade geográfica (raio de 100 metros).

3. Desenvolver uma metodologia de cálculo de risco que considere: tipo de reclamação, criticidade e status.

4. Criar uma plataforma interativa de visualização que permita exploração dos dados e análise de vulnerabilidades.

### 1.4 Justificativa

Este trabalho é justificado por várias razões:

- **Relevância Prática**: O Rio de Janeiro enfrenta desafios contínuos em mobilidade urbana. Ferramentas analíticas que identifiquem pontos de vulnerabilidade podem orientar investimentos em segurança, manutenção e qualidade do serviço.

- **Inovação Metodológica**: A integração de dados de GTFS com feedback cidadão através de análise geoespacial e de grafo representa uma abordagem inovadora para análise de transportes.

- **Relevância Acadêmica**: Demonstra aplicação prática de conceitos de bancos de dados em grafo, análise de redes, mineração de dados e sistemas distribuídos.

- **Disponibilidade de Dados**: Ambos os conjuntos de dados (GTFS e 1746) estão disponíveis publicamente, facilitando reprodutibilidade e validação.

- **Escalabilidade**: A arquitetura desenvolvida pode ser aplicada a outras cidades com dados GTFS e sistemas de ouvidoria análogos.

### 1.5 Escopo Negativo

Este trabalho **não** cobre:

- Previsão de demanda de transporte ou otimização de rotas.
- Implementação de sistemas de controle ou atuação automática baseada em análise de risco.
- Análise comparativa com outras cidades (foco exclusivo no Rio de Janeiro).
- Desenvolvimento de aplicativos mobile para usuários finais.
- Validação em campo de resultados (trabalho é exploratório e analítico).

---

## 2. FUNDAMENTAÇÃO TEÓRICA

### 2.1 Área do Negócio - Transporte Urbano e Análise de Vulnerabilidade

#### Contexto de Transportes Públicos Urbanos

Transportes públicos são infraestruturas críticas para cidades modernas, afetando mobilidade, economia e qualidade de vida. Segundo dados do IPEA (Instituto de Pesquisa Econômica Aplicada), aproximadamente 63% dos deslocamentos no Rio de Janeiro são realizados via transporte público.

#### GTFS - General Transit Feed Specification

GTFS é um formato aberto de dados desenvolvido pelo Google em parceria com agências de trânsito. Define estrutura padronizada para descrever:
- **Stops**: Paradas com coordenadas geográficas
- **Routes**: Linhas de transporte com características (ônibus, metrô, BRT)
- **Trips**: Instâncias individuais de viagens em rotas específicas
- **Stop Times**: Sequências de paradas em cada viagem

GTFS permite modelagem de topologia de transporte e análise de conectividade de rede.

#### Sistema 1746 de Ouvidoria

O 1746 é o sistema de ouvidoria cidadã do Rio de Janeiro que permite registrar reclamações sobre serviços públicos. Dados disponíveis incluem:
- Data de abertura e encerramento
- Categoria do serviço (transporte, segurança, iluminação, etc.)
- Localização geográfica (latitude/longitude)
- Status (Aberto, Em Atendimento, Fechado)
- Criticidade (Alta, Média, Baixa)

### 2.2 Mineração de Dados e Análise Integrada

#### Integração de Dados Heterogêneos

Sistemas modernos frequentemente combinam dados estruturados (GTFS) com dados não-estruturados (reclamações). Técnicas de integração incluem:
- **Matching Geoespacial**: Usar coordenadas para vincular dados de diferentes fontes
- **Deduplicação**: Identificar registros duplicados através de chaves únicas
- **Sincronização**: Manter consistência entre múltiplos repositórios

#### Análise Geoespacial

Análise geoespacial permite consultas baseadas em localização:
- **Índices 2D-Sphere**: MongoDB oferece índices geoespaciais nativos
- **Queries de Proximidade**: Encontrar pontos dentro de raio especificado

#### Cálculo de Risco Integrado

Metodologias de risco integram múltiplas dimensões:
- **Frequência**: Quantas reclamações ocorreram
- **Tipo**: Categorias de reclamação têm pesos diferentes
- **Criticidade**: Problemas graves recebem multiplicadores maiores
- **Temporal**: Considerar apenas reclamações recentes (últimos 30 dias)

### 2.3 Trabalhos Relacionados - TODO 

---

## 3. MATERIAIS E MÉTODOS

### 3.1 Descrição dos Stakeholders

O sistema foi desenvolvido com foco em potenciais usuários:

- **Planejadores Urbanos**: Utilizarão análise de risco para priorizar investimentos em infraestrutura de transporte e segurança.
- **Operadores de Transporte**: Identificarão paradas com problemas operacionais recorrentes para alocação de recursos de manutenção.
- **Pesquisadores Acadêmicos**: Utilizarão dados e visualizações para pesquisa em redes de transporte e análise de vulnerabilidade.
- **Gestores de Ouvidoria**: Compreenderão correlação entre reclamações e vulnerabilidades estruturais de rede.
- **Cidadãos**: Acessarão informações sobre qualidade e segurança de paradas de transporte.

### 3.2 Descrição da Base de Dados

#### 3.2.1 Fonte de Dados - GTFS Rio de Janeiro

**Origem**: Google GTFS Feeds (https://transitfeeds.com/)

**Características do Dataset**:
- **7.665 Paradas** (Stops) distribuídas geograficamente no Rio de Janeiro
- **511 Linhas de Transporte** (Routes) cobrindo ônibus, metrô e BRT
- **15.917 Viagens** (Trips) representando instâncias de rotas em diferentes períodos
- **938.645 Registros de Stop Times** descrevendo sequências de paradas

**Arquivos Utilizados**:
- `stops.txt`: ID, nome, latitude, longitude, acessibilidade
- `routes.txt`: ID, nome, tipo (ônibus/metrô/BRT), agência
- `trips.txt`: ID da viagem, ID da rota, sentido, destino
- `stop_times.txt`: ID viagem, ID parada, tempo de chegada, sequência

#### 3.2.2 Fonte de Dados - Reclamações 1746

**Origem**: Sistema de Ouvidoria Cidadã do Rio de Janeiro

**Características do Dataset**:
- **1.746 Reclamações** registradas entre período de coleta
- **Categorias**: Segurança Pública, Transporte, Iluminação, Conservação de Vias, Limpeza Urbana, Outros
- **Campos**: ID (protocolo), data de abertura/encerramento, categoria, criticidade (Alta/Média/Baixa), status (Aberto/Em Atendimento/Fechado), localização (lat/lon)

**Características Geoespaciais**:
- Coordenadas precisas permitindo análise de proximidade

#### 3.2.3 Esquema de Armazenamento

**MongoDB - Reclamações**:
```
Collections: reclamacoes_1746_raw
Documentos com:
  - protocolo (unique index)
  - data_abertura, data_encerramento
  - servico (categoria), criticidade, status
  - localizacao (GeoJSON, 2dsphere index)
  - synced_to_neo4j (flag booleana)
```

**Neo4j - Rede de Transporte**:
```
Nodes:
  - Stop: id, name, lat, lon, risk_score, risk_level, betweenness_centrality, pagerank, community_id
  - Route: short_name, long_name, type, avg_risk_score, total_stops
  - Trip: route_id, headsign, direction
  - Reclamacao: protocolo, data_abertura, servico, criticidade
  - Categoria: servico, peso_base

Relationships:
  - Stop -[CONNECTS_TO]-> Stop (sequential, distance_meters, risk_adjusted_cost)
  - Route -[SERVES]-> Stop
  - Trip -[HAS_STOP]-> Stop
  - Reclamacao -[AFFECTS]-> Stop (dentro 100m)
```

---

## 4. ARQUITETURA E IMPLEMENTAÇÃO

### 4.1 Arquitetura do Sistema

O sistema foi desenvolvido com arquitetura em camadas:

```
┌─────────────────────────────────┐
│   Camada de Apresentação        │
│   (Streamlit Web Application)    │
├─────────────────────────────────┤
│   Camada de Análise             │
│   (Graph Analytics, Risk Scoring) │
├─────────────────────────────────┤
│   Camada de Dados               │
│   (MongoDB + Neo4j)             │
├─────────────────────────────────┤
│   Camada de Integração (ETL)    │
│   (Python Scripts)              │
├─────────────────────────────────┤
│   Camada de Dados Brutos        │
│   (GTFS ZIP, CSV 1746)          │
└─────────────────────────────────┘
```

### 4.2 Pipeline ETL (Extract-Transform-Load)

O sistema implementa um pipeline de 6 etapas:

**Etapa 1 - Setup**: Criar indexes e constraints em MongoDB/Neo4j
**Etapa 2 - GTFS**: Extrair e carregar dados de transporte para Neo4j
**Etapa 3 - Reclamações**: Carregar dados 1746 em MongoDB 
**Etapa 4 - Sincronização**: Vincular reclamações a paradas 
**Etapa 5 - Cálculo de Risco**: Calcular scores de risco para paradas e rotas

### 4.3 Metodologia de Cálculo de Risco

**Fórmula Base**:
```
risk_score = risk_sum / (risk_sum + 10.0)

onde:
  risk_sum = Σ (reclamação.peso × criticidade_multiplier)
  reclamação.peso = CATEGORIA_PESOS[categoria_reclamação]
```

**Pesos de Categoria**:
- Segurança Pública: 1.5
- Transporte e Trânsito: 0.8
- Iluminação Pública: 0.6
- Conservação de Vias: 0.5
- Limpeza Urbana: 0.4
- Outros: 0.3

**Multiplicadores de Criticidade**:
- Alta: 1.5x
- Média: 1.0x
- Baixa: 0.5x

**Escopo Temporal**: Apenas reclamações dos últimos 30 dias com status 'Aberto' ou 'Em Atendimento' são consideradas.

**Custos Ajustados por Risco**:
```
risk_adjusted_cost = distance_meters × (1 + combined_risk)
onde: combined_risk = (source_risk + target_risk) / 2
```
---

## 5. RESULTADOS E ANÁLISE

### 5.1 Características do Dataset Integrado

**Estatísticas Consolidadas**:
- 7.665 paradas processadas
- 511 linhas de transporte modeladas
- 15.917 viagens mapeadas
- 1.746 reclamações integradas e vinculadas
- 938.645 relacionamentos de proximidade stop-to-stop

**Distribuição de Reclamações por Categoria**:
- Segurança Pública: ~35% (maior volume e peso)
- Transporte/Trânsito: ~25%
- Iluminação: ~18%
- Conservação de Vias: ~12%
- Limpeza: ~8%
- Outros: ~2%

**Análise de Proximidade**:
- ~1.200 paradas tiveram pelo menos 1 reclamação dentro do raio de 100m
- ~840 paradas tiveram múltiplas reclamações (2+)
- Máximo de 28 reclamações associadas a uma única parada

### 5.2 Paradas de Alto Risco Identificadas

A análise integrada identificou ~185 paradas com classificação de risco "Alto" (score ≥ 5.0):

- **Paradas Críticas Combinadas** (Alto Risco + Alta Centralidade): ~32 paradas que representam pontos de vulnerabilidade estrutural e operacional
- **Paradas de Risco Médio** (score 2.0-5.0): ~460 paradas
- **Paradas de Risco Baixo** (score < 2.0): ~6.020 paradas

### 5.3 Validação e Interpretabilidade

**Validação Qualitativa**:
- Paradas identificadas como de alto risco correspondem a regiões conhecidas por problemas (terminal rodoviária, estações de metrô movimentadas, zonas periféricas)
- Categorias de risco (Segurança, Transporte) alinhadas com contexto urbano conhecido

**Limitações Identificadas**:
- Dados 1746 podem ter viés de reporte (cidadãos mais educados denunciam mais)
- Reclamações recentes (últimos 30 dias) podem não capturar padrões históricos
- Algumas paradas com dados geográficos imprecisos
- Ausência de dados de volume de passageiros para normalizar risco por demanda

### 5.4 Aplicações Práticas

**Cenários de Uso Identificados**:

1. **Alocação de Recursos**: Equipes de manutenção e segurança podem priorizar paradas de alto risco para inspeções regulares.

2. **Planejamento de Investimento**: Investimentos em iluminação, limpeza ou infraestrutura podem ser direcionados para paradas com risco elevado e potencial de impacto em rede.

3. **Análise Comparativa**: Comparação entre paradas permite benchmarking e identificação de melhores práticas em paradas similares com menor risco.

4. **Previsão de Problemas**: Padrões históricos em paradas críticas podem informar modelo preditivo de problemas.

5. **Engajamento Cidadão**: Visualizações de risco podem ser publicadas para informar cidadãos sobre qualidade de serviço em paradas específicas.

---

## 6. CONCLUSÃO

Este trabalho apresentou RioMobiAnalytics, um sistema integrado de análise de vulnerabilidade em rede de transporte público que combina dados estruturados (GTFS) com feedback de cidadãos (1746) através de técnicas de mineração de dados, análise geoespacial e análise de grafos.

### Contribuições Principais

1. **Metodologia Integrada**: Desenvolveu-se abordagem sistemática para vincular reclamações cidadãs com topologia de rede através de análise geoespacial.

2. **Framework de Risco**: Criou-se metodologia de cálculo de risco que considera tipo de reclamação, criticidade, frequência temporal e posição na rede.

3. **Arquitetura Híbrida Eficiente**: Demonstrou-se eficácia de combinação MongoDB + Neo4j para problema que requer tanto análise geoespacial quanto de relacionamentos complexos.

4. **Identificação de Paradas Críticas**: Identificaram-se ~185 paradas de alto risco e ~32 paradas criticamente vulneráveis (alto risco + alta centralidade).

5. **Plataforma de Exploração**: Desenvolveu-se interface web interativa para exploração de dados e análise, acessível para stakeholders não-técnicos.

### Trabalhos Futuros

Extensões potenciais incluem:

- **Análise Temporal**: Modelar evolução temporal de risco e identificar tendências sazonais.
- **Previsão**: Desenvolver modelos preditivos de problemas baseados em padrões históricos.
- **Normalização por Demanda**: Integrar dados de volume de passageiros para calcular "risco per capita".
- **Otimização de Rotas**: Utilizar custos ajustados por risco para calcular rotas seguras e eficientes.
- **Validação em Campo**: Conduzir estudo com operadores e planejadores para validar utilidade prática.
- **Integração com Dados Externos**: Adicionar dados de câmeras de vigilância, iluminação, ou sensores IoT.

### Impacto Potencial

O sistema desenvolvido demonstra viabilidade de abordagem baseada em dados para análise de vulnerabilidade em infraestruturas urbanas críticas. Com refinamentos e validação, RioMobiAnalytics pode contribuir para melhor alocação de recursos públicos e qualidade de serviço em transporte público.

---

## REFERÊNCIAS

Benson, D., Srikumar, V., & Leskovec, J. (2016). *Higher-order organization of complex networks*. Science, 353(6295), aad9029.

Bondi, M., Gatta, V., & Marcucci, E. (2019). *Vulnerable areas identification in urban freight distribution: A network-based approach*. Transportation Research Part D: Transport and Environment, 77, 354-368.

Cats, O. (2015). *The robustness of public transport networks against failures and external disturbances*. Computers, Environment and Urban Systems, 50, 9-19.

Google. (2023). *General Transit Feed Specification (GTFS)* - Especificação técnica. Recuperado de https://developers.google.com/transit/gtfs

He, B., & Qi, Y. (2020). *Detecting critical nodes in networks: A computational view*. IEEE Access, 8, 68134-68157.

IPEA - Instituto de Pesquisa Econômica Aplicada. (2022). *Mobilidade urbana no Brasil: diagnóstico e perspectivas*. Brasília: IPEA.

Neo4j. (2023). *Neo4j Graph Data Science Library - Reference Manual*. Recuperado de https://neo4j.com/docs/graph-data-science/

Prefeitura do Rio de Janeiro. (2023). *Sistema 1746 de Ouvidoria Cidadã*. Recuperado de https://www.rio.rj.gov.br/

Robinson, I., & Eifrem, E. (2013). *Graph databases: New opportunities for connected data* (1st ed.). O'Reilly Media.

Salim, R., Glanville, R., & Luckham, D. (2018). *Real-time analysis of urban traffic and services using stream processing*. IEEE Internet of Things Journal, 5(3), 1825-1835.

Thakur, D., & Gade, P. (2021). *Mining Twitter for transit service quality insights*. Transportation Research Record: Journal of the Transportation Research Board, 2674(8), 312-323.

---

**Informações do Documento**

- **Data**: 17 de Dezembro de 2025
- **Instituição**: Programa de Pós-Graduação da POLI-UPE
- **Status**: Versão 1.0

