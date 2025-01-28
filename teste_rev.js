/* Esse script é um esboço para aplicação do NDVI
primeiramente adicione a geometria ou shape da sua área de interesse
Foi utilizado a coleção USGS Landsat 9 Level 2, Collection 2, Tier 1, seu ID é (ee.ImageCollection("LANDSAT/LC09/C02/T1_L2"))
Já com a supercifie corrigida para reflectancia
*/
//Bacia Hidrográfica do Rio São João
var retangulo = ee.Geometry.Rectangle([-42.64, -22.85, -41.91, -22.38]);
Map.addLayer(retangulo);
Map.centerObject(retangulo, 10);

// Define os anos desejados
var years = ee.List.sequence(2022, 2023);

// Lista para armazenar as imagens filtradas
var filteredImages = ee.ImageCollection([]);

// Loop sobre os anos
years.evaluate(function(yearsList) {
  // Precisamos usar uma abordagem assíncrona, como o Promise.all(), para lidar com múltiplas avaliações de ano
  Promise.all(yearsList.map(function(year) {
    return new Promise(function(resolve) {
      // Filtra as imagens de junho a setembro para o ano atual
      var imagesOfYear = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        .filterDate(year + '-06-01', year + '-09-30')
        .filterMetadata('CLOUD_COVER', 'less_than', 5)
        .filterBounds(retangulo);
      
      // Adiciona as imagens filtradas à lista
      filteredImages = filteredImages.merge(imagesOfYear);
      
      // Resolve a promessa após terminar de processar as imagens do ano atual
      resolve();
    });
  })).then(function() {
    // Imprime a lista de bandas disponíveis
    var firstImage = ee.Image(filteredImages.first());
    var bandList = firstImage.bandNames();
    print('Lista de bandas:', bandList);
    
    // Aplica outras operações após a conclusão do loop, como escala de fatores, visualização, etc.
    applyOperations(filteredImages);
  });
});

// Função para aplicar operações após filtrar as imagens
function applyOperations(collection) {
  // Aplicação de correção de fatores de escala
  function applyScaleFactors(image) {
    var opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2);
    var thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0);
    return image.addBands(opticalBands, null, true)
                .addBands(thermalBands, null, true);
  }

  var scaledCollection = collection.map(applyScaleFactors);

  // Determina os parâmetros de visualização
  var visualization = {
    bands: ['SR_B4', 'SR_B3', 'SR_B2'],
    min: 0.0,
    max: 0.2,
  };

  // Adiciona a coleção ao mapa com a visualização
  Map.addLayer(scaledCollection, visualization, '432');
}

var mediana = dataset.median ()
.select ('SR_B.')
.clip (retangulo);
Map.addLayer(mediana, visualization, 'RGB')


var ndvi = mediana.normalizedDifference(['SR_B5','SR_B4']); //observar que as bandas possuem palavras-chave diferente

// os comandos abaixo, adiciona ao mapa
var vegPalette = ['white', 'green'];
Map.addLayer(ndvi, {min:-1, max:1, palette: vegPalette}, 'NDVI 2 cores');

var custumPalette = ['white', 'red', 'yellow', 'green'];
Map.addLayer(ndvi, {min:-1, max: 1, palette: custumPalette}, 'NDVI 4 cores');

//Comando para exportar imagem NDVI para seu Drive
// OBS: para mais informações de como iniciar download, acesse a apostila na página 21

Export.image.toDrive({image:ndvi, // nome da variável que armazena sua imagem
                        description:'landsat9_RC',
                        folder:'GEE', //exemplo de nome da pasta dentro do seu Drive
                        fileNamePrefix:'Landsat9_RC',
                        region:retangulo,//representam a região a ser exportada, podendo ser uma geometria ou coordenadas em forma de string
                        scale:20,
                        crs:'EPSG:4326',
                        maxPixels:1e13,
                        fileFormat:'GeoTIFF'});