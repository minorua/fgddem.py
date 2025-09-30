// FGD DEM Web Converter core logic (GML/XML to raster array)
document.getElementById('convertBtn').onclick = async function() {
  const fileInput = document.getElementById('fileInput');
  const output = document.getElementById('output');
  if (!fileInput.files.length) {
    output.textContent = 'ファイルを選択してください。';
    return;
  }
  const file = fileInput.files[0];
  if (file.name.endsWith('.xml')) {
    const text = await file.text();
    const result = parseJPGISGML(text);
    output.textContent = 'GMLパース結果: ' + JSON.stringify(result, null, 2);
    // GeoTIFF出力ボタン追加
    const dlBtn = document.createElement('button');
    dlBtn.textContent = 'GeoTIFFダウンロード';
    dlBtn.onclick = async () => {
      try {
        const tiffBlob = await createGeoTIFF(result);
        const url = URL.createObjectURL(tiffBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.name.replace(/\.xml$/i, '.tif');
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
      } catch (e) {
        alert('GeoTIFF作成失敗: ' + e);
      }
    };
    output.appendChild(document.createElement('br'));
    output.appendChild(dlBtn);
  } else if (file.name.endsWith('.zip')) {
    output.textContent = 'ZIP対応は今後実装予定です。';
  } else {
    output.textContent = '対応していないファイル形式です。';
  }
// GeoTIFF作成関数（geotiff.js使用）
async function createGeoTIFF(result) {
  // geotiff.jsのGeoTIFFImageWriterを使う
  // result.raster: 2次元配列 [y][x]
  const {xsize, ysize} = result.size;
  // 1次元Float32Arrayに変換
  const data = new Float32Array(xsize * ysize);
  for (let y = 0; y < ysize; y++) {
    for (let x = 0; x < xsize; x++) {
      data[y * xsize + x] = result.raster[y][x];
    }
  }
  // geotiff.jsのfromArrayBufferでGeoTIFF作成
  // ここではgeotiff.js v2.0以降のwriteArrayBuffer APIを想定
  // https://geotiffjs.github.io/geotiff.js/module-geotiff.html#.writeArrayBuffer
  const geoKeys = {
    GTModelTypeGeoKey: 2, // Geographic
    GTRasterTypeGeoKey: 1, // PixelIsArea
    GeographicTypeGeoKey: 4326 // WGS84 (仮)
  };
  const tiepoint = [0, 0, 0, result.bounds.ulx, result.bounds.uly, 0];
  const pixelScale = [
    (result.bounds.lrx - result.bounds.ulx) / xsize,
    (result.bounds.lry - result.bounds.uly) / ysize,
    0
  ];
  // geotiff.js v2+ のAPI例
  const arrayBuffer = await GeoTIFF.writeArrayBuffer([
    {
      width: xsize,
      height: ysize,
      data: [data],
      samplesPerPixel: 1,
      bitsPerSample: 32,
      sampleFormat: 3, // float
      geoKeyDirectory: geoKeys,
      tiePoints: tiepoint,
      pixelScale: pixelScale,
      noData: -9999
    }
  ]);
  return new Blob([arrayBuffer], {type: 'image/tiff'});
}
};

function parseJPGISGML(text) {
  // GMLのheader/body/footer分割
  const [header, bodyWithFooter] = text.split('<gml:tupleList>');
  const [body, footer] = bodyWithFooter.split('</gml:tupleList>');
  const parser = new DOMParser();
  const doc = parser.parseFromString(header + footer, 'application/xml');
  // 範囲情報
  const lowerCorner = doc.querySelector('gml\\:lowerCorner').textContent.split(' ');
  const upperCorner = doc.querySelector('gml\\:upperCorner').textContent.split(' ');
  const lry = parseFloat(lowerCorner[0]);
  const ulx = parseFloat(lowerCorner[1]);
  const uly = parseFloat(upperCorner[0]);
  const lrx = parseFloat(upperCorner[1]);
  // サイズ
  const high = doc.querySelector('gml\\:high').textContent.split(' ');
  const xsize = parseInt(high[0]) + 1;
  const ysize = parseInt(high[1]) + 1;
  // 開始点
  const startPoint = doc.querySelector('gml\\:startPoint').textContent.split(' ');
  const startX = parseInt(startPoint[0]);
  const startY = parseInt(startPoint[1]);
  // ラスタ配列生成
  const narray = Array.from({length: ysize}, () => Array(xsize).fill(-9999));
  const tuples = body.trim().split(/\r?\n/);
  let i = 0, sx = startX;
  for (let y = startY; y < ysize; y++) {
    for (let x = sx; x < xsize; x++) {
      if (i < tuples.length) {
        const vals = tuples[i].split(',');
        if (vals.length === 2 && !vals[1].includes('-99')) {
          narray[y][x] = parseFloat(vals[1]);
        }
        i++;
      } else {
        break;
      }
    }
    if (i === tuples.length) break;
    sx = 0;
  }
  return {
    bounds: {lry, ulx, uly, lrx},
    size: {xsize, ysize},
    start: {startX, startY},
    raster: narray
  };
}
