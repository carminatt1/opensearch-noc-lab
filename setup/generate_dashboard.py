#!/usr/bin/env python3
"""Gera o arquivo 05_dashboard.ndjson para importação no OpenSearch Dashboards."""
import json
import os

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "05_dashboard.ndjson")

objects = []

# 1. Index Pattern
objects.append({
    "id": "telecom-noc-pattern",
    "type": "index-pattern",
    "attributes": {
        "title": "telecom-noc*",
        "timeFieldName": "timestamp"
    },
    "references": []
})

# Helper para criar visualizações
def make_vis(vid, title, desc, vis_type, aggs, params, query="", filter_list=None):
    search_source = {
        "index": "telecom-noc-pattern",
        "query": {"query": query, "language": "kuery"},
        "filter": filter_list or []
    }
    return {
        "id": vid,
        "type": "visualization",
        "attributes": {
            "title": title,
            "visState": json.dumps({
                "title": title,
                "type": vis_type,
                "aggs": aggs,
                "params": params
            }),
            "uiStateJSON": "{}",
            "description": desc,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps(search_source)
            }
        },
        "references": [{
            "id": "telecom-noc-pattern",
            "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
            "type": "index-pattern"
        }]
    }

# 2. Volume de Ingestão (Metric)
objects.append(make_vis(
    "vis-volume-ingestao",
    "📊 Volume de Ingestão (24h)",
    "Total de documentos ingeridos",
    "metric",
    [{"id":"1","enabled":True,"type":"count","schema":"metric","params":{"customLabel":"Documentos Ingeridos"}}],
    {"addTooltip":True,"addLegend":False,"type":"metric","metric":{
        "percentageMode":False,"useRanges":False,"colorSchema":"Green to Red",
        "metricColorMode":"None","colorsRange":[{"from":0,"to":10000}],
        "labels":{"show":True},"invertColors":False,
        "style":{"bgFill":"#000","bgColor":False,"labelColor":False,"subText":"","fontSize":40}
    }}
))

# 3. Taxa de Erros (Gauge)
objects.append(make_vis(
    "vis-taxa-erros",
    "🔴 Taxa de Erros CRITICAL",
    "Contagem de eventos CRITICAL",
    "metric",
    [{"id":"1","enabled":True,"type":"count","schema":"metric","params":{"customLabel":"Eventos CRITICAL"}}],
    {"addTooltip":True,"addLegend":False,"type":"metric","metric":{
        "percentageMode":False,"useRanges":True,"colorSchema":"Green to Red",
        "metricColorMode":"Background","colorsRange":[{"from":0,"to":5},{"from":5,"to":20},{"from":20,"to":1000}],
        "labels":{"show":True},"invertColors":False,
        "style":{"bgFill":"#000","bgColor":True,"labelColor":False,"subText":"eventos críticos","fontSize":40}
    }},
    query="severity:CRITICAL"
))

# 4. Utilização Média (Metric)
objects.append(make_vis(
    "vis-utilizacao-media",
    "📈 Utilização Média (%)",
    "Média de utilização da rede",
    "metric",
    [{"id":"1","enabled":True,"type":"avg","schema":"metric","params":{"field":"utilization_pct","customLabel":"Utilização Média (%)"}}],
    {"addTooltip":True,"addLegend":False,"type":"metric","metric":{
        "percentageMode":False,"useRanges":True,"colorSchema":"Green to Red",
        "metricColorMode":"Background","colorsRange":[{"from":0,"to":30},{"from":30,"to":60},{"from":60,"to":100}],
        "labels":{"show":True},"invertColors":False,
        "style":{"bgFill":"#000","bgColor":True,"labelColor":False,"subText":"% média de uso","fontSize":40}
    }}
))

# 5. Latência Média (Metric)
objects.append(make_vis(
    "vis-latencia-media",
    "⏱️ Latência Média (ms)",
    "Latência média de rede em milissegundos",
    "metric",
    [{"id":"1","enabled":True,"type":"avg","schema":"metric","params":{"field":"latency_ms","customLabel":"Latência Média (ms)"}}],
    {"addTooltip":True,"addLegend":False,"type":"metric","metric":{
        "percentageMode":False,"useRanges":True,"colorSchema":"Green to Red",
        "metricColorMode":"Background","colorsRange":[{"from":0,"to":50},{"from":50,"to":200},{"from":200,"to":1000}],
        "labels":{"show":True},"invertColors":False,
        "style":{"bgFill":"#000","bgColor":True,"labelColor":False,"subText":"ms latência","fontSize":40}
    }}
))

# 6. Tendência de Utilização por Host (Area Chart)
objects.append(make_vis(
    "vis-tendencia-utilizacao",
    "📉 Tendência de Utilização por Host",
    "Série temporal de utilização média por hostname",
    "area",
    [
        {"id":"1","enabled":True,"type":"avg","schema":"metric","params":{"field":"utilization_pct","customLabel":"Utilização (%)"}},
        {"id":"2","enabled":True,"type":"date_histogram","schema":"segment","params":{
            "field":"timestamp","useNormalizedOpenSearchInterval":True,"interval":"auto","drop_partials":False,"min_doc_count":1,"extended_bounds":{}}},
        {"id":"3","enabled":True,"type":"terms","schema":"group","params":{
            "field":"hostname","orderBy":"1","order":"desc","size":6,"otherBucket":False,"missingBucket":False}}
    ],
    {"type":"area","grid":{"categoryLines":False},
     "categoryAxes":[{"id":"CategoryAxis-1","type":"category","position":"bottom","show":True,"style":{},"scale":{"type":"linear"},"labels":{"show":True,"filter":True,"truncate":100},"title":{}}],
     "valueAxes":[{"id":"ValueAxis-1","name":"LeftAxis-1","type":"value","position":"left","show":True,"style":{},"scale":{"type":"linear","mode":"normal"},"labels":{"show":True,"rotate":0,"filter":False,"truncate":100},"title":{"text":"Utilização (%)"}}],
     "seriesParams":[{"show":True,"type":"area","mode":"stacked","data":{"label":"Utilização (%)","id":"1"},"drawLinesBetweenPoints":True,"lineWidth":2,"showCircles":True,"interpolate":"linear","valueAxis":"ValueAxis-1"}],
     "addTooltip":True,"addLegend":True,"legendPosition":"right","times":[],"addTimeMarker":False,
     "thresholdLine":{"show":True,"value":80,"width":2,"style":"dashed","color":"#E7664C"},
     "labels":{},"orderBucketsBySum":False}
))

# 7. Timeline de Severidade (Stacked Bar)
objects.append(make_vis(
    "vis-timeline-severidade",
    "📊 Timeline de Severidade",
    "Distribuição temporal de eventos por severidade",
    "histogram",
    [
        {"id":"1","enabled":True,"type":"count","schema":"metric","params":{"customLabel":"Eventos"}},
        {"id":"2","enabled":True,"type":"date_histogram","schema":"segment","params":{
            "field":"timestamp","useNormalizedOpenSearchInterval":True,"interval":"auto","drop_partials":False,"min_doc_count":1,"extended_bounds":{}}},
        {"id":"3","enabled":True,"type":"terms","schema":"group","params":{
            "field":"severity","orderBy":"1","order":"desc","size":5,"otherBucket":False,"missingBucket":False}}
    ],
    {"type":"histogram","grid":{"categoryLines":False},
     "categoryAxes":[{"id":"CategoryAxis-1","type":"category","position":"bottom","show":True,"style":{},"scale":{"type":"linear"},"labels":{"show":True,"filter":True,"truncate":100},"title":{}}],
     "valueAxes":[{"id":"ValueAxis-1","name":"LeftAxis-1","type":"value","position":"left","show":True,"style":{},"scale":{"type":"linear","mode":"normal"},"labels":{"show":True,"rotate":0,"filter":False,"truncate":100},"title":{"text":"Eventos"}}],
     "seriesParams":[{"show":True,"type":"histogram","mode":"stacked","data":{"label":"Eventos","id":"1"},"valueAxis":"ValueAxis-1","drawLinesBetweenPoints":True,"lineWidth":2,"showCircles":True}],
     "addTooltip":True,"addLegend":True,"legendPosition":"right","times":[],"addTimeMarker":False,"labels":{"show":False},"orderBucketsBySum":False}
))

# 8. Heatmap Utilização por Host x Hora
objects.append(make_vis(
    "vis-heatmap-host",
    "🔥 Heatmap: Utilização por Host",
    "Mapa de calor mostrando utilização média por hostname",
    "heatmap",
    [
        {"id":"1","enabled":True,"type":"avg","schema":"metric","params":{"field":"utilization_pct","customLabel":"Utilização (%)"}},
        {"id":"2","enabled":True,"type":"date_histogram","schema":"segment","params":{
            "field":"timestamp","useNormalizedOpenSearchInterval":True,"interval":"auto","drop_partials":False,"min_doc_count":1,"extended_bounds":{}}},
        {"id":"3","enabled":True,"type":"terms","schema":"group","params":{
            "field":"hostname","orderBy":"1","order":"desc","size":10,"otherBucket":False,"missingBucket":False}}
    ],
    {"type":"heatmap","addTooltip":True,"addLegend":True,"enableHover":True,"legendPosition":"right",
     "colorsNumber":6,"colorSchema":"Reds","setColorRange":False,"colorsRange":[],"invertColors":False,"percentageMode":False,
     "valueAxes":[{"show":False,"id":"ValueAxis-1","type":"value","scale":{"type":"linear","defaultYExtents":False},"labels":{"show":False,"rotate":0,"overwriteColor":False,"color":"black"}}]}
))

# 9. Top Hosts por Erros (Data Table)
objects.append(make_vis(
    "vis-top-hosts-erro",
    "🏆 Top Hosts por Eventos Críticos",
    "Ranking de hosts por volume de eventos críticos",
    "table",
    [
        {"id":"1","enabled":True,"type":"count","schema":"metric","params":{"customLabel":"Total Eventos"}},
        {"id":"2","enabled":True,"type":"terms","schema":"bucket","params":{
            "field":"hostname","orderBy":"1","order":"desc","size":10,"otherBucket":False,"missingBucket":False,"customLabel":"Hostname"}},
        {"id":"3","enabled":True,"type":"avg","schema":"metric","params":{"field":"utilization_pct","customLabel":"Util. Média (%)"}},
        {"id":"4","enabled":True,"type":"avg","schema":"metric","params":{"field":"latency_ms","customLabel":"Latência Média (ms)"}},
        {"id":"5","enabled":True,"type":"avg","schema":"metric","params":{"field":"packet_loss_pct","customLabel":"Perda Pacotes (%)"}}
    ],
    {"perPage":10,"showPartialRows":False,"showMetricsAtAllLevels":False,
     "sort":{"columnIndex":None,"direction":None},"showTotal":True,"totalFunc":"sum","percentageCol":""},
    query="severity:CRITICAL"
))

# 10. Distribuição de Latência (Histogram)
objects.append(make_vis(
    "vis-distribuicao-latencia",
    "📊 Distribuição de Latência",
    "Histograma de distribuição de latência de rede",
    "histogram",
    [
        {"id":"1","enabled":True,"type":"count","schema":"metric","params":{"customLabel":"Ocorrências"}},
        {"id":"2","enabled":True,"type":"histogram","schema":"segment","params":{
            "field":"latency_ms","interval":25,"min_doc_count":1,"extended_bounds":{},"customLabel":"Latência (ms)"}}
    ],
    {"type":"histogram","grid":{"categoryLines":False},
     "categoryAxes":[{"id":"CategoryAxis-1","type":"category","position":"bottom","show":True,"style":{},"scale":{"type":"linear"},"labels":{"show":True,"filter":True,"truncate":100},"title":{"text":"Latência (ms)"}}],
     "valueAxes":[{"id":"ValueAxis-1","name":"LeftAxis-1","type":"value","position":"left","show":True,"style":{},"scale":{"type":"linear","mode":"normal"},"labels":{"show":True,"rotate":0,"filter":False,"truncate":100},"title":{"text":"Ocorrências"}}],
     "seriesParams":[{"show":True,"type":"histogram","mode":"normal","data":{"label":"Ocorrências","id":"1"},"valueAxis":"ValueAxis-1","drawLinesBetweenPoints":True,"lineWidth":2,"showCircles":True}],
     "addTooltip":True,"addLegend":False,"legendPosition":"right","times":[],"addTimeMarker":False,"labels":{"show":True},"orderBucketsBySum":False}
))

# 11. Tendência Latência vs Packet Loss (Line dual axis)
objects.append(make_vis(
    "vis-tendencia-latencia",
    "📉 Latência vs Packet Loss",
    "Correlação temporal entre latência e perda de pacotes",
    "line",
    [
        {"id":"1","enabled":True,"type":"avg","schema":"metric","params":{"field":"latency_ms","customLabel":"Latência (ms)"}},
        {"id":"4","enabled":True,"type":"avg","schema":"metric","params":{"field":"packet_loss_pct","customLabel":"Packet Loss (%)"}},
        {"id":"2","enabled":True,"type":"date_histogram","schema":"segment","params":{
            "field":"timestamp","useNormalizedOpenSearchInterval":True,"interval":"auto","drop_partials":False,"min_doc_count":1,"extended_bounds":{}}}
    ],
    {"type":"line","grid":{"categoryLines":False},
     "categoryAxes":[{"id":"CategoryAxis-1","type":"category","position":"bottom","show":True,"style":{},"scale":{"type":"linear"},"labels":{"show":True,"filter":True,"truncate":100},"title":{}}],
     "valueAxes":[
         {"id":"ValueAxis-1","name":"LeftAxis-1","type":"value","position":"left","show":True,"style":{},"scale":{"type":"linear","mode":"normal"},"labels":{"show":True,"rotate":0,"filter":False,"truncate":100},"title":{"text":"Latência (ms)"}},
         {"id":"ValueAxis-2","name":"RightAxis-1","type":"value","position":"right","show":True,"style":{},"scale":{"type":"linear","mode":"normal"},"labels":{"show":True,"rotate":0,"filter":False,"truncate":100},"title":{"text":"Packet Loss (%)"}}
     ],
     "seriesParams":[
         {"show":True,"type":"line","mode":"normal","data":{"label":"Latência (ms)","id":"1"},"valueAxis":"ValueAxis-1","drawLinesBetweenPoints":True,"lineWidth":2,"showCircles":False,"interpolate":"cardinal"},
         {"show":True,"type":"line","mode":"normal","data":{"label":"Packet Loss (%)","id":"4"},"valueAxis":"ValueAxis-2","drawLinesBetweenPoints":True,"lineWidth":2,"showCircles":False,"interpolate":"cardinal"}
     ],
     "addTooltip":True,"addLegend":True,"legendPosition":"right","times":[],"addTimeMarker":True,
     "thresholdLine":{"show":True,"value":200,"width":2,"style":"dashed","color":"#E7664C"},
     "labels":{},"orderBucketsBySum":False}
))

# 12. Eventos por Região (Donut)
objects.append(make_vis(
    "vis-regiao-distribuicao",
    "🌎 Eventos por Região",
    "Distribuição de eventos por região geográfica",
    "pie",
    [
        {"id":"1","enabled":True,"type":"count","schema":"metric","params":{"customLabel":"Eventos"}},
        {"id":"2","enabled":True,"type":"terms","schema":"segment","params":{
            "field":"region","orderBy":"1","order":"desc","size":10,"otherBucket":True,"otherBucketLabel":"Outras","missingBucket":False,"customLabel":"Região"}}
    ],
    {"type":"pie","addTooltip":True,"addLegend":True,"legendPosition":"right","isDonut":True,
     "labels":{"show":True,"values":True,"last_level":True,"truncate":100}}
))

# 13. Mapa Geográfico (Coordinate Map)
objects.append(make_vis(
    "vis-mapa-calor",
    "🗺️ Mapa de Incidentes",
    "Mapa geográfico mostrando o volume de incidentes por região no Brasil",
    "tile_map",
    [
        {"id":"1","enabled":True,"type":"count","schema":"metric","params":{"customLabel":"Eventos"}},
        {"id":"2","enabled":True,"type":"geohash_grid","schema":"segment","params":{
            "field":"location","autoPrecision":True,"precision":2,"useGeocentroid":True,"isFilteredByCollar":True,"customLabel":"Localização"}}
    ],
    {"mapType":"Scaled Circle Markers","isDesaturated":True,"addTooltip":True,"colorSchema":"Yellow to Red","metricColorMode":"None","colorsRange":[{"from":0,"to":10000}],"mapZoom":4,"mapCenter":[-15.0,-55.0]}
))

# 14. ML Forecasting (Line com Split Series)
objects.append(make_vis(
    "vis-forecasting",
    "🔮 ML Forecasting: Projeção de Utilização (+15 min)",
    "Tendência futura calculada via Machine Learning (Regressão Linear)",
    "line",
    [
        {"id":"1","enabled":True,"type":"avg","schema":"metric","params":{"field":"utilization_pct","customLabel":"Utilização Média"}},
        {"id":"2","enabled":True,"type":"date_histogram","schema":"segment","params":{
            "field":"timestamp","useNormalizedOpenSearchInterval":True,"interval":"1m","drop_partials":False,"min_doc_count":0,"extended_bounds":{}}},
        {"id":"3","enabled":True,"type":"terms","schema":"group","params":{
            "field":"_index","orderBy":"1","order":"desc","size":5,"otherBucket":False,"missingBucket":False,"customLabel":"Origem dos Dados"}}
    ],
    {"type":"line","grid":{"categoryLines":False},
     "categoryAxes":[{"id":"CategoryAxis-1","type":"category","position":"bottom","show":True,"style":{},"scale":{"type":"linear"},"labels":{"show":True,"filter":True,"truncate":100},"title":{}}],
     "valueAxes":[{"id":"ValueAxis-1","name":"LeftAxis-1","type":"value","position":"left","show":True,"style":{},"scale":{"type":"linear","mode":"normal","setYExtents":True,"defaultYExtents":False,"min":0,"max":100},"labels":{"show":True,"rotate":0,"filter":False,"truncate":100},"title":{"text":"Utilização (%)"}}],
     "seriesParams":[{"show":True,"type":"line","mode":"normal","data":{"label":"Utilização Média","id":"1"},"valueAxis":"ValueAxis-1","drawLinesBetweenPoints":True,"lineWidth":2,"showCircles":False,"interpolate":"cardinal"}],
     "addTooltip":True,"addLegend":True,"legendPosition":"right","times":[],"addTimeMarker":True,
     "thresholdLine":{"show":True,"value":85,"width":2,"style":"dashed","color":"#E7664C"},
     "labels":{},"orderBucketsBySum":False}
))

# 15. Dashboard
panel_refs = []
panel_defs = []
vis_ids = [
    "vis-volume-ingestao", "vis-taxa-erros", "vis-utilizacao-media", "vis-latencia-media",
    "vis-tendencia-utilizacao", "vis-forecasting", "vis-timeline-severidade", "vis-heatmap-host",
    "vis-top-hosts-erro", "vis-distribuicao-latencia", "vis-tendencia-latencia", "vis-regiao-distribuicao", "vis-mapa-calor"
]
# Layout grid
layouts = [
    {"x":0,"y":0,"w":12,"h":8},   # volume
    {"x":12,"y":0,"w":12,"h":8},  # erros
    {"x":24,"y":0,"w":12,"h":8},  # util media
    {"x":36,"y":0,"w":12,"h":8},  # latencia
    {"x":0,"y":8,"w":24,"h":14},  # tendencia util
    {"x":24,"y":8,"w":24,"h":14}, # forecasting (NEW)
    {"x":0,"y":22,"w":24,"h":14}, # timeline sev
    {"x":24,"y":22,"w":24,"h":14},# heatmap
    {"x":0,"y":36,"w":48,"h":12}, # top hosts
    {"x":0,"y":48,"w":24,"h":14}, # dist latencia
    {"x":24,"y":48,"w":24,"h":14},# latencia vs loss
    {"x":0,"y":62,"w":24,"h":14}, # regiao
    {"x":24,"y":62,"w":24,"h":14},# mapa de calor
]

for i, (vid, layout) in enumerate(zip(vis_ids, layouts)):
    panel_defs.append({
        "version":"2.13.0",
        "gridData":{**layout, "i": str(i+1)},
        "panelIndex": str(i+1),
        "embeddableConfig":{},
        "panelRefName": f"panel_{i}"
    })
    panel_refs.append({
        "id": vid,
        "name": f"panel_{i}",
        "type": "visualization"
    })

objects.append({
    "id": "dashboard-noc-analytics",
    "type": "dashboard",
    "attributes": {
        "title": "🖥️ NOC Telecom — Dashboard Analítico",
        "hits": 0,
        "description": "Dashboard analítico de alto nível para monitoramento NOC Telecom. KPIs, séries temporais, heatmaps, distribuições e correlações.",
        "panelsJSON": json.dumps(panel_defs),
        "optionsJSON": json.dumps({"useMargins":True,"hidePanelTitles":False}),
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps({"query":{"query":"","language":"kuery"},"filter":[]})
        }
    },
    "references": panel_refs
})

# Escrever NDJSON
with open(output_path, "w", encoding="utf-8") as f:
    for obj in objects:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

print(f"✅ Dashboard NDJSON gerado: {output_path}")
print(f"   Total de objetos: {len(objects)}")
