var codIbge = '1505536';
var nomeMunicipio = 'Parauapebas';
var anoAnalise = 2023;

var assetCol11 = 'projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_mining_substances_v1';
var assetMunicipios = 'projects/mapbiomas-workspace/AUXILIAR/municipios-2020';

var municipio = ee.FeatureCollection(assetMunicipios)
  .filter(ee.Filter.eq('CD_MUN', codIbge));

var imgColecao11 = ee.Image(assetCol11);
var bandaAno = 'classification_' + anoAnalise;
var mineracaoAno = imgColecao11.select(bandaAno).clip(municipio);

Export.image.toDrive({
  image: mineracaoAno,
  description: 'mapbiomas_mineracao_' + codIbge + '_' + anoAnalise,
  folder: 'MAPBIOMAS_EXPORT',
  fileNamePrefix: 'mapbiomas_mineracao_' + anoAnalise,
  region: municipio.geometry(),
  scale: 30,
  crs: 'EPSG:4674',
  maxPixels: 1e9,
});
