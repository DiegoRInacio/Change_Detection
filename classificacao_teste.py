import ee
import geemap
import geopandas as gpd
import json
import os

def obtem_ano(ano):
    # Carrega o shapefile e filtra para o PARNA Serra da Canastra
    pnsc = gpd.read_file(r"G:\Meu Drive\@EquipeGEO\zz.Bases\ICMBio\UC_Fed_nov_2020.shp")
    pnsc = pnsc.loc[pnsc["nome"] == "PARQUE NACIONAL DA SERRA DA CANASTRA"]
    pnsc_geojson = pnsc.to_json()

    # Converte o shapefile para um objeto Earth Engine
    pnsc_ee = ee.FeatureCollection(json.loads(pnsc_geojson))

    # Função para selecionar a coleção Landsat com base no ano
    def selecionarColecaoLandsat(ano):
        if ano >= 1984 and ano <= 1999:
            return "LANDSAT/LT05/C02/T1_L2"  # Landsat 5
        elif ano >= 1999 and ano <= 2012:
            return "LANDSAT/LE07/C02/T1_L2"  # Landsat 7
        elif ano >= 2013:
            return "LANDSAT/LC08/C02/T1_L2"  # Landsat 8
        else:
            raise ValueError("Ano fora do intervalo disponível para coleções Landsat")

    # Função para mascarar nuvens e sombras
    def maskLandsat(image):
        qa = image.select('QA_PIXEL')
        cloud = qa.bitwiseAnd(1 << 3).eq(0)
        shadow = qa.bitwiseAnd(1 << 5).eq(0)
        mask = cloud.And(shadow)
        return image.updateMask(mask)

    # Função para verificar se o incêndio ocorreu no período informado
    def verificar_periodo_incendio(nbrMin, ano):
        data_inicio = f"{ano}-07-01"
        data_fim = f"{ano}-10-31"
        
        # Verifica se o incêndio ocorreu no período informado
        incendio_no_periodo = nbrMin.metadata('system:time_start').gte(data_inicio) and (nbrMin.metadata('system:time_start').lte(data_fim))
        
        return incendio_no_periodo

    # Parâmetros de entrada
    data_inicio = f"{ano}-07-01"
    data_fim = f"{ano}-10-31"

    # Seleciona a coleção com base no ano
    colecao = selecionarColecaoLandsat(ano)

    # Filtra e aplica a máscara na coleção de imagens
    dataset = ee.ImageCollection(colecao) \
        .filterDate(data_inicio, data_fim) \
        .filterBounds(pnsc_ee) \
        .map(maskLandsat)

    # Seleciona as bandas para a visualização True Color e NBR
    if ano <= 2012:  # Landsat 5 e 7
        trueColor432 = dataset.select(["SR_B3", "SR_B2", "SR_B1"])
        nbr = dataset.map(lambda image: image.normalizedDifference(["SR_B4", "SR_B7"]).rename("NBR"))
    else:  # Landsat 8
        trueColor432 = dataset.select(["SR_B4", "SR_B3", "SR_B2"])
        nbr = dataset.map(lambda image: image.normalizedDifference(["SR_B5", "SR_B7"]).rename("NBR"))

    trueColor432Vis = {
        "min": 0.0,
        "max": 0.4,
    }

    # Obtém o NBR mínimo (severidade máxima)
    nbrMin = nbr.min()

    # Verifica se o incêndio ocorreu no período informado
    incendio_no_periodo = verificar_periodo_incendio(nbrMin, ano)

    # Classifica a severidade das queimadas com base em novos limiares
    classificacao = nbrMin.expression(
        "(nbr < -0.5) ? 3 : "  # Queimada de alta intensidade (vermelho)
        "((nbr >= -0.5) && (nbr < -0.2)) ? 2 : "  # Queimada de moderada intensidade (amarelo)
        "((nbr >= -0.2) && (nbr < -0.1)) ? 1 : "  # Queimada de baixa intensidade (laranja)
        "0", # Área não queimada (não exibida)
        {"nbr": nbrMin}
    )

    # Parâmetros de visualização para a classificação de severidade
    classificacaoVis = {
        "min": 1,
        "max": 3,
        "palette": ["orange", "yellow", "red"]  # Baixa intensidade (laranja), Moderada (amarelo), Alta (vermelho)
    }

    # Calcula o centróide do PNSC
    centroid = pnsc_ee.geometry().centroid()

    # Inicializa o mapa centrado no centróide do PNSC
    Map = geemap.Map(center=(centroid.coordinates().get(1).getInfo(), centroid.coordinates().get(0).getInfo()), zoom=10)

    # Adiciona camadas ao mapa
    Map.addLayer(trueColor432.median(), trueColor432Vis, "True Color (432)")
    Map.addLayer(nbrMin, {"min": -1, "max": 1}, "NBR Mínimo (Maior Severidade de Queimada)")

    # Adiciona uma camada com informação sobre o período do incêndio
    if incendio_no_periodo:
        Map.addLayer(classificacao.updateMask((link unavailable)(0)), classificacaoVis, f"Class Sever {ano} (Incêndio no período)")
    else:
        Map.addLayer(classificacao.updateMask((link unavailable)(0)), classificacaoVis, f"Class Sever {ano} (Incêndio fora do período)")

    Map.addLayer(ee.Image().paint(pnsc_ee, 0, 2), {}, "PARNA Serra da Canastra")

    # Retorna o mapa atualizado
    return Map
